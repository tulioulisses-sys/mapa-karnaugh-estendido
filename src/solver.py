from __future__ import annotations

from typing import Any, Mapping

from sympy import Symbol

from .engine import (
    _avaliar,
    _formatar_literal,
    _pontos_alcancaveis,
    _rotulos_eventos,
    construir_etapas,
    interpretar_sequencia,
    resolver as _resolver,
)

__all__ = [
    "analisar_entrada",
    "inferir_estados_iniciais",    
    "validar_estados",
    "resolver_site",
    "interpretar_sequencia",
    "construir_etapas",
]


def _estado_dict(valores: tuple[int, ...], nomes: tuple[str, ...]) -> dict[str, int]:
    return {nome: int(valor) for nome, valor in zip(nomes, valores)}


def _formatar_etapa(comandos: list[str]) -> str:
    return comandos[0] if len(comandos) == 1 else "(" + " ∥ ".join(comandos) + ")"

def _formatar_fatores(
    fatores,
    atuadores: tuple[str, ...],
    memorias: tuple[str, ...],
) -> str:
    """
    Converte uma lista de literais booleanos para a
    notação utilizada nas equações do método.
    """

    textos = [
        _formatar_literal(
            fator,
            atuadores,
            memorias,
        )
        for fator in fatores
    ]

    if not textos:
        return "1"

    return ".".join(textos)


def _formatar_ponto_perigoso(
    valores: tuple[int, ...],
    atuadores: tuple[str, ...],
    memorias: tuple[str, ...],
) -> str:
    """
    Formata apenas os estados dos atuadores e das
    memórias. O último valor corresponde a S e não
    precisa aparecer no ponto do mapa.
    """

    nomes = atuadores + memorias
    valores_mapa = valores[:len(nomes)]

    return " · ".join(
        f"{nome.lower()}{valor}"
        for nome, valor in zip(
            nomes,
            valores_mapa,
        )
    )


def _obter_contracomando(comando: str) -> str:
    """
    Retorna o comando de sentido oposto.
    """

    dispositivo = comando[:-1]
    sentido = comando[-1]

    sentido_oposto = (
        "-"
        if sentido == "+"
        else "+"
    )

    return f"{dispositivo}{sentido_oposto}"


def _montar_resolucao_metodo(
    resultado,
) -> list[dict[str, object]]:
    """
    Monta a resolução respeitando as etapas do método:

    1. condição mínima;
    2. qualificação entre comando e contracomando;
    3. verificação dos pontos perigosos;
    4. qualificação complementar;
    5. equação final.
    """

    linhas: list[dict[str, object]] = []

    todas_saidas = {
        saida
        for evento in resultado.eventos
        for saida in evento.saidas
    }

    for numero, evento in enumerate(
        resultado.eventos,
        start=1,
    ):
        qualificadores_contracomando = list(
            evento.qualificadores_contracomando
        )

        qualificadores_complementares = list(
            evento.qualificadores_complementares
        )

        quantidade_acrescentada = (
            len(qualificadores_contracomando)
            + len(qualificadores_complementares)
        )

        # Os fatores_ordenados estão organizados como:
        #
        # condição mínima
        # + qualificadores de contracomando
        # + qualificadores complementares
        if quantidade_acrescentada:
            fatores_base = list(
                evento.fatores_ordenados[
                    :-quantidade_acrescentada
                ]
            )
        else:
            fatores_base = list(
                evento.fatores_ordenados
            )

        fatores_qualificados = (
            fatores_base
            + qualificadores_contracomando
        )

        condicao_minima = _formatar_fatores(
            fatores_base,
            resultado.atuadores,
            resultado.memorias,
        )

        qualificacao_contracomando = (
            _formatar_fatores(
                qualificadores_contracomando,
                resultado.atuadores,
                resultado.memorias,
            )
            if qualificadores_contracomando
            else "Nenhum"
        )

        equacao_qualificada = _formatar_fatores(
            fatores_qualificados,
            resultado.atuadores,
            resultado.memorias,
        )

        qualificacao_complementar = (
            _formatar_fatores(
                qualificadores_complementares,
                resultado.atuadores,
                resultado.memorias,
            )
            if qualificadores_complementares
            else "Nenhum"
        )

        pontos_perigosos = []

        for valores in evento.pontos_perigosos:
            ponto_texto = _formatar_ponto_perigoso(
                valores,
                resultado.atuadores,
                resultado.memorias,
            )

            if ponto_texto not in pontos_perigosos:
                pontos_perigosos.append(
                    ponto_texto
                )

        comandos = " ∥ ".join(
            evento.saidas
        )

        contracomandos = []

        for comando in evento.saidas:
            oposto = _obter_contracomando(
                comando
            )

            if oposto in todas_saidas:
                contracomandos.append(
                    oposto
                )
            else:
                contracomandos.append(
                    f"{oposto} não ocorre"
                )

        termo_final = _formatar_fatores(
            evento.fatores_ordenados,
            resultado.atuadores,
            resultado.memorias,
        )

        equacoes_qualificadas = " | ".join(
            f"{saida} = {equacao_qualificada}"
            for saida in evento.saidas
        )

        equacoes_finais = " | ".join(
            f"{saida} = {termo_final}"
            for saida in evento.saidas
        )

        linhas.append(
            {
                "Passo": numero,
                "Comando": comandos,
                "Condição mínima": condicao_minima,
                "Contracomando": " ∥ ".join(
                    contracomandos
                ),
                "Qualificador de diferenciação": (
                    qualificacao_contracomando
                ),
                "Equação qualificada": (
                    equacoes_qualificadas
                ),
                "Pontos perigosos": (
                    "; ".join(pontos_perigosos)
                    if pontos_perigosos
                    else "Nenhum"
                ),
                "Qualificador complementar": (
                    qualificacao_complementar
                ),
                "Equação final": equacoes_finais,
            }
        )

    return linhas

