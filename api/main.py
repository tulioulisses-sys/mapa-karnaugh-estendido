from __future__ import annotations

import os
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.engine import VERSAO
from src.mapa import gerar_mapa_svg
from src.solver import analisar_entrada, resolver_site

from .acesso.dependencias import (
    obter_provedor_acesso,
    obter_usuario_atual,
)
from .acesso.supabase import ProvedorAcesso, UsuarioAutenticado
from .erros import ErroAPI, erro_do_motor
from .modelos import (
    LIMITE_SEQUENCIA,
    RespostaErro,
    RespostaSaude,
    SolicitacaoAcessoUsuario,
    SolicitacaoAnalise,
    SolicitacaoCotasLote,
    SolicitacaoEstadoUsuario,
    SolicitacaoPapelUsuario,
    SolicitacaoResolucao,
)


API_VERSION = "1.2.0"


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
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
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
        item.get("loc", ())[-1:] == ("sequencia",)
        and (
            item.get("type") == "string_too_long"
            or item.get("ctx", {}).get("max_length") == LIMITE_SEQUENCIA
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
        401: {"model": RespostaErro},
        403: {"model": RespostaErro},
        409: {"model": RespostaErro},
        413: {"model": RespostaErro},
        422: {"model": RespostaErro},
        500: {"model": RespostaErro},
        503: {"model": RespostaErro},
    },
    tags=["karnaugh"],
)
def resolver(
    solicitacao: SolicitacaoResolucao,
    usuario: Annotated[
        UsuarioAutenticado,
        Depends(obter_usuario_atual),
    ],
    provedor: Annotated[
        ProvedorAcesso,
        Depends(obter_provedor_acesso),
    ],
) -> dict[str, Any]:
    # Erros básicos de entrada são identificados antes de qualquer reserva.
    try:
        analisar_entrada(solicitacao.sequencia)
    except (ValueError, TypeError) as erro:
        raise erro_do_motor(erro) from erro

    reserva = provedor.reservar(
        usuario_id=usuario.id,
        chave_idempotencia=solicitacao.chave_idempotencia,
        turma_id=solicitacao.turma_id,
    )
    reserva_id = _id_reserva(reserva)
    estado_reserva = str(reserva.get("estado", ""))

    if estado_reserva in {"estornada", "expirada"}:
        raise ErroAPI(
            status_code=409,
            codigo="CHAVE_IDEMPOTENCIA_ENCERRADA",
            mensagem=(
                "Essa identificação já foi encerrada. "
                "Inicie uma nova solicitação."
            ),
            campo="chave_idempotencia",
        )

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
    except (ValueError, RuntimeError, TypeError) as erro:
        _estornar_apos_falha(
            provedor,
            reserva_id,
            "erro_entrada_ou_resolucao",
        )
        raise erro_do_motor(
            erro,
            estados_iniciais_informados=(
                solicitacao.estados_iniciais is not None
            ),
        ) from erro
    except Exception as erro:
        _estornar_apos_falha(provedor, reserva_id, "falha_interna_motor")
        raise ErroAPI(
            status_code=500,
            codigo="FALHA_INTERNA_RESOLUCAO",
            mensagem="Não foi possível concluir a análise.",
        ) from erro

    consumo = provedor.consumir(reserva_id)
    resultado["controle_acesso"] = {
        "reserva_id": str(reserva_id),
        "estado": consumo.get("estado", "consumida"),
        "acesso": reserva.get("acesso"),
        "analises_restantes": consumo.get(
            "analises_restantes",
            reserva.get("analises_restantes"),
        ),
        "requisicao_repetida": bool(
            reserva.get("idempotente") or consumo.get("idempotente")
        ),
    }
    return resultado


