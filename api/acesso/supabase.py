from __future__ import annotations

import os
from math import isfinite
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import httpx2

from api.erros import ErroAPI


@dataclass(frozen=True, slots=True)
class ConfiguracaoSupabase:
    url: str
    chave_publicavel: str
    chave_secreta: str
    timeout_segundos: float = 10.0

    def __post_init__(self) -> None:
        url = self.url.strip().rstrip("/")
        publicavel = self.chave_publicavel.strip()
        secreta = self.chave_secreta.strip()

        if not url or not publicavel or not secreta:
            raise ValueError("A configuração do Supabase está incompleta.")
        if not url.startswith(("https://", "http://127.0.0.1:")):
            raise ValueError("A URL do Supabase é inválida.")
        if publicavel == secreta:
            raise ValueError("As chaves pública e secreta devem ser distintas.")
        if not isfinite(self.timeout_segundos) or self.timeout_segundos <= 0:
            raise ValueError("O timeout do Supabase deve ser positivo.")

        object.__setattr__(self, "url", url)
        object.__setattr__(self, "chave_publicavel", publicavel)
        object.__setattr__(self, "chave_secreta", secreta)

    @classmethod
    def do_ambiente(cls) -> ConfiguracaoSupabase:
        try:
            timeout = float(os.getenv("SUPABASE_TIMEOUT_SEGUNDOS", "10"))
            return cls(
                url=os.getenv("SUPABASE_URL", ""),
                chave_publicavel=os.getenv(
                    "SUPABASE_PUBLISHABLE_KEY",
                    "",
                ),
                chave_secreta=os.getenv("SUPABASE_SECRET_KEY", ""),
                timeout_segundos=timeout,
            )
        except (TypeError, ValueError) as erro:
            raise ErroAPI(
                status_code=503,
                codigo="SUPABASE_NAO_CONFIGURADO",
                mensagem=(
                    "O controle de acesso ainda não está configurado "
                    "no servidor."
                ),
            ) from erro


@dataclass(frozen=True, slots=True)
class UsuarioAutenticado:
    id: UUID
    email: str | None


class ProvedorAcesso(Protocol):
    def autenticar(self, token: str) -> UsuarioAutenticado: ...

    def reservar(
        self,
        *,
        usuario_id: UUID,
        chave_idempotencia: str,
        turma_id: UUID | None,
    ) -> dict[str, Any]: ...

    def consumir(self, reserva_id: UUID) -> dict[str, Any]: ...

    def estornar(
        self,
        reserva_id: UUID,
        motivo: str,
    ) -> dict[str, Any]: ...

    def listar_usuarios(self, ator_id: UUID) -> list[dict[str, Any]]: ...

    def alterar_estado_usuario(
        self,
        *,
        ator_id: UUID,
        usuario_id: UUID,
        estado: str,
    ) -> dict[str, Any]: ...

    def definir_acesso_usuario(
        self,
        *,
        ator_id: UUID,
        usuario_id: UUID,
        acesso: str,
        analises_restantes: int | None,
    ) -> dict[str, Any]: ...

    def ajustar_cotas_lote(
        self,
        *,
        ator_id: UUID,
        operacao: str,
        quantidade: int,
        usuario_ids: list[UUID] | None,
    ) -> dict[str, Any]: ...

    def alterar_papel_usuario(
        self,
        *,
        ator_id: UUID,
        usuario_id: UUID,
        papel: str,
    ) -> dict[str, Any]: ...


