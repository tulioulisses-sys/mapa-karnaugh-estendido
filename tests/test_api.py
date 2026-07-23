from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
        self.operacoes_admin: list[tuple[str, dict[str, Any]]] = []
        self.erro_reserva: ErroAPI | None = None
        self.autenticado_em = datetime.now(timezone.utc)

    def autenticar(self, token: str) -> UsuarioAutenticado:
        if token != "token-valido":
            raise ErroAPI(
                status_code=401,
                codigo="TOKEN_INVALIDO",
                mensagem="Entre novamente para continuar.",
            )
        return UsuarioAutenticado(
            id=USUARIO_ID,
            email="teste@example.com",
            autenticado_em=self.autenticado_em,
        )

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

    def listar_usuarios(self, ator_id: UUID) -> list[dict[str, Any]]:
        self.operacoes_admin.append(("listar", {"ator_id": ator_id}))
        return [
            {
                "id": str(USUARIO_ID),
                "email": "aluno@example.com",
                "papel": "usuario",
                "estado": "aguardando_aprovacao",
                "acesso": "limitado",
                "analises_restantes": 0,
            }
        ]

    def alterar_estado_usuario(
        self,
        *,
        ator_id: UUID,
        usuario_id: UUID,
        estado: str,
    ) -> dict[str, Any]:
        dados = {
            "ator_id": ator_id,
            "usuario_id": usuario_id,
            "estado": estado,
        }
        self.operacoes_admin.append(("estado", dados))
        return {"id": str(usuario_id), "estado": estado}

    def definir_acesso_usuario(
        self,
        *,
        ator_id: UUID,
        usuario_id: UUID,
        acesso: str,
        analises_restantes: int | None,
    ) -> dict[str, Any]:
        dados = {
            "ator_id": ator_id,
            "usuario_id": usuario_id,
            "acesso": acesso,
            "analises_restantes": analises_restantes,
        }
        self.operacoes_admin.append(("acesso", dados))
        return {"id": str(usuario_id), **dados}

    def ajustar_cotas_lote(
        self,
        *,
        ator_id: UUID,
        operacao: str,
        quantidade: int,
        turma_id: UUID,
        usuario_ids: list[UUID] | None,
    ) -> dict[str, Any]:
        dados = {
            "ator_id": ator_id,
            "operacao": operacao,
            "quantidade": quantidade,
            "turma_id": turma_id,
            "usuario_ids": usuario_ids,
        }
        self.operacoes_admin.append(("lote", dados))
        return {
            "operacao": operacao,
            "quantidade": quantidade,
            "usuarios_alterados": 2,
            "usuarios_ignorados": 0,
        }

    def alterar_papel_usuario(
        self,
        *,
        ator_id: UUID,
        usuario_id: UUID,
        papel: str,
    ) -> dict[str, Any]:
        dados = {
            "ator_id": ator_id,
            "usuario_id": usuario_id,
            "papel": papel,
        }
        self.operacoes_admin.append(("papel", dados))
        return {"id": str(usuario_id), "papel": papel}

    def obter_transferencia_master(
        self,
        usuario_id: UUID,
    ) -> dict[str, Any] | None:
        self.operacoes_admin.append(
            ("obter_transferencia", {"usuario_id": usuario_id})
        )
        return {
            "id": str(RESERVA_ID),
            "master_atual_id": str(USUARIO_ID),
            "master_atual_email": "master@ufpe.br",
            "email_destino": "novo.master@ufpe.br",
            "estado": "pendente",
            "sou_origem": True,
            "sou_destino": False,
        }

    def iniciar_transferencia_master(
        self,
        *,
        ator_id: UUID,
        email_destino: str,
        dias_validade: int,
    ) -> dict[str, Any]:
        dados = {
            "ator_id": ator_id,
            "email_destino": email_destino,
            "dias_validade": dias_validade,
        }
        self.operacoes_admin.append(("iniciar_transferencia", dados))
        return {
            "id": str(RESERVA_ID),
            "email_destino": email_destino,
            "estado": "pendente",
            "envio_tipo": "magic_link",
        }

    def cancelar_transferencia_master(
        self,
        *,
        ator_id: UUID,
        transferencia_id: UUID,
    ) -> dict[str, Any]:
        dados = {
            "ator_id": ator_id,
            "transferencia_id": transferencia_id,
        }
        self.operacoes_admin.append(("cancelar_transferencia", dados))
        return {"id": str(transferencia_id), "estado": "cancelada"}

    def aceitar_transferencia_master(
        self,
        *,
        usuario_id: UUID,
        transferencia_id: UUID,
    ) -> dict[str, Any]:
        dados = {
            "usuario_id": usuario_id,
            "transferencia_id": transferencia_id,
        }
        self.operacoes_admin.append(("aceitar_transferencia", dados))
        return {"id": str(transferencia_id), "estado": "aceita"}

    def listar_turmas(self, ator_id: UUID) -> list[dict[str, Any]]:
        self.operacoes_admin.append(("listar_turmas", {"ator_id": ator_id}))
        return [
            {
                "id": "c19c03e5-bbf3-4f2a-88d6-b121043f5eb8",
                "codigo": "2026.1",
                "nome": "Circuitos Fluido Mecânicos",
                "ativa": True,
                "quantidade_alunos": 0,
            }
        ]

    def criar_turma(
        self,
        *,
        ator_id: UUID,
        codigo: str,
        nome: str,
    ) -> dict[str, Any]:
        dados = {"ator_id": ator_id, "codigo": codigo, "nome": nome}
        self.operacoes_admin.append(("criar_turma", dados))
        return {
            "id": "c19c03e5-bbf3-4f2a-88d6-b121043f5eb8",
            "codigo": codigo,
            "nome": nome,
            "ativa": True,
            "quantidade_alunos": 0,
        }

    def encerrar_turma(
        self,
        *,
        ator_id: UUID,
        turma_id: UUID,
        estado_usuarios: str,
    ) -> dict[str, Any]:
        dados = {
            "ator_id": ator_id,
            "turma_id": turma_id,
            "estado_usuarios": estado_usuarios,
        }
        self.operacoes_admin.append(("encerrar_turma", dados))
        return {
            "id": str(turma_id),
            "ativa": False,
            "estado_usuarios": estado_usuarios,
            "usuarios_alterados": 2,
            "matriculas_encerradas": 2,
            "convites_cancelados": 1,
        }

    def listar_auditoria(
        self,
        *,
        ator_id: UUID,
        limite: int,
    ) -> list[dict[str, Any]]:
        self.operacoes_admin.append(
            ("listar_auditoria", {"ator_id": ator_id, "limite": limite})
        )
        return [
            {
                "id": 1,
                "ator_id": str(ator_id),
                "ator_email": "professor@ufpe.br",
                "acao": "criar_turma",
                "entidade": "turma",
                "entidade_id": str(RESERVA_ID),
                "valor_anterior": None,
                "valor_posterior": {"codigo": "2026.1"},
                "criada_em": "2026-07-23T12:00:00Z",
            }
        ]

    def listar_convites(self, ator_id: UUID) -> list[dict[str, Any]]:
        self.operacoes_admin.append(("listar_convites", {"ator_id": ator_id}))
        return []

    def criar_convites_lote(
        self,
        *,
        ator_id: UUID,
        emails: list[str],
        papel_destino: str,
        acesso_destino: str,
        analises_iniciais: int | None,
        turma_id: UUID | None,
        dias_validade: int,
    ) -> dict[str, Any]:
        dados = {
            "ator_id": ator_id,
            "emails": emails,
            "papel_destino": papel_destino,
            "acesso_destino": acesso_destino,
            "analises_iniciais": analises_iniciais,
            "turma_id": turma_id,
            "dias_validade": dias_validade,
        }
        self.operacoes_admin.append(("criar_convites", dados))
        return {
            "total": len(emails),
            "convites": [
                {
                    "id": f"convite-{indice}",
                    "email": email,
                    "estado": "pendente",
                    "envio_tipo": "convite",
                }
                for indice, email in enumerate(emails)
            ],
        }

    def cancelar_convite(
        self,
        *,
        ator_id: UUID,
        convite_id: UUID,
    ) -> dict[str, Any]:
        dados = {"ator_id": ator_id, "convite_id": convite_id}
        self.operacoes_admin.append(("cancelar_convite", dados))
        return {"id": str(convite_id), "estado": "cancelado"}

    def enviar_email_acesso(self, *, email: str, tipo: str) -> None:
        self.operacoes_admin.append(
            ("enviar_email", {"email": email, "tipo": tipo})
        )


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
    assert resposta.json()["api_version"] == "1.5.0"
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
    assert "/api/v1/admin/usuarios" in caminhos
    assert "/api/v1/admin/usuarios/{usuario_id}/estado" in caminhos
    assert "/api/v1/admin/usuarios/{usuario_id}/acesso" in caminhos
    assert "/api/v1/admin/usuarios/cotas-em-lote" in caminhos
    assert "/api/v1/admin/usuarios/{usuario_id}/papel" in caminhos
    assert "/api/v1/transferencia-master" in caminhos
    assert "/api/v1/admin/transferencia-master" in caminhos
    assert (
        "/api/v1/admin/transferencia-master/"
        "{transferencia_id}/cancelar"
    ) in caminhos
    assert (
        "/api/v1/transferencia-master/{transferencia_id}/aceitar"
    ) in caminhos
    assert "/api/v1/admin/turmas" in caminhos
    assert "/api/v1/admin/turmas/{turma_id}/encerrar" in caminhos
    assert "/api/v1/admin/auditoria" in caminhos
    assert "/api/v1/admin/convites" in caminhos
    assert "/api/v1/admin/convites/lote" in caminhos
    assert "/api/v1/admin/convites/{convite_id}/cancelar" in caminhos