@app.get(
    "/api/v1/admin/usuarios",
    response_model=list[dict[str, Any]],
    responses={
        401: {"model": RespostaErro},
        403: {"model": RespostaErro},
        503: {"model": RespostaErro},
    },
    tags=["administração"],
)
def listar_usuarios_administracao(
    usuario: Annotated[
        UsuarioAutenticado,
        Depends(obter_usuario_atual),
    ],
    provedor: Annotated[
        ProvedorAcesso,
        Depends(obter_provedor_acesso),
    ],
) -> list[dict[str, Any]]:
    return provedor.listar_usuarios(usuario.id)


@app.patch(
    "/api/v1/admin/usuarios/{usuario_id}/estado",
    response_model=dict[str, Any],
    tags=["administração"],
)
def alterar_estado_usuario(
    usuario_id: UUID,
    solicitacao: SolicitacaoEstadoUsuario,
    usuario: Annotated[
        UsuarioAutenticado,
        Depends(obter_usuario_atual),
    ],
    provedor: Annotated[
        ProvedorAcesso,
        Depends(obter_provedor_acesso),
    ],
) -> dict[str, Any]:
    return provedor.alterar_estado_usuario(
        ator_id=usuario.id,
        usuario_id=usuario_id,
        estado=solicitacao.estado,
    )


@app.patch(
    "/api/v1/admin/usuarios/{usuario_id}/acesso",
    response_model=dict[str, Any],
    tags=["administração"],
)
def definir_acesso_usuario(
    usuario_id: UUID,
    solicitacao: SolicitacaoAcessoUsuario,
    usuario: Annotated[
        UsuarioAutenticado,
        Depends(obter_usuario_atual),
    ],
    provedor: Annotated[
        ProvedorAcesso,
        Depends(obter_provedor_acesso),
    ],
) -> dict[str, Any]:
    return provedor.definir_acesso_usuario(
        ator_id=usuario.id,
        usuario_id=usuario_id,
        acesso=solicitacao.acesso,
        analises_restantes=solicitacao.analises_restantes,
    )


@app.post(
    "/api/v1/admin/usuarios/cotas-em-lote",
    response_model=dict[str, Any],
    tags=["administração"],
)
def ajustar_cotas_em_lote(
    solicitacao: SolicitacaoCotasLote,
    usuario: Annotated[
        UsuarioAutenticado,
        Depends(obter_usuario_atual),
    ],
    provedor: Annotated[
        ProvedorAcesso,
        Depends(obter_provedor_acesso),
    ],
) -> dict[str, Any]:
    return provedor.ajustar_cotas_lote(
        ator_id=usuario.id,
        operacao=solicitacao.operacao,
        quantidade=solicitacao.quantidade,
        usuario_ids=solicitacao.usuario_ids,
    )


@app.patch(
    "/api/v1/admin/usuarios/{usuario_id}/papel",
    response_model=dict[str, Any],
    tags=["administração"],
)
def alterar_papel_usuario(
    usuario_id: UUID,
    solicitacao: SolicitacaoPapelUsuario,
    usuario: Annotated[
        UsuarioAutenticado,
        Depends(obter_usuario_atual),
    ],
    provedor: Annotated[
        ProvedorAcesso,
        Depends(obter_provedor_acesso),
    ],
) -> dict[str, Any]:
    return provedor.alterar_papel_usuario(
        ator_id=usuario.id,
        usuario_id=usuario_id,
        papel=solicitacao.papel,
    )


def _id_reserva(reserva: dict[str, Any]) -> UUID:
    try:
        return UUID(str(reserva["reserva_id"]))
    except (KeyError, TypeError, ValueError) as erro:
        raise ErroAPI(
            status_code=503,
            codigo="RESPOSTA_CONTROLE_ACESSO_INVALIDA",
            mensagem="O controle de acesso retornou uma resposta inválida.",
        ) from erro


def _estornar_apos_falha(
    provedor: ProvedorAcesso,
    reserva_id: UUID,
    motivo: str,
) -> None:
    try:
        provedor.estornar(reserva_id, motivo)
    except ErroAPI as erro:
        raise ErroAPI(
            status_code=503,
            codigo="ESTORNO_PENDENTE",
            mensagem=(
                "A análise falhou e a reserva será liberada automaticamente."
            ),
        ) from erro
