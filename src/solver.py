from __future__ import annotations

from typing import Any, Mapping, Sequence

from sympy import Symbol

from .engine import (
    ContextoFisico,
    VERSAO,
    Evento,
    Resultado,
    _avaliar,
    _formatar_literal,
    _pontos_alcancaveis,
    _rotulos_eventos,
    construir_etapas,
    interpretar_sequencia,
    resolver as _resolver,
)
from .modelos import ProjetoSequencial
from .parser_entrada import formatar_projeto, interpretar_entrada


__all__ = [
    "analisar_entrada",
    "inferir_estados_iniciais",
    "inferir_sensores_iniciais",
    "validar_estados",
    "resolver_site",
    "interpretar_sequencia",
    "construir_etapas",
]


def _estado_logico_dict(
    valores: Sequence[int],
    nomes: Sequence[str],
) -> dict[str, int]:
    """Converte uma tupla binária em dicionário nome -> 0/1."""

    return {
        str(nome): int(valor)
        for nome, valor in zip(nomes, valores)
    }


def _codigo_memorias_dict(
    valores: Sequence[int],
    memorias: Sequence[str],
) -> dict[str, int]:
    return _estado_logico_dict(valores, memorias)


def _sensores_ativos_dict(
    valores: tuple[int, ...],
    contexto: ContextoFisico,
) -> dict[str, str]:
    """Retorna o sensor ativo de cada atuador no estado informado."""

    return {
        atuador: contexto.sensor_ativo(valores, atuador)
        for atuador in contexto.atuadores
    }


def _indices_posicoes_dict(
    valores: tuple[int, ...],
    contexto: ContextoFisico,
) -> dict[str, int]:
    """
    Retorna o índice da posição ativa de cada atuador.

    Esse formato mantém compatibilidade com a interface atual:

        {"A": 0, "B": 2, "C": 1}

    é exibido como a0 · b2 · c1.
    """

    resultado: dict[str, int] = {}

    for atuador in contexto.atuadores:
        sensor = contexto.sensor_ativo(valores, atuador)
        configuracao = contexto.configuracoes[atuador]
        resultado[atuador] = configuracao.indice_sensor(sensor)

    return resultado


def _formatar_estado_fisico(
    valores: tuple[int, ...],
    contexto: ContextoFisico,
) -> str:
    return " · ".join(
        contexto.sensor_ativo(valores, atuador)
        for atuador in contexto.atuadores
    )


def _formatar_ponto_perigoso(
    valores: tuple[int, ...],
    resultado: Resultado,
) -> str:
    """
    Formata o ponto usando os sensores físicos ativos e os estados das
    memórias. O último valor da tupla corresponde ao sinal S.
    """

    quantidade_fisica = resultado.contexto_fisico.quantidade_variaveis
    fisico = valores[:quantidade_fisica]

    inicio_memorias = quantidade_fisica
    fim_memorias = inicio_memorias + len(resultado.memorias)
    codigo = valores[inicio_memorias:fim_memorias]

    partes = [
        resultado.contexto_fisico.sensor_ativo(
            tuple(fisico),
            atuador,
        )
        for atuador in resultado.atuadores
    ]

    partes.extend(
        f"{memoria.lower()}{int(valor)}"
        for memoria, valor in zip(resultado.memorias, codigo)
    )

    inicio_externas = fim_memorias
    fim_externas = inicio_externas + len(resultado.entradas_externas)
    externas = valores[inicio_externas:fim_externas]

    partes.extend(
        f"{nome}={int(valor)}"
        for nome, valor in zip(resultado.entradas_externas, externas)
    )

    return " · ".join(partes)


def _formatar_etapa(comandos: Sequence[str]) -> str:
    comandos = list(comandos)

    if not comandos:
        return "—"

    if len(comandos) == 1:
        return comandos[0]

    return "(" + " ∥ ".join(comandos) + ")"


def _formatar_fatores(
    fatores: Sequence[object],
    resultado: Resultado,
) -> str:
    textos = [
        _formatar_literal(
            fator,
            resultado.contexto_fisico,
            resultado.memorias,
        )
        for fator in fatores
    ]

    return ".".join(textos) if textos else "1"


def _literal_entrada_externa(nome: str, valor: int) -> str:
    """Formata uma entrada externa na notação booleana do método."""

    return str(nome) if int(valor) else f"{nome}'"


