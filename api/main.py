from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.engine import VERSAO
from src.mapa import gerar_mapa_svg
from src.solver import analisar_entrada, resolver_site

from .erros import ErroAPI, erro_do_motor
from .modelos import (
    LIMITE_SEQUENCIA,
    RespostaErro,
    RespostaSaude,
    SolicitacaoAnalise,
    SolicitacaoResolucao,
)


API_VERSION = "1.0.0"


def _origens_permitidas() -> list[str]:
    return [
        origem.strip().rstrip("/")
        for origem in os.getenv("CORS_ORIGINS", "").split(",")
        if origem.strip()
    ]


app = FastAPI(
    title="API do Mapa de Karnaugh Estendido",
    version=API_VERSION,
    description=(
        "Interpreta e resolve sistemas sequenciais pelo Método do Mapa "
        "de Karnaugh Estendido."
    ),
    docs_url="/docs",
    redoc_url=None,
)

origens = _origens_permitidas()
if origens:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origens,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )


def _corpo_erro(erro: ErroAPI) -> dict[str, Any]:
    return {
        "erro": {
            "codigo": erro.codigo,
            "mensagem": erro.mensagem,
            "campo": erro.campo,
            "detalhes": erro.detalhes,
        }
    }


@app.middleware("http")
async def cabecalhos_de_seguranca(request: Request, call_next):
    resposta = await call_next(request)
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    if request.url.path.startswith("/api/"):
        resposta.headers["Cache-Control"] = "no-store"
    return resposta


@app.exception_handler(ErroAPI)
async def tratar_erro_api(_request: Request, erro: ErroAPI) -> JSONResponse:
    return JSONResponse(
        status_code=erro.status_code,
        content=_corpo_erro(erro),
    )


@app.exception_handler(RequestValidationError)
async def tratar_erro_validacao(
    _request: Request,
    erro: RequestValidationError,
) -> JSONResponse:
    erros = erro.errors()
    tipos = {str(item.get("type", "")) for item in erros}

    if "json_invalid" in tipos:
        erro_api = ErroAPI(
            status_code=400,
            codigo="JSON_INVALIDO",
            mensagem="O corpo da requisição não contém um JSON válido.",
        )
    elif any(
        item.get("type") == "string_too_long"
        or (
            item.get("loc", ())[-1:] == ("sequencia",)
            and item.get("ctx", {}).get("max_length") == LIMITE_SEQUENCIA
        )
        for item in erros
    ):
        erro_api = ErroAPI(
            status_code=413,
            codigo="ENTRADA_MUITO_GRANDE",
            mensagem=(
                f"A sequência deve possuir no máximo {LIMITE_SEQUENCIA} "
                "caracteres."
            ),
            campo="sequencia",
        )
    else:
        primeiro = erros[0] if erros else {}
        localizacao = primeiro.get("loc", ())
        campo = str(localizacao[-1]) if localizacao else None
        erro_api = ErroAPI(
            status_code=422,
            codigo="DADOS_INVALIDOS",
            mensagem="Revise os dados enviados e tente novamente.",
            campo=campo,
            detalhes={"erros": erros},
        )

    return JSONResponse(
        status_code=erro_api.status_code,
        content=_corpo_erro(erro_api),
    )


@app.get("/", include_in_schema=False)
def raiz() -> dict[str, str]:
    return {
        "nome": "API do Mapa de Karnaugh Estendido",
        "documentacao": "/docs",
        "saude": "/health",
    }


@app.get("/health", response_model=RespostaSaude, tags=["sistema"])
def verificar_saude() -> RespostaSaude:
    return RespostaSaude(
        status="ok",
        api_version=API_VERSION,
        motor_version=VERSAO,
    )


@app.post(
    "/api/v1/analises",
    response_model=dict[str, Any],
    responses={400: {"model": RespostaErro}, 422: {"model": RespostaErro}},
    tags=["karnaugh"],
)
def analisar(solicitacao: SolicitacaoAnalise) -> dict[str, Any]:
    try:
        resultado = analisar_entrada(solicitacao.sequencia)
    except (ValueError, TypeError) as erro:
        raise erro_do_motor(erro) from erro

    # ProjetoSequencial é uma representação interna e não faz parte do JSON.
    resultado.pop("projeto", None)
    return resultado


@app.post(
    "/api/v1/resolucoes",
    response_model=dict[str, Any],
    responses={
        400: {"model": RespostaErro},
        413: {"model": RespostaErro},
        422: {"model": RespostaErro},
    },
    tags=["karnaugh"],
)
def resolver(solicitacao: SolicitacaoResolucao) -> dict[str, Any]:
    try:
        resultado = resolver_site(
            sequencia=solicitacao.sequencia,
            estados_iniciais=solicitacao.estados_iniciais,
            ciclo_continuo=solicitacao.ciclo_continuo,
        )

        if solicitacao.incluir_mapa:
            mapa = gerar_mapa_svg(resultado)
            resultado["mapa_svg"] = mapa.svg
            resultado["mapa_largura"] = mapa.largura
            resultado["mapa_altura"] = mapa.altura
        else:
            resultado["mapa_svg"] = None

        return resultado
    except (ValueError, RuntimeError, TypeError) as erro:
        raise erro_do_motor(
            erro,
            estados_iniciais_informados=(
                solicitacao.estados_iniciais is not None
            ),
        ) from erro

