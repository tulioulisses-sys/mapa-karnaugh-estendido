from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from api.acesso.supabase import ClienteSupabase, ConfiguracaoSupabase
from api.erros import ErroAPI


USUARIO_ID = UUID("86047b7d-1ea2-45c4-a5bd-8e2d53300f6d")
RESERVA_ID = UUID("48c97529-bfcb-42af-b7ff-4da435020787")


class RespostaFake:
    def __init__(self, status_code: int, dados: Any) -> None:
        self.status_code = status_code
        self._dados = dados

    def json(self) -> Any:
        return self._dados


class HTTPFake:
    def __init__(self) -> None:
        self.gets: list[dict[str, Any]] = []
        self.posts: list[dict[str, Any]] = []
        self.resposta_get = RespostaFake(
            200,
            {"id": str(USUARIO_ID), "email": "Teste@Example.com"},
        )
        self.resposta_post = RespostaFake(
            200,
            {
                "reserva_id": str(RESERVA_ID),
                "estado": "reservada",
                "idempotente": False,
            },
        )

    def get(self, url: str, **kwargs: Any) -> RespostaFake:
        self.gets.append({"url": url, **kwargs})
        return self.resposta_get

    def post(self, url: str, **kwargs: Any) -> RespostaFake:
        self.posts.append({"url": url, **kwargs})
        return self.resposta_post


@pytest.fixture
def configuracao() -> ConfiguracaoSupabase:
    return ConfiguracaoSupabase(
        url="https://projeto.supabase.co/",
        chave_publicavel="sb_publishable_teste",
        chave_secreta="sb_secret_teste",
    )


def test_configuracao_remove_barra_final(
    configuracao: ConfiguracaoSupabase,
) -> None:
    assert configuracao.url == "https://projeto.supabase.co"


def test_autenticacao_valida_token_no_servidor_supabase(
    configuracao: ConfiguracaoSupabase,
) -> None:
    http = HTTPFake()
    cliente = ClienteSupabase(configuracao, cliente_http=http)

    usuario = cliente.autenticar("jwt-do-usuario")

    assert usuario.id == USUARIO_ID
    assert usuario.email == "teste@example.com"
    chamada = http.gets[0]
    assert chamada["url"].endswith("/auth/v1/user")
    assert chamada["headers"]["apikey"] == "sb_publishable_teste"
    assert chamada["headers"]["Authorization"] == "Bearer jwt-do-usuario"
    assert "sb_secret_teste" not in chamada["headers"].values()


def test_token_recusado_vira_erro_401(
    configuracao: ConfiguracaoSupabase,
) -> None:
    http = HTTPFake()
    http.resposta_get = RespostaFake(401, {"message": "invalid JWT"})
    cliente = ClienteSupabase(configuracao, cliente_http=http)

    with pytest.raises(ErroAPI) as capturado:
        cliente.autenticar("jwt-invalido")

    assert capturado.value.status_code == 401
    assert capturado.value.codigo == "TOKEN_INVALIDO"


def test_rpc_usa_somente_chave_secreta_no_backend(
    configuracao: ConfiguracaoSupabase,
) -> None:
    http = HTTPFake()
    cliente = ClienteSupabase(configuracao, cliente_http=http)

    resposta = cliente.reservar(
        usuario_id=USUARIO_ID,
        chave_idempotencia="requisicao-001",
        turma_id=None,
    )

    assert resposta["reserva_id"] == str(RESERVA_ID)
    chamada = http.posts[0]
    assert chamada["url"].endswith("/rest/v1/rpc/reservar_analise")
    assert chamada["headers"]["apikey"] == "sb_secret_teste"
    assert "Authorization" not in chamada["headers"]
    assert chamada["json"]["p_usuario_id"] == str(USUARIO_ID)


def test_lista_administrativa_aceita_resposta_em_lista(
    configuracao: ConfiguracaoSupabase,
) -> None:
    http = HTTPFake()
    http.resposta_post = RespostaFake(
        200,
        [
            {
                "id": str(USUARIO_ID),
                "email": "aluno@example.com",
                "papel": "usuario",
            }
        ],
    )
    cliente = ClienteSupabase(configuracao, cliente_http=http)

    usuarios = cliente.listar_usuarios(USUARIO_ID)

    assert usuarios[0]["email"] == "aluno@example.com"
    chamada = http.posts[0]
    assert chamada["url"].endswith(
        "/rest/v1/rpc/listar_usuarios_administracao"
    )
    assert chamada["json"] == {"p_ator_id": str(USUARIO_ID)}


def test_ajuste_em_lote_serializa_ids(
    configuracao: ConfiguracaoSupabase,
) -> None:
    http = HTTPFake()
    http.resposta_post = RespostaFake(
        200,
        {"usuarios_alterados": 1, "usuarios_ignorados": 0},
    )
    cliente = ClienteSupabase(configuracao, cliente_http=http)

    cliente.ajustar_cotas_lote(
        ator_id=USUARIO_ID,
        operacao="adicionar",
        quantidade=1,
        usuario_ids=[USUARIO_ID],
    )

    assert http.posts[0]["json"]["p_usuario_ids"] == [str(USUARIO_ID)]


@pytest.mark.parametrize(
    ("mensagem", "codigo"),
    (
        ("O usuário não possui análises disponíveis.", "COTA_ESGOTADA"),
        ("A conta não está ativa.", "CONTA_INATIVA"),
        ("O usuário precisa de uma turma ativa.", "TURMA_INDISPONIVEL"),
        (
            "Permissão administrativa negada.",
            "PERMISSAO_ADMINISTRATIVA_NEGADA",
        ),
    ),
)
def test_traduz_erros_seguros_do_banco(
    configuracao: ConfiguracaoSupabase,
    mensagem: str,
    codigo: str,
) -> None:
    http = HTTPFake()
    http.resposta_post = RespostaFake(400, {"message": mensagem})
    cliente = ClienteSupabase(configuracao, cliente_http=http)

    with pytest.raises(ErroAPI) as capturado:
        cliente.reservar(
            usuario_id=USUARIO_ID,
            chave_idempotencia="requisicao-001",
            turma_id=None,
        )

    assert capturado.value.codigo == codigo
    assert capturado.value.status_code == 403


def test_resposta_rpc_invalida_falha_fechada(
    configuracao: ConfiguracaoSupabase,
) -> None:
    http = HTTPFake()
    http.resposta_post = RespostaFake(200, ["formato", "inesperado"])
    cliente = ClienteSupabase(configuracao, cliente_http=http)

    with pytest.raises(ErroAPI) as capturado:
        cliente.consumir(RESERVA_ID)

    assert capturado.value.status_code == 503
    assert capturado.value.codigo == "RESPOSTA_CONTROLE_ACESSO_INVALIDA"