def _formatar_condicoes_externas(
    condicoes: Sequence[tuple[str, int]],
    *,
    descritivo: bool = False,
) -> str:
    if not condicoes:
        return "Nenhuma"

    if descritivo:
        return " e ".join(
            f"{nome} = {int(valor)}"
            for nome, valor in condicoes
        )

    return ".".join(
        _literal_entrada_externa(nome, valor)
        for nome, valor in condicoes
    )


def _loop_para_dict(loop: object) -> dict[str, Any]:
    """Converte LoopConfig em um dicionário estável para a interface."""

    inicio = int(getattr(loop, "inicio"))
    fim = int(getattr(loop, "fim"))
    sensor = str(getattr(loop, "sensor"))
    repetir_quando = int(getattr(loop, "repetir_quando"))
    sair_quando = int(getattr(loop, "sair_quando"))

    return {
        "inicio": inicio,
        "fim": fim,
        "etapa_inicial": inicio + 1,
        "etapa_final": fim + 1,
        "retorna_para_etapa": inicio + 1,
        "continua_na_etapa": fim + 2,
        "sensor": sensor,
        "repetir_quando": repetir_quando,
        "sair_quando": sair_quando,
        "condicao_repeticao": {sensor: repetir_quando},
        "condicao_saida": {sensor: sair_quando},
        "condicao_repeticao_texto": (
            f"{sensor} = {repetir_quando}"
        ),
        "condicao_saida_texto": f"{sensor} = {sair_quando}",
        "literal_repeticao": _literal_entrada_externa(
            sensor,
            repetir_quando,
        ),
        "literal_saida": _literal_entrada_externa(
            sensor,
            sair_quando,
        ),
        "quantidade_etapas": fim - inicio + 1,
        "descricao": str(
            getattr(
                loop,
                "descricao",
                f"etapas {inicio + 1} a {fim + 1}",
            )
        ),
    }


# ---------------------------------------------------------------------------
# Descrição compacta da entrada
# ---------------------------------------------------------------------------


def _registro_rotulos_projeto(
    projeto: ProjetoSequencial,
) -> dict[tuple[str, str, str], str]:
    """
    Replica a identificação dos comandos lógicos utilizada pelo motor.

    Quando uma mesma saída possui vários destinos, são criados rótulos como
    B+(1), B+(2) e B+(3).
    """

    destinos_por_saida: dict[str, list[str]] = {}

    for etapa in projeto.etapas:
        for movimento in etapa.movimentos:
            saida = f"{movimento.atuador}{movimento.sentido}"
            destinos = destinos_por_saida.setdefault(saida, [])

            if movimento.sensor_destino not in destinos:
                destinos.append(movimento.sensor_destino)

    registro: dict[tuple[str, str, str], str] = {}

    for saida, destinos in destinos_por_saida.items():
        atuador = saida[:-1]
        sentido = saida[-1]
        varios_destinos = len(destinos) > 1

        for numero, sensor in enumerate(destinos, start=1):
            registro[(atuador, sentido, sensor)] = (
                f"{saida}({numero})"
                if varios_destinos
                else saida
            )

    return registro


def _descricao_movimento_entrada(
    projeto: ProjetoSequencial,
    atuador: str,
    sentido: str,
    sensor_destino: str,
) -> str:
    configuracao = projeto.atuadores[atuador]

    destino_padrao = (
        configuracao.sensor_maximo
        if sentido == "+"
        else configuracao.sensor_minimo
    )

    if (
        configuracao.quantidade_posicoes == 2
        and sensor_destino == destino_padrao
    ):
        return f"{atuador}{sentido}"

    return f"{atuador}{sentido} até {sensor_destino}"


def _formatar_projeto_compacto(
    projeto: ProjetoSequencial,
) -> str:
    loops_por_inicio = {
        loop.inicio: loop
        for loop in projeto.loops
    }

    partes: list[str] = []
    indice = 0

    def descricao_etapa(indice_etapa: int) -> str:
        etapa = projeto.etapas[indice_etapa]
        movimentos = [
            _descricao_movimento_entrada(
                projeto,
                movimento.atuador,
                movimento.sentido,
                movimento.sensor_destino,
            )
            for movimento in etapa.movimentos
        ]
        return _formatar_etapa(movimentos)

    while indice < len(projeto.etapas):
        loop = loops_por_inicio.get(indice)

        if loop is None:
            partes.append(descricao_etapa(indice))
            indice += 1
            continue

        conteudo = ", ".join(
            descricao_etapa(posicao)
            for posicao in range(loop.inicio, loop.fim + 1)
        )

        partes.append(
            f"[{conteudo}] enquanto "
            f"{loop.sensor}={loop.repetir_quando}"
        )
        indice = loop.fim + 1

    return " → ".join(partes)


