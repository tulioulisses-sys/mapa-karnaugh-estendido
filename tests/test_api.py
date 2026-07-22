from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from api.acesso.dependencias import obter_provedor_acesso
from api.acesso.supabase import UsuarioAutenticado
from api.erros import ErroAPI
from api.main import app


USUARIO_ID = UUID("86047b7d-1ea2-45c4-a5bd-8e2d53300f6d")
RESERVA_ID = UUID("48c97529-bfcb-42af-b7ff-4da435020787")
CABECALHO_LOGIN = {"Authorization": "Bearer token-valido"}


class ProvedorAcessoFake:
    def __init__(self) -> None:
        self.reservas: list[dict[str, Any]] = []
        self.consumos: list[UUID] = []
        self.estornos: list[tuple[UUID, str]] = []
        self.erro_reserva: ErroAPI | None = None

    def autenticar(self, token: str) -> UsuarioAutenticado:
        if token != "token-valido":
            raise ErroAPI(
                status_code=401,
                codigo="TOKEN_INVALIDO",
                mensagem="Entre novamente para continuar.",
            )
        return UsuarioAutenticado(id=USUARIO_ID, email="teste@example.com")

    def reservar(
        self,
        *,
        usuario_id: UUID,
        chave_idempotencia: str,
        turma_id: UUID | None,
    ) -> dict[str, Any]:
        if self.erro_reserva:
            raise self.erro_reserva

        self.reservas.append(
            {
                "usuario_id": usuario_id,
                "chave_idempotencia": chave_idempotencia,
                "turma_id": turma_id,
            }
        )
        return {
            "reserva_id": str(RESERVA_ID),
            "estado": "reservada",
            "acesso": "limitado",
            "analises_restantes": 2,
            "idempotente": False,
        }

    def consumir(self, reserva_id: UUID) -> dict[str, Any]:
        self.consumos.append(reserva_id)
        return {
            "reserva_id": str(reserva_id),
            "estado": "consumida",
            "analises_restantes": 2,
            "idempotente": False,
        }

    def estornar(
        self,
        reserva_id: UUID,
        motivo: str,
    ) -> dict[str, Any]:
        self.estornos.append((reserva_id, motivo))
        return {
            "reserva_id": str(reserva_id),
            "estado": "estornada",
            "analises_restantes": 3,
            "idempotente": False,
        }


client = TestClient(app)


@pytest.fixture
def provedor() -> ProvedorAcessoFake:
    fake = ProvedorAcessoFake()
    app.dependency_overrides[obter_provedor_acesso] = lambda: fake
    yield fake
    app.dependency_overrides.pop(obter_provedor_acesso, None)


def _solicitacao_resolucao(**extras: Any) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "sequencia": "A+, B+, B-, A-",
        "chave_idempotencia": "requisicao-teste-001",
    }
    corpo.update(extras)
    return corpo


def test_health() -> None:
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"
    assert resposta.json()["api_version"] == "1.1.0"
    assert resposta.headers["x-content-type-options"] == "nosniff"


def test_analisa_sequencia_sem_consumir_cota() -> None:
    resposta = client.post(
        "/api/v1/analises",
        json={"sequencia": "A+, B+, B-, A-"},
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["atuadores"] == ["A", "B"]
    assert dados["quantidade_etapas"] == 4
    assert "projeto" not in dados


def test_resolucao_exige_login() -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        json=_solicitacao_resolucao(),
    )

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "AUTENTICACAO_OBRIGATORIA"


def test_resolve_com_mapa_e_consumo(provedor: ProvedorAcessoFake) -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        headers=CABECALHO_LOGIN,
        json=_solicitacao_resolucao(),
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["memorias"] == ["X"]
    assert dados["quantidade_memorias"] == 1
    assert dados["mapa_svg"].startswith("<svg")
    assert dados["mapa_largura"] > 0
    assert dados["controle_acesso"]["estado"] == "consumida"
    assert dados["controle_acesso"]["analises_restantes"] == 2
    assert provedor.reservas[0]["usuario_id"] == USUARIO_ID
    assert provedor.consumos == [RESERVA_ID]
    assert resposta.headers["cache-control"] == "no-store"


def test_pode_omitir_mapa(provedor: ProvedorAcessoFake) -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        headers=CABECALHO_LOGIN,
        json=_solicitacao_resolucao(incluir_mapa=False),
    )

    assert resposta.status_code == 200
    assert resposta.json()["mapa_svg"] is None
    assert provedor.consumos == [RESERVA_ID]


def test_entrada_invalida_nao_reserva_cota(
    provedor: ProvedorAcessoFake,
) -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        headers=CABECALHO_LOGIN,
        json=_solicitacao_resolucao(sequencia="A+, B"),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "SEQUENCIA_INVALIDA"
    assert provedor.reservas == []


def test_falha_apos_reserva_estorna_cota(
    provedor: ProvedorAcessoFake,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def falhar_resolucao(**_kwargs: Any) -> dict[str, Any]:
        raise ValueError("Falha de validação posterior.")

    monkeypatch.setattr("api.main.resolver_site", falhar_resolucao)
    resposta = client.post(
        "/api/v1/resolucoes",
        headers=CABECALHO_LOGIN,
        json=_solicitacao_resolucao(),
    )

    assert resposta.status_code == 422
    assert provedor.estornos == [
        (RESERVA_ID, "erro_entrada_ou_resolucao")
    ]
    assert provedor.consumos == []


def test_cota_esgotada_impede_motor(provedor: ProvedorAcessoFake) -> None:
    provedor.erro_reserva = ErroAPI(
        status_code=403,
        codigo="COTA_ESGOTADA",
        mensagem="Você não possui análises disponíveis.",
    )
    resposta = client.post(
        "/api/v1/resolucoes",
        headers=CABECALHO_LOGIN,
        json=_solicitacao_resolucao(),
    )

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "COTA_ESGOTADA"
    assert provedor.consumos == []


def test_rejeita_campo_desconhecido(provedor: ProvedorAcessoFake) -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        headers=CABECALHO_LOGIN,
        json=_solicitacao_resolucao(administrador=True),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"
    assert provedor.reservas == []


def test_limita_tamanho_da_sequencia(provedor: ProvedorAcessoFake) -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        headers=CABECALHO_LOGIN,
        json=_solicitacao_resolucao(sequencia="A" * 20_001),
    )

    assert resposta.status_code == 413
    assert resposta.json()["erro"]["codigo"] == "ENTRADA_MUITO_GRANDE"
    assert provedor.reservas == []


def test_limita_chave_sem_confundir_com_tamanho_da_sequencia(
    provedor: ProvedorAcessoFake,
) -> None:
    resposta = client.post(
        "/api/v1/resolucoes",
        headers=CABECALHO_LOGIN,
        json=_solicitacao_resolucao(chave_idempotencia="x" * 201),
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "DADOS_INVALIDOS"
    assert resposta.json()["erro"]["campo"] == "chave_idempotencia"
    assert provedor.reservas == []


def test_openapi_publica_endpoints_v1() -> None:
    resposta = client.get("/openapi.json")

    assert resposta.status_code == 200
    caminhos = resposta.json()["paths"]
    assert "/health" in caminhos
    assert "/api/v1/analises" in caminhos
    assert "/api/v1/resolucoes" in caminhos