def inferir_estados_iniciais(
    sequencia: str,
) -> dict[str, int]:
    """
    Determina automaticamente o estado inicial dos atuadores
    a partir da primeira ação de cada um.

    Primeira ação com +:
        o atuador começa recuado, estado 0.

    Primeira ação com -:
        o atuador começa avançado, estado 1.
    """

    grupos = interpretar_sequencia(sequencia)
    estados_iniciais: dict[str, int] = {}

    for grupo in grupos:
        for acao in grupo:
            atuador = acao.atuador

            # Somente a primeira ação de cada atuador importa.
            if atuador in estados_iniciais:
                continue

            comando = acao.nome.strip()

            if comando.endswith("+"):
                estados_iniciais[atuador] = 0

            elif comando.endswith("-"):
                estados_iniciais[atuador] = 1

            else:
                raise ValueError(
                    f"Não foi possível determinar o estado "
                    f"inicial do atuador {atuador}."
                )

    return estados_iniciais

def _formatar_ponto(
    valores: tuple[int, ...],
    nomes: list[str],
) -> str:
    sinais = []

    for nome, valor in zip(nomes, valores):
        # S é considerado acionado durante a verificação,
        # mas não precisa aparecer em cada ponto.
        if nome == "S":
            continue

        sinais.append(
            f"{nome.lower()}{valor}"
        )

    return " · ".join(sinais)


def analisar_entrada(sequencia: str) -> dict[str, Any]:
    """
    Analisa a sequência, determina automaticamente os estados
    iniciais e valida toda a evolução dos atuadores.
    """

    grupos = interpretar_sequencia(sequencia)

    estados_iniciais = inferir_estados_iniciais(
        sequencia
    )

    atuadores, inicial_validado, etapas_construidas = (
        construir_etapas(
            sequencia,
            estado_inicial=estados_iniciais,
        )
    )

    etapas = [
        [acao.nome for acao in grupo]
        for grupo in grupos
    ]

    return {
        "atuadores": list(atuadores),
        "etapas": etapas,
        "quantidade_etapas": len(etapas_construidas),
        "sequencia_formatada": " → ".join(
            _formatar_etapa(comandos)
            for comandos in etapas
        ),
        "estado_inicial": dict(inicial_validado),
    }


def validar_estados(
    sequencia: str,
    estados_iniciais: Mapping[str, int | bool],
) -> dict[str, Any]:
    atuadores, inicial, etapas = construir_etapas(
        sequencia,
        estado_inicial=estados_iniciais,
    )

    return {
        "atuadores": list(atuadores),
        "estado_inicial": dict(inicial),
        "quantidade_etapas": len(etapas),
    }