def _projeto_para_etapas_entrada(
    projeto: ProjetoSequencial,
) -> list[list[str]]:
    registro = _registro_rotulos_projeto(projeto)

    return [
        [
            registro[
                (
                    movimento.atuador,
                    movimento.sentido,
                    movimento.sensor_destino,
                )
            ]
            for movimento in etapa.movimentos
        ]
        for etapa in projeto.etapas
    ]


def _estado_inicial_indices_projeto(
    projeto: ProjetoSequencial,
) -> dict[str, int]:
    return {
        configuracao.nome: configuracao.indice_sensor(
            configuracao.sensor_inicial
        )
        for configuracao in projeto.atuadores.values()
    }


# ---------------------------------------------------------------------------
# Análise e validação da entrada
# ---------------------------------------------------------------------------


def inferir_sensores_iniciais(
    sequencia: str | ProjetoSequencial,
) -> dict[str, str]:
    """Retorna o sensor inicial inferido para cada atuador."""

    projeto = (
        sequencia
        if isinstance(sequencia, ProjetoSequencial)
        else interpretar_entrada(sequencia)
    )

    projeto.validar()

    return {
        configuracao.nome: configuracao.sensor_inicial
        for configuracao in projeto.atuadores.values()
    }


def inferir_estados_iniciais(
    sequencia: str | ProjetoSequencial,
) -> dict[str, int]:
    """
    Retorna o índice inicial de cada atuador.

    Para um atuador tradicional, os valores continuam sendo 0 e 1. Para um
    atuador multiposição, podem ser retornados 0, 1, 2, 3 etc.
    """

    projeto = (
        sequencia
        if isinstance(sequencia, ProjetoSequencial)
        else interpretar_entrada(sequencia)
    )

    projeto.validar()
    return _estado_inicial_indices_projeto(projeto)


def analisar_entrada(
    sequencia: str | ProjetoSequencial,
) -> dict[str, Any]:
    """
    Interpreta e valida a entrada sem executar ainda o cálculo das equações.

    A função aceita a sequência textual ou um ProjetoSequencial montado pelo
    futuro editor visual.
    """

    projeto = (
        sequencia
        if isinstance(sequencia, ProjetoSequencial)
        else interpretar_entrada(sequencia)
    )

    projeto.validar()

    etapas = _projeto_para_etapas_entrada(projeto)
    multiposicao = [
        nome
        for nome, configuracao in projeto.atuadores.items()
        if configuracao.quantidade_posicoes > 2
    ]

    loops = [
        _loop_para_dict(loop)
        for loop in projeto.loops
    ]

    return {
        "atuadores": list(projeto.atuadores),
        "sensores_por_atuador": {
            nome: list(configuracao.sensores)
            for nome, configuracao in projeto.atuadores.items()
        },
        "atuadores_multiposicao": multiposicao,
        "possui_atuador_multiposicao": bool(multiposicao),
        "etapas": etapas,
        "quantidade_etapas": len(projeto.etapas),
        "sequencia_formatada": _formatar_projeto_compacto(projeto),
        "sequencia_normalizada": formatar_projeto(projeto),
        "estado_inicial": _estado_inicial_indices_projeto(projeto),
        "sensores_iniciais": inferir_sensores_iniciais(projeto),
        "entradas_externas": list(projeto.entradas_externas),
        "loops": loops,
        "possui_loop": bool(loops),
        "sinal_partida": projeto.sinal_partida,
        "projeto": projeto,
    }