def test_lista_usuarios_para_painel_admin(
    provedor: ProvedorAcessoFake,
) -> None:
    resposta = client.get(
        "/api/v1/admin/usuarios",
        headers=CABECALHO_LOGIN,
    )

    assert resposta.status_code == 200
    assert resposta.json()[0]["email"] == "aluno@example.com"
    assert provedor.operacoes_admin == [
        ("listar", {"ator_id": USUARIO_ID})
    ]


def test_aprova_usuario_pela_api(provedor: ProvedorAcessoFake) -> None:
    aluno_id = UUID("251323e1-26d0-4fe0-8478-3ca9870eb59a")
    resposta = client.patch(
        f"/api/v1/admin/usuarios/{aluno_id}/estado",
        headers=CABECALHO_LOGIN,
        json={"estado": "ativo"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "ativo"
    assert provedor.operacoes_admin[-1] == (
        "estado",
        {
            "ator_id": USUARIO_ID,
            "usuario_id": aluno_id,
            "estado": "ativo",
        },
    )


def test_define_acesso_limitado(provedor: ProvedorAcessoFake) -> None:
    aluno_id = UUID("251323e1-26d0-4fe0-8478-3ca9870eb59a")
    resposta = client.patch(
        f"/api/v1/admin/usuarios/{aluno_id}/acesso",
        headers=CABECALHO_LOGIN,
        json={"acesso": "limitado", "analises_restantes": 3},
    )

    assert resposta.status_code == 200
    assert provedor.operacoes_admin[-1][1]["analises_restantes"] == 3


def test_rejeita_acesso_limitado_sem_saldo(
    provedor: ProvedorAcessoFake,
) -> None:
    aluno_id = UUID("251323e1-26d0-4fe0-8478-3ca9870eb59a")
    resposta = client.patch(
        f"/api/v1/admin/usuarios/{aluno_id}/acesso",
        headers=CABECALHO_LOGIN,
        json={"acesso": "limitado"},
    )

    assert resposta.status_code == 422
    assert provedor.operacoes_admin == []


def test_adiciona_cota_em_lote(provedor: ProvedorAcessoFake) -> None:
    turma_id = "c19c03e5-bbf3-4f2a-88d6-b121043f5eb8"
    resposta = client.post(
        "/api/v1/admin/usuarios/cotas-em-lote",
        headers=CABECALHO_LOGIN,
        json={
            "operacao": "adicionar",
            "quantidade": 1,
            "turma_id": turma_id,
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["usuarios_alterados"] == 2
    assert provedor.operacoes_admin[-1][1]["usuario_ids"] is None
    assert str(provedor.operacoes_admin[-1][1]["turma_id"]) == turma_id


def test_promove_submaster(provedor: ProvedorAcessoFake) -> None:
    aluno_id = UUID("251323e1-26d0-4fe0-8478-3ca9870eb59a")
    resposta = client.patch(
        f"/api/v1/admin/usuarios/{aluno_id}/papel",
        headers=CABECALHO_LOGIN,
        json={"papel": "submaster"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["papel"] == "submaster"


def test_inicia_transferencia_master_e_envia_email(
    provedor: ProvedorAcessoFake,
) -> None:
    resposta = client.post(
        "/api/v1/admin/transferencia-master",
        headers=CABECALHO_LOGIN,
        json={
            "email_destino": "NOVO.MASTER@UFPE.BR",
            "dias_validade": 7,
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["envio_email"] == "enviado"
    assert (
        "iniciar_transferencia",
        {
            "ator_id": USUARIO_ID,
            "email_destino": "novo.master@ufpe.br",
            "dias_validade": 7,
        },
    ) in provedor.operacoes_admin
    assert (
        "enviar_email",
        {
            "email": "novo.master@ufpe.br",
            "tipo": "magic_link",
        },
    ) in provedor.operacoes_admin


def test_transferencia_master_exige_login_recente(
    provedor: ProvedorAcessoFake,
) -> None:
    provedor.autenticado_em = datetime.now(timezone.utc) - timedelta(hours=1)

    resposta = client.post(
        "/api/v1/admin/transferencia-master",
        headers=CABECALHO_LOGIN,
        json={"email_destino": "novo.master@ufpe.br"},
    )

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "REAUTENTICACAO_NECESSARIA"
    assert provedor.operacoes_admin == []


def test_destinatario_aceita_transferencia_master(
    provedor: ProvedorAcessoFake,
) -> None:
    resposta = client.post(
        f"/api/v1/transferencia-master/{RESERVA_ID}/aceitar",
        headers=CABECALHO_LOGIN,
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "aceita"
    assert provedor.operacoes_admin[-1] == (
        "aceitar_transferencia",
        {
            "usuario_id": USUARIO_ID,
            "transferencia_id": RESERVA_ID,
        },
    )


def test_master_cancela_transferencia_pendente(
    provedor: ProvedorAcessoFake,
) -> None:
    resposta = client.patch(
        f"/api/v1/admin/transferencia-master/{RESERVA_ID}/cancelar",
        headers=CABECALHO_LOGIN,
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "cancelada"


def test_cria_turma_para_convites(provedor: ProvedorAcessoFake) -> None:
    resposta = client.post(
        "/api/v1/admin/turmas",
        headers=CABECALHO_LOGIN,
        json={
            "codigo": "2026.1",
            "nome": "Circuitos Fluido Mecânicos",
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["codigo"] == "2026.1"
    assert provedor.operacoes_admin[-1][0] == "criar_turma"


def test_encerra_turma_e_revoga_alunos(
    provedor: ProvedorAcessoFake,
) -> None:
    turma_id = "c19c03e5-bbf3-4f2a-88d6-b121043f5eb8"
    resposta = client.patch(
        f"/api/v1/admin/turmas/{turma_id}/encerrar",
        headers=CABECALHO_LOGIN,
        json={"estado_usuarios": "revogado"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["ativa"] is False
    assert resposta.json()["usuarios_alterados"] == 2
    assert provedor.operacoes_admin[-1] == (
        "encerrar_turma",
        {
            "ator_id": USUARIO_ID,
            "turma_id": UUID(turma_id),
            "estado_usuarios": "revogado",
        },
    )


def test_lista_auditoria_com_limite(
    provedor: ProvedorAcessoFake,
) -> None:
    resposta = client.get(
        "/api/v1/admin/auditoria?limite=25",
        headers=CABECALHO_LOGIN,
    )

    assert resposta.status_code == 200
    assert resposta.json()[0]["acao"] == "criar_turma"
    assert provedor.operacoes_admin[-1] == (
        "listar_auditoria",
        {"ator_id": USUARIO_ID, "limite": 25},
    )


def test_rejeita_limite_invalido_da_auditoria(
    provedor: ProvedorAcessoFake,
) -> None:
    resposta = client.get(
        "/api/v1/admin/auditoria?limite=201",
        headers=CABECALHO_LOGIN,
    )

    assert resposta.status_code == 422
    assert provedor.operacoes_admin == []


def test_cria_convites_em_lote_e_envia_emails(
    provedor: ProvedorAcessoFake,
) -> None:
    turma_id = "c19c03e5-bbf3-4f2a-88d6-b121043f5eb8"
    resposta = client.post(
        "/api/v1/admin/convites/lote",
        headers=CABECALHO_LOGIN,
        json={
            "emails": [
                "ALUNO1@UFPE.BR",
                "aluno2@ufpe.br",
                "aluno1@ufpe.br",
            ],
            "papel_destino": "usuario",
            "acesso_destino": "limitado",
            "analises_iniciais": 3,
            "turma_id": turma_id,
            "dias_validade": 7,
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 2
    assert resposta.json()["emails_enviados"] == 2
    criacao = next(
        dados
        for operacao, dados in provedor.operacoes_admin
        if operacao == "criar_convites"
    )
    assert criacao["emails"] == ["aluno1@ufpe.br", "aluno2@ufpe.br"]
    assert criacao["analises_iniciais"] == 3
    assert sum(
        operacao == "enviar_email"
        for operacao, _dados in provedor.operacoes_admin
    ) == 2


def test_rejeita_convite_ilimitado_com_saldo(
    provedor: ProvedorAcessoFake,
) -> None:
    resposta = client.post(
        "/api/v1/admin/convites/lote",
        headers=CABECALHO_LOGIN,
        json={
            "emails": ["aluno@ufpe.br"],
            "acesso_destino": "ilimitado",
            "analises_iniciais": 1,
        },
    )

    assert resposta.status_code == 422
    assert provedor.operacoes_admin == []