class ClienteSupabase:
    def __init__(
        self,
        configuracao: ConfiguracaoSupabase,
        *,
        cliente_http: Any | None = None,
    ) -> None:
        self._configuracao = configuracao
        self._http = cliente_http or httpx2.Client(
            timeout=configuracao.timeout_segundos,
        )

    def autenticar(self, token: str) -> UsuarioAutenticado:
        token = token.strip()
        if not token:
            raise _erro_token_invalido()

        try:
            resposta = self._http.get(
                f"{self._configuracao.url}/auth/v1/user",
                headers={
                    "apikey": self._configuracao.chave_publicavel,
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
        except httpx2.HTTPError as erro:
            raise ErroAPI(
                status_code=503,
                codigo="AUTENTICACAO_INDISPONIVEL",
                mensagem="Não foi possível validar o login neste momento.",
            ) from erro

        if resposta.status_code in {401, 403}:
            raise _erro_token_invalido()
        if resposta.status_code >= 400:
            raise ErroAPI(
                status_code=503,
                codigo="AUTENTICACAO_INDISPONIVEL",
                mensagem="Não foi possível validar o login neste momento.",
            )

        try:
            dados = resposta.json()
            usuario_id = UUID(str(dados["id"]))
            email_bruto = dados.get("email")
            email = str(email_bruto).strip().casefold() if email_bruto else None
        except (KeyError, TypeError, ValueError) as erro:
            raise ErroAPI(
                status_code=503,
                codigo="RESPOSTA_AUTENTICACAO_INVALIDA",
                mensagem="O provedor de login retornou uma resposta inválida.",
            ) from erro

        return UsuarioAutenticado(id=usuario_id, email=email)

    def reservar(
        self,
        *,
        usuario_id: UUID,
        chave_idempotencia: str,
        turma_id: UUID | None,
    ) -> dict[str, Any]:
        return self._rpc(
            "reservar_analise",
            {
                "p_usuario_id": str(usuario_id),
                "p_chave_idempotencia": chave_idempotencia,
                "p_turma_id": str(turma_id) if turma_id else None,
            },
        )

    def consumir(self, reserva_id: UUID) -> dict[str, Any]:
        return self._rpc(
            "consumir_reserva_analise",
            {"p_reserva_id": str(reserva_id)},
        )

    def estornar(
        self,
        reserva_id: UUID,
        motivo: str,
    ) -> dict[str, Any]:
        return self._rpc(
            "estornar_reserva_analise",
            {
                "p_reserva_id": str(reserva_id),
                "p_motivo": motivo,
            },
        )

    def listar_usuarios(self, ator_id: UUID) -> list[dict[str, Any]]:
        dados = self._rpc_json(
            "listar_usuarios_administracao",
            {"p_ator_id": str(ator_id)},
        )
        if not isinstance(dados, list) or not all(
            isinstance(item, dict) for item in dados
        ):
            raise _erro_resposta_controle_invalida()
        return dados

    def alterar_estado_usuario(
        self,
        *,
        ator_id: UUID,
        usuario_id: UUID,
        estado: str,
    ) -> dict[str, Any]:
        return self._rpc(
            "alterar_estado_usuario",
            {
                "p_ator_id": str(ator_id),
                "p_usuario_id": str(usuario_id),
                "p_estado": estado,
            },
        )

    def definir_acesso_usuario(
        self,
        *,
        ator_id: UUID,
        usuario_id: UUID,
        acesso: str,
        analises_restantes: int | None,
    ) -> dict[str, Any]:
        return self._rpc(
            "definir_acesso_usuario",
            {
                "p_ator_id": str(ator_id),
                "p_usuario_id": str(usuario_id),
                "p_acesso": acesso,
                "p_analises_restantes": analises_restantes,
            },
        )

    def ajustar_cotas_lote(
        self,
        *,
        ator_id: UUID,
        operacao: str,
        quantidade: int,
        usuario_ids: list[UUID] | None,
    ) -> dict[str, Any]:
        return self._rpc(
            "ajustar_cotas_em_lote",
            {
                "p_ator_id": str(ator_id),
                "p_operacao": operacao,
                "p_quantidade": quantidade,
                "p_usuario_ids": (
                    [str(usuario_id) for usuario_id in usuario_ids]
                    if usuario_ids is not None
                    else None
                ),
            },
        )

    def alterar_papel_usuario(
        self,
        *,
        ator_id: UUID,
        usuario_id: UUID,
        papel: str,
    ) -> dict[str, Any]:
        return self._rpc(
            "alterar_papel_usuario",
            {
                "p_ator_id": str(ator_id),
                "p_usuario_id": str(usuario_id),
                "p_papel": papel,
            },
        )

    def _rpc(
        self,
        funcao: str,
        parametros: dict[str, Any],
    ) -> dict[str, Any]:
        dados = self._rpc_json(funcao, parametros)
        if not isinstance(dados, dict):
            raise _erro_resposta_controle_invalida()
        return dados

    def _rpc_json(
        self,
        funcao: str,
        parametros: dict[str, Any],
    ) -> Any:
        try:
            resposta = self._http.post(
                f"{self._configuracao.url}/rest/v1/rpc/{funcao}",
                headers={
                    "apikey": self._configuracao.chave_secreta,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=parametros,
            )
        except httpx2.HTTPError as erro:
            raise ErroAPI(
                status_code=503,
                codigo="CONTROLE_ACESSO_INDISPONIVEL",
                mensagem=(
                    "Não foi possível consultar as permissões neste momento."
                ),
            ) from erro

        if resposta.status_code >= 400:
            raise _traduzir_erro_rpc(resposta)

        try:
            dados = resposta.json()
        except (TypeError, ValueError) as erro:
            raise _erro_resposta_controle_invalida() from erro

        return dados


def _erro_token_invalido() -> ErroAPI:
    return ErroAPI(
        status_code=401,
        codigo="TOKEN_INVALIDO",
        mensagem="Entre novamente para continuar.",
    )


def _erro_resposta_controle_invalida() -> ErroAPI:
    return ErroAPI(
        status_code=503,
        codigo="RESPOSTA_CONTROLE_ACESSO_INVALIDA",
        mensagem="O controle de acesso retornou uma resposta inválida.",
    )


def _traduzir_erro_rpc(resposta: Any) -> ErroAPI:
    try:
        corpo = resposta.json()
        mensagem = str(corpo.get("message", ""))
    except (AttributeError, TypeError, ValueError):
        mensagem = ""

    normalizada = mensagem.casefold()
    if "permissão administrativa negada" in normalizada:
        return ErroAPI(
            status_code=403,
            codigo="PERMISSAO_ADMINISTRATIVA_NEGADA",
            mensagem="Sua conta não pode realizar essa operação.",
        )
    if "somente o master" in normalizada:
        return ErroAPI(
            status_code=403,
            codigo="OPERACAO_EXCLUSIVA_MASTER",
            mensagem="Somente o master pode realizar essa operação.",
        )
    if "usuário não encontrado" in normalizada:
        return ErroAPI(
            status_code=404,
            codigo="USUARIO_NAO_ENCONTRADO",
            mensagem="O usuário selecionado não foi encontrado.",
        )
    if (
        "não pode administrar esse usuário" in normalizada
        or "master não pode ser alterado" in normalizada
        or "não pode alterar a própria conta" in normalizada
    ):
        return ErroAPI(
            status_code=409,
            codigo="USUARIO_NAO_GERENCIAVEL",
            mensagem="Essa conta não pode ser alterada por você.",
        )
    if (
        "quantidade" in normalizada
        or "saldo" in normalizada
        or "tipo de acesso" in normalizada
        or "papel de destino" in normalizada
        or "operação de cota" in normalizada
    ):
        return ErroAPI(
            status_code=422,
            codigo="AJUSTE_ADMINISTRATIVO_INVALIDO",
            mensagem="Revise os dados do ajuste administrativo.",
        )
    if "não possui análises disponíveis" in normalizada:
        return ErroAPI(
            status_code=403,
            codigo="COTA_ESGOTADA",
            mensagem="Você não possui análises disponíveis.",
        )
    if "conta não está ativa" in normalizada:
        return ErroAPI(
            status_code=403,
            codigo="CONTA_INATIVA",
            mensagem="Sua conta ainda não está liberada para análises.",
        )
    if "turma ativa" in normalizada or "não pertence à turma" in normalizada:
        return ErroAPI(
            status_code=403,
            codigo="TURMA_INDISPONIVEL",
            mensagem="Sua conta não está vinculada a uma turma ativa.",
        )
    if "chave de idempotência" in normalizada:
        return ErroAPI(
            status_code=422,
            codigo="CHAVE_IDEMPOTENCIA_INVALIDA",
            mensagem="A identificação da solicitação é inválida.",
            campo="chave_idempotencia",
        )
    if (
        "não pode mais ser consumida" in normalizada
        or "consumida não pode ser estornada" in normalizada
    ):
        return ErroAPI(
            status_code=409,
            codigo="RESERVA_INVALIDA",
            mensagem="Essa solicitação não pode mais ser finalizada.",
        )

    return ErroAPI(
        status_code=503,
        codigo="CONTROLE_ACESSO_INDISPONIVEL",
        mensagem="Não foi possível consultar as permissões neste momento.",
    )