def validar_estados(
    sequencia: str | ProjetoSequencial,
    estados_iniciais: Mapping[str, int | bool | str],
) -> dict[str, Any]:
    """Valida estados iniciais informados manualmente."""

    projeto = (
        sequencia
        if isinstance(sequencia, ProjetoSequencial)
        else interpretar_entrada(sequencia)
    )

    atuadores, inicial, etapas = construir_etapas(
        projeto,
        estado_inicial=estados_iniciais,
    )

    indices: dict[str, int] = {}

    for nome, sensor in inicial.items():
        indices[nome] = projeto.atuadores[nome].indice_sensor(sensor)

    return {
        "atuadores": list(atuadores),
        "estado_inicial": indices,
        "sensores_iniciais": dict(inicial),
        "quantidade_etapas": len(etapas),
    }


# ---------------------------------------------------------------------------
# Resolução detalhada do método
# ---------------------------------------------------------------------------


def _contracomandos_evento(
    evento: Evento,
    resultado: Resultado,
) -> list[str]:
    todos = [
        comando
        for outro_evento in resultado.eventos
        for comando in outro_evento.comandos
    ]

    resposta: list[str] = []

    for comando in evento.comandos:
        sentido_oposto = "-" if comando.sentido == "+" else "+"
        opostos = [
            outro.rotulo
            for outro in todos
            if outro.dispositivo == comando.dispositivo
            and outro.sentido == sentido_oposto
        ]

        if opostos:
            for rotulo in opostos:
                if rotulo not in resposta:
                    resposta.append(rotulo)
        else:
            resposta.append(
                f"{comando.dispositivo}{sentido_oposto} não ocorre"
            )

    return resposta