def _montar_resolucao_detalhada(resultado) -> list[dict[str, str]]:
    eventos = resultado.eventos
    nomes = list(resultado.atuadores) + list(resultado.memorias) + ["S"]
    simbolos = [Symbol(nome, boolean=True) for nome in nomes]
    rotulos = _rotulos_eventos(eventos, True)
    pontos = _pontos_alcancaveis(eventos)

    linhas: list[dict[str, str]] = []

    for indice, evento in enumerate(eventos):
        fatores = [
            _formatar_literal(
                fator,
                resultado.atuadores,
                resultado.memorias,
            )
            for fator in evento.fatores_ordenados
        ]

        if indice == 0:
            quantidade_base = 1
        else:
            anterior = eventos[indice - 1]
            quantidade_base = len(anterior.acoes) if anterior.tipo == "atuador" else 1

        fatores_base = fatores[:quantidade_base]
        qualificadores = fatores[quantidade_base:]

        condicao_basica = (
            " · ".join(fatores_base)
            if fatores_base
            else "1"
        )

        qualificacao = (
            " · ".join(qualificadores)
            if qualificadores
            else "Nenhum"
        )

        perigosos: list[str] = []
        for ponto in pontos:
            bloqueado = any(
                rotulos[saida][ponto.evento] == "0"
                for saida in evento.saidas
            )
            if bloqueado and _avaliar(evento.base, simbolos, ponto.valores):
                texto = _formatar_ponto(ponto.valores, nomes)
                if texto not in perigosos:
                    perigosos.append(texto)

        equacoes_finais = [
            f"{saida} = {resultado.equacoes[saida]}"
            for saida in evento.saidas
        ]

        linhas.append(
            {
                "Comando": " e ".join(
                    evento.saidas
                ),
                "Condição básica": condicao_basica,
                "Pontos perigosos encontrados": (
                    "; ".join(perigosos)
                    if perigosos
                    else "Nenhum"
                ),
                "Qualificador acrescentado": qualificacao,
                "Equação final": " | ".join(
                    equacoes_finais
                ),
            }
        )

    return linhas


def resolver_site(
    sequencia: str,
    estados_iniciais: Mapping[str, int | bool] | None = None,
    *,
    ciclo_continuo: bool = False,
) -> dict[str, Any]:
    
    if estados_iniciais is None:
        estados_iniciais = inferir_estados_iniciais(
            sequencia
        )


    resultado = _resolver(
        sequencia,
        estado_inicial=estados_iniciais,
        ciclo_continuo=ciclo_continuo,
    )

    etapas = []
    for etapa in resultado.etapas:
        comandos = [acao.nome for acao in etapa.acoes]
        etapas.append(
            {
                "numero": etapa.indice + 1,
                "comandos": comandos,
                "comando_texto": _formatar_etapa(comandos),
                "simultaneo": len(comandos) > 1,
                "estado_antes": _estado_dict(etapa.antes, resultado.atuadores),
                "estado_depois": _estado_dict(etapa.depois, resultado.atuadores),
                "estados_intermediarios": [
                    _estado_dict(estado, resultado.atuadores)
                    for estado in etapa.intermediarios
                ],
                "fase": etapa.fase,
                "codigo_memorias": _estado_dict(
                    etapa.codigo,
                    resultado.memorias,
                ),
            }
        )


    eventos_mapa = []

    for evento in resultado.eventos:
        eventos_mapa.append(
            {
                "tipo": evento.tipo,
                "saidas": list(evento.saidas),

                "estado_fisico": _estado_dict(
                    evento.fisico,
                    resultado.atuadores,
                ),

                "codigo_memorias": _estado_dict(
                    evento.codigo,
                    resultado.memorias,
                ),

                "estados_intermediarios": [
                    _estado_dict(
                        estado,
                        resultado.atuadores,
                    )
                    for estado in evento.intermediarios
                ],
            }
        )

    return {
        "atuadores": list(resultado.atuadores),
        "estado_inicial": dict(resultado.estado_inicial),
        "etapas": etapas,
        "memorias": list(resultado.memorias),
        "quantidade_memorias": len(resultado.memorias),
        "equacoes": dict(resultado.equacoes),
        "equacoes_memorias": dict(resultado.equacoes_memorias),
        "resolucao": _montar_resolucao_metodo(
            resultado
        ),
        "eventos_mapa": eventos_mapa,        
        "validacoes": list(resultado.validacoes),
        "observacoes": list(resultado.observacoes),
    }