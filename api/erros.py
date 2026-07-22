from __future__ import annotations

from typing import Any


class ErroAPI(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        codigo: str,
        mensagem: str,
        campo: str | None = None,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.status_code = status_code
        self.codigo = codigo
        self.mensagem = mensagem
        self.campo = campo
        self.detalhes = detalhes or {}


def erro_do_motor(
    erro: Exception,
    *,
    estados_iniciais_informados: bool = False,
) -> ErroAPI:
    mensagem = str(erro)
    mensagem_normalizada = mensagem.casefold()

    if isinstance(erro, RuntimeError):
        return ErroAPI(
            status_code=422,
            codigo="RESOLUCAO_IMPOSSIVEL",
            mensagem=mensagem,
            campo="sequencia",
        )

    if "estado final deve ser igual" in mensagem_normalizada:
        codigo = "CICLO_NAO_FECHA"
        campo = "ciclo_continuo"
    elif estados_iniciais_informados and any(
        termo in mensagem_normalizada
        for termo in ("estado", "sensor", "posição", "posicao")
    ):
        codigo = "ESTADO_INICIAL_INVALIDO"
        campo = "estados_iniciais"
    else:
        codigo = "SEQUENCIA_INVALIDA"
        campo = "sequencia"

    return ErroAPI(
        status_code=422,
        codigo=codigo,
        mensagem=mensagem,
        campo=campo,
    )