def _montar_resolucao_metodo(
    resultado: Resultado,
) -> list[dict[str, object]]:
    """
    Monta a tabela didática do método, separando:

    1. condição mínima;
    2. qualificação comando/contracomando;
    3. contato de parada de posições intermediárias;
    4. pontos perigosos;
    5. qualificação complementar;
    6. equação final.
    """

    linhas: list[dict[str, object]] = []

    for numero, evento in enumerate(resultado.eventos, start=1):
        qualificadores_contracomando = list(
            evento.qualificadores_contracomando
        )
        qualificadores_complementares = list(
            evento.qualificadores_complementares
        )
        qualificadores_parada = list(
            evento.qualificadores_parada
        )

        quantidade_adicionada = (
            len(qualificadores_contracomando)
            + len(qualificadores_complementares)
            + len(qualificadores_parada)
        )

        if quantidade_adicionada:
            fatores_base = list(
                evento.fatores_ordenados[:-quantidade_adicionada]
            )
        else:
            fatores_base = list(evento.fatores_ordenados)

        fatores_qualificados = (
            fatores_base
            + qualificadores_contracomando
            + qualificadores_parada
        )

        condicao_minima = _formatar_fatores(
            fatores_base,
            resultado,
        )

        condicao_externa = _formatar_condicoes_externas(
            evento.condicoes_externas,
        )
        restricao_ramo = _formatar_condicoes_externas(
            evento.restricoes_externas,
            descritivo=True,
        )

        qualificacao_contracomando = (
            _formatar_fatores(
                qualificadores_contracomando,
                resultado,
            )
            if qualificadores_contracomando
            else "Nenhum"
        )

        contato_parada = (
            _formatar_fatores(
                qualificadores_parada,
                resultado,
            )
            if qualificadores_parada
            else "Nenhum"
        )

        equacao_qualificada = _formatar_fatores(
            fatores_qualificados,
            resultado,
        )

        qualificacao_complementar = (
            _formatar_fatores(
                qualificadores_complementares,
                resultado,
            )
            if qualificadores_complementares
            else "Nenhum"
        )

        pontos_perigosos: list[str] = []

        for valores in evento.pontos_perigosos:
            ponto_texto = _formatar_ponto_perigoso(
                valores,
                resultado,
            )

            if ponto_texto not in pontos_perigosos:
                pontos_perigosos.append(ponto_texto)

        comandos = " ∥ ".join(evento.saidas)
        contracomandos = _contracomandos_evento(evento, resultado)

        termo_final = _formatar_fatores(
            evento.fatores_ordenados,
            resultado,
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
                "Condição externa": condicao_externa,
                "Restrição do ramo": restricao_ramo,
                "Contracomando": " ∥ ".join(contracomandos),
                "Qualificador de diferenciação": (
                    qualificacao_contracomando
                ),
                "Contato de parada": contato_parada,
                "Equação qualificada": equacoes_qualificadas,
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


def _montar_resolucao_detalhada(
    resultado: Resultado,
) -> list[dict[str, str]]:
    """Versão compacta mantida para compatibilidade interna."""

    nomes = [
        *resultado.contexto_fisico.variaveis,
        *resultado.memorias,
        *resultado.entradas_externas,
        "S",
    ]
    simbolos = [
        Symbol(nome, boolean=True)
        for nome in nomes
    ]
    rotulos = _rotulos_eventos(resultado.eventos, True)
    pontos = _pontos_alcancaveis(
        resultado.eventos,
        resultado.entradas_externas,
    )

    linhas: list[dict[str, str]] = []

    for evento in resultado.eventos:
        perigosos: list[str] = []

        for ponto in pontos:
            bloqueado = any(
                rotulos[chave][ponto.evento] == "0"
                for chave in evento.chaves_saidas
            )

            if bloqueado and _avaliar(
                evento.base,
                simbolos,
                ponto.valores,
            ):
                texto = _formatar_ponto_perigoso(
                    ponto.valores,
                    resultado,
                )

                if texto not in perigosos:
                    perigosos.append(texto)

        linhas.append(
            {
                "Comando": " e ".join(evento.saidas),
                "Condição básica": _formatar_fatores(
                    list(evento.base.args)
                    if getattr(evento.base, "func", None).__name__ == "And"
                    else [evento.base],
                    resultado,
                ),
                "Pontos perigosos encontrados": (
                    "; ".join(perigosos)
                    if perigosos
                    else "Nenhum"
                ),
                "Qualificador acrescentado": _formatar_fatores(
                    [
                        *evento.qualificadores_contracomando,
                        *evento.qualificadores_complementares,
                        *evento.qualificadores_parada,
                    ],
                    resultado,
                )
                if (
                    evento.qualificadores_contracomando
                    or evento.qualificadores_complementares
                    or evento.qualificadores_parada
                )
                else "Nenhum",
                "Equação final": " | ".join(
                    f"{saida} = "
                    f"{resultado.equacoes_comandos.get(saida, '—')}"
                    for saida in evento.saidas
                ),
            }
        )

    return linhas


# ---------------------------------------------------------------------------
# Conversão dos resultados do motor para a interface
# ---------------------------------------------------------------------------


def _aplicar_acoes_evento(
    estado: tuple[int, ...],
    evento: Evento,
) -> tuple[int, ...]:
    novo = list(estado)

    for acao in evento.acoes:
        for indice, valor in acao.alteracoes:
            novo[indice] = int(valor)

    return tuple(novo)


def _codigo_destino_evento(
    evento: Evento,
    memorias: tuple[str, ...],
) -> tuple[int, ...]:
    if evento.tipo != "memoria" or not evento.comandos:
        return tuple(evento.codigo)

    comando = evento.comandos[0]

    if comando.dispositivo not in memorias:
        return tuple(evento.codigo)

    indice = memorias.index(comando.dispositivo)
    novo = list(evento.codigo)
    novo[indice] = 1 if comando.sentido == "+" else 0
    return tuple(novo)


def _dados_estado(
    estado: tuple[int, ...],
    contexto: ContextoFisico,
) -> dict[str, Any]:
    return {
        "indices": _indices_posicoes_dict(estado, contexto),
        "sensores_ativos": _sensores_ativos_dict(estado, contexto),
        "logico": _estado_logico_dict(estado, contexto.variaveis),
        "texto": _formatar_estado_fisico(estado, contexto),
    }


def _montar_etapas_saida(
    resultado: Resultado,
) -> list[dict[str, Any]]:
    etapas: list[dict[str, Any]] = []
    contexto = resultado.contexto_fisico

    for etapa in resultado.etapas:
        comandos = [acao.nome for acao in etapa.acoes]
        antes = _dados_estado(etapa.antes, contexto)
        depois = _dados_estado(etapa.depois, contexto)

        intermediarios = [
            _dados_estado(estado, contexto)
            for estado in etapa.intermediarios
        ]

        movimentos = [
            {
                "atuador": acao.atuador,
                "sentido": acao.sentido,
                "saida": acao.saida_fisica,
                "comando": acao.nome,
                "sensor_origem": acao.sensor_origem,
                "sensor_destino": acao.sensor_destino,
                "requer_parada": acao.requer_parada,
            }
            for acao in etapa.acoes
        ]

        loops_etapa = [
            _loop_para_dict(loop)
            for loop in resultado.loops
            if loop.inicio <= etapa.indice <= loop.fim
        ]

        condicoes_externas = dict(etapa.condicoes_externas)
        restricoes_externas = dict(etapa.restricoes_externas)

        etapas.append(
            {
                "numero": etapa.indice + 1,
                "comandos": comandos,
                "saidas_fisicas": [
                    acao.saida_fisica
                    for acao in etapa.acoes
                ],
                "comando_texto": _formatar_etapa(comandos),
                "simultaneo": len(comandos) > 1,
                "movimentos": movimentos,

                # Campos históricos usados pela interface atual.
                "estado_antes": antes["indices"],
                "estado_depois": depois["indices"],
                "estados_intermediarios": [
                    estado["indices"]
                    for estado in intermediarios
                ],

                # Novos campos explícitos.
                "sensores_ativos_antes": antes["sensores_ativos"],
                "sensores_ativos_depois": depois["sensores_ativos"],
                "sensores_ativos_intermediarios": [
                    estado["sensores_ativos"]
                    for estado in intermediarios
                ],
                "estado_logico_antes": antes["logico"],
                "estado_logico_depois": depois["logico"],
                "estados_logicos_intermediarios": [
                    estado["logico"]
                    for estado in intermediarios
                ],
                "estado_antes_texto": antes["texto"],
                "estado_depois_texto": depois["texto"],

                # Condições e pertencimento a loops.
                "condicoes_externas": condicoes_externas,
                "restricoes_externas": restricoes_externas,
                "condicao_externa_texto": (
                    _formatar_condicoes_externas(
                        etapa.condicoes_externas,
                        descritivo=True,
                    )
                ),
                "literal_condicao_externa": (
                    _formatar_condicoes_externas(
                        etapa.condicoes_externas,
                    )
                ),
                "restricao_ramo_texto": (
                    _formatar_condicoes_externas(
                        etapa.restricoes_externas,
                        descritivo=True,
                    )
                ),
                "loops": loops_etapa,
                "pertence_loop": bool(loops_etapa),
                "fase": etapa.fase,
                "codigo_memorias": _codigo_memorias_dict(
                    etapa.codigo,
                    resultado.memorias,
                ),
            }
        )

    return etapas


def _montar_eventos_mapa(
    resultado: Resultado,
) -> list[dict[str, Any]]:
    eventos_mapa: list[dict[str, Any]] = []
    contexto = resultado.contexto_fisico

    for evento in resultado.eventos:
        origem = _dados_estado(evento.fisico, contexto)

        destino_fisico_tupla = (
            _aplicar_acoes_evento(evento.fisico, evento)
            if evento.tipo == "atuador"
            else tuple(evento.fisico)
        )
        destino = _dados_estado(destino_fisico_tupla, contexto)

        codigo_destino = _codigo_destino_evento(
            evento,
            resultado.memorias,
        )

        intermediarios = [
            _dados_estado(estado, contexto)
            for estado in evento.intermediarios
        ]

        condicoes_externas = dict(evento.condicoes_externas)
        restricoes_externas = dict(evento.restricoes_externas)

        loops_evento = [
            _loop_para_dict(loop)
            for loop in resultado.loops
            if (
                evento.etapa_indice is not None
                and loop.inicio <= evento.etapa_indice <= loop.fim
            )
        ]

        eventos_mapa.append(
            {
                "indice": evento.indice,
                "tipo": evento.tipo,
                "saidas": list(evento.saidas),
                "comandos": list(evento.saidas),
                "saidas_fisicas": list(evento.saidas_fisicas),

                # Campos históricos.
                "estado_fisico": origem["indices"],
                "destino_fisico": destino["indices"],
                "codigo_memorias": _codigo_memorias_dict(
                    evento.codigo,
                    resultado.memorias,
                ),
                "destino_memoria": _codigo_memorias_dict(
                    codigo_destino,
                    resultado.memorias,
                ),
                "estados_intermediarios": [
                    estado["indices"]
                    for estado in intermediarios
                ],

                # Campos novos usados pelo futuro mapa multiposição.
                "sensores_ativos": origem["sensores_ativos"],
                "destino_sensores_ativos": destino["sensores_ativos"],
                "estado_logico": origem["logico"],
                "destino_logico": destino["logico"],
                "estados_logicos_intermediarios": [
                    estado["logico"]
                    for estado in intermediarios
                ],
                "estado_texto": origem["texto"],
                "destino_texto": destino["texto"],
                "etapa_indice": evento.etapa_indice,

                # Dados necessários para desenhar decisões e retornos.
                "condicoes_externas": condicoes_externas,
                "restricoes_externas": restricoes_externas,
                "condicao_externa_texto": (
                    _formatar_condicoes_externas(
                        evento.condicoes_externas,
                        descritivo=True,
                    )
                ),
                "literal_condicao_externa": (
                    _formatar_condicoes_externas(
                        evento.condicoes_externas,
                    )
                ),
                "restricao_ramo_texto": (
                    _formatar_condicoes_externas(
                        evento.restricoes_externas,
                        descritivo=True,
                    )
                ),
                "loops": loops_evento,
                "pertence_loop": bool(loops_evento),
            }
        )

    return eventos_mapa


def _equacoes_para_exibicao(
    resultado: Resultado,
) -> dict[str, str]:
    """
    Exibe primeiro as equações das ocorrências lógicas e, em seguida, as
    equações físicas agregadas que ainda não estiverem presentes.
    """

    equacoes = dict(resultado.equacoes_comandos)

    for saida, equacao in resultado.equacoes.items():
        if saida not in equacoes:
            equacoes[saida] = equacao

    return equacoes


def resolver_site(
    sequencia: str | ProjetoSequencial,
    estados_iniciais: Mapping[str, int | bool | str] | None = None,
    *,
    ciclo_continuo: bool = False,
) -> dict[str, Any]:
    """
    Resolve a sequência e converte o Resultado do motor para a estrutura
    consumida pela aplicação Streamlit.
    """

    resultado = _resolver(
        sequencia,
        estado_inicial=estados_iniciais,
        ciclo_continuo=ciclo_continuo,
    )

    contexto = resultado.contexto_fisico
    etapas = _montar_etapas_saida(resultado)
    eventos_mapa = _montar_eventos_mapa(resultado)

    atuadores_multiposicao = [
        nome
        for nome, configuracao in contexto.configuracoes.items()
        if configuracao.quantidade_posicoes > 2
    ]

    estado_inicial_indices = {
        nome: contexto.configuracoes[nome].indice_sensor(sensor)
        for nome, sensor in resultado.estado_inicial.items()
    }

    return {
        "atuadores": list(resultado.atuadores),
        "variaveis_fisicas": list(resultado.variaveis_fisicas),
        "sensores_por_atuador": {
            nome: list(sensores)
            for nome, sensores in resultado.sensores_por_atuador.items()
        },
        "atuadores_multiposicao": atuadores_multiposicao,
        "possui_atuador_multiposicao": bool(
            atuadores_multiposicao
        ),
        "entradas_externas": list(resultado.entradas_externas),
        "loops": [
            _loop_para_dict(loop)
            for loop in resultado.loops
        ],
        "possui_loop": bool(resultado.loops),
        "possui_fluxo_condicional": bool(
            resultado.entradas_externas or resultado.loops
        ),

        # Compatibilidade com a interface atual.
        "estado_inicial": estado_inicial_indices,

        # Estado inicial explícito por sensor.
        "sensores_iniciais": dict(resultado.estado_inicial),
        "etapas": etapas,
        "memorias": list(resultado.memorias),
        "quantidade_memorias": len(resultado.memorias),

        # Equações apresentadas na tela.
        "equacoes": _equacoes_para_exibicao(resultado),

        # Separação explícita para as próximas telas.
        "equacoes_comandos": dict(resultado.equacoes_comandos),
        "equacoes_fisicas": dict(resultado.equacoes),
        "equacoes_memorias": dict(resultado.equacoes_memorias),
        "resolucao": _montar_resolucao_metodo(resultado),
        "resolucao_compacta": _montar_resolucao_detalhada(resultado),
        "eventos_mapa": eventos_mapa,
        "mapa_multiposicao_pendente": bool(atuadores_multiposicao),
        "mapa_loop_pendente": bool(resultado.loops),
        "mapa_requer_adaptacao": bool(
            atuadores_multiposicao or resultado.loops
        ),
        "validacoes": list(resultado.validacoes),
        "observacoes": list(resultado.observacoes),
        "versao_motor": VERSAO,
    }