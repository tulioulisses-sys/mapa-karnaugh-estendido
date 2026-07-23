from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header

from api.erros import ErroAPI

from .supabase import (
    ClienteSupabase,
    ConfiguracaoSupabase,
    ProvedorAcesso,
    UsuarioAutenticado,
)


@lru_cache(maxsize=1)
def _provedor_padrao() -> ProvedorAcesso:
    return ClienteSupabase(ConfiguracaoSupabase.do_ambiente())


def obter_provedor_acesso() -> ProvedorAcesso:
    return _provedor_padrao()


def obter_token_bearer(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization:
        raise _erro_autenticacao_obrigatoria()

    esquema, separador, token = authorization.partition(" ")
    if separador != " " or esquema.casefold() != "bearer" or not token.strip():
        raise _erro_autenticacao_obrigatoria()

    return token.strip()


def obter_usuario_atual(
    token: Annotated[str, Depends(obter_token_bearer)],
    provedor: Annotated[ProvedorAcesso, Depends(obter_provedor_acesso)],
) -> UsuarioAutenticado:
    return provedor.autenticar(token)


def _erro_autenticacao_obrigatoria() -> ErroAPI:
    return ErroAPI(
        status_code=401,
        codigo="AUTENTICACAO_OBRIGATORIA",
        mensagem="Entre na sua conta para realizar uma análise.",
    )
