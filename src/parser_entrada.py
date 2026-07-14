from __future__ import annotations

from dataclasses import dataclass
import re

from src.modelos import (
    AtuadorConfig,
    EtapaSequencial,
    LoopConfig,
    Movimento,
    ProjetoSequencial,
)


# -------------------------------------------------------------------
# Expressões regulares
# -------------------------------------------------------------------

_RE_MOVIMENTO = re.compile(
    r"""
    ^
    (?P<atuador>[A-Za-z][A-Za-z0-9_]*)
    \s*
    (?P<sentido>[+-])
    (?:
        \s*
        (?:
            (?:até|ate|para)
            \s*
            (?P<sensor>[A-Za-z][A-Za-z0-9_]*)

            |

            (?:->|→)
            \s*
            (?P<sensor_seta>[A-Za-z][A-Za-z0-9_]*)

            |

            \(
                \s*(?P<indice>\d+)\s*
            \)
        )
    )?
    $
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


_RE_LOOP = re.compile(
    r"""
    ^
    \[
        (?P<conteudo>.*)
    \]
    \s*
    (?:
        repetir\s+
    )?
    enquanto
    \s*
    (?P<sensor>[A-Za-z][A-Za-z0-9_]*)
    \s*=\s*
    (?P<valor>[01])
    $
    """,
    flags=re.IGNORECASE | re.VERBOSE | re.DOTALL,
)


_RE_SENSOR_NUMERICO = re.compile(
    r"^(?P<prefixo>[A-Za-z][A-Za-z0-9_]*?)[_]?(\d+)$"
)


# -------------------------------------------------------------------
# Estruturas internas do parser
# -------------------------------------------------------------------

@dataclass(frozen=True)
class _MovimentoBruto:
    atuador: str
    sentido: str
    sensor_destino: str | None = None


@dataclass(frozen=True)
class _EtapaBruta:
    movimentos: tuple[_MovimentoBruto, ...]


@dataclass(frozen=True)
class _LoopBruto:
    inicio: int
    fim: int
    sensor: str
    repetir_quando: int


# -------------------------------------------------------------------
# Normalização
# -------------------------------------------------------------------

def _normalizar_texto(texto: str) -> str:
    return (
        str(texto)
        .strip()
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
    )


def _sensor_por_indice(
    atuador: str,
    indice: int,
) -> str:
    return f"{atuador.lower()}{indice}"


def _indice_sensor(
    sensor: str,
    atuador: str,
) -> int:
    """
    Obtém o índice de sensores escritos como:

        a0
        a1
        b2
        B_3

    Na entrada textual, sensores multiposição precisam seguir esse
    padrão para que sua ordem física possa ser determinada.
    """

    sensor_limpo = sensor.strip()

    correspondencia = _RE_SENSOR_NUMERICO.fullmatch(
        sensor_limpo
    )

    if not correspondencia:
        raise ValueError(
            f"Não foi possível determinar a ordem do sensor "
            f"{sensor!r}. Na entrada textual, utilize nomes como "
            f"{atuador.lower()}0, {atuador.lower()}1, "
            f"{atuador.lower()}2 etc."
        )

    prefixo = correspondencia.group(
        "prefixo"
    ).rstrip("_")

    indice_encontrado = re.search(
        r"(\d+)$",
        sensor_limpo,
    )

    if indice_encontrado is None:
        raise ValueError(
            f"Não foi possível identificar o índice do sensor "
            f"{sensor!r}."
        )

    if prefixo.casefold() != atuador.casefold():
        raise ValueError(
            f"O sensor {sensor!r} não corresponde ao "
            f"atuador {atuador}."
        )

    return int(
        indice_encontrado.group(1)
    )


# -------------------------------------------------------------------
# Separação da sequência
# -------------------------------------------------------------------

def _separar_topo(texto: str) -> list[str]:
    """
    Separa a sequência por vírgula ou ponto e vírgula.

    Vírgulas internas de movimentos simultâneos e loops são
    preservadas.

    Exemplos:

        A+, B+, B-, A-

        A+, (B+, C+), C-

        A+, [C+, D+, C-, D-] enquanto e=0, A-
    """

    partes: list[str] = []
    atual: list[str] = []

    nivel_parenteses = 0
    nivel_colchetes = 0

    for caractere in texto:
        if caractere == "(":
            nivel_parenteses += 1
            atual.append(caractere)
            continue

        if caractere == ")":
            nivel_parenteses -= 1

            if nivel_parenteses < 0:
                raise ValueError(
                    "Foi encontrado um parêntese de fechamento "
                    "sem abertura."
                )

            atual.append(caractere)
            continue

        if caractere == "[":
            nivel_colchetes += 1

            if nivel_colchetes > 1:
                raise ValueError(
                    "Loops aninhados ainda não são permitidos."
                )

            atual.append(caractere)
            continue

        if caractere == "]":
            nivel_colchetes -= 1

            if nivel_colchetes < 0:
                raise ValueError(
                    "Foi encontrado um colchete de fechamento "
                    "sem abertura."
                )

            atual.append(caractere)
            continue

        if (
            caractere in {",", ";"}
            and nivel_parenteses == 0
            and nivel_colchetes == 0
        ):
            trecho = "".join(
                atual
            ).strip()

            if trecho:
                partes.append(
                    trecho
                )

            atual = []
            continue

        atual.append(
            caractere
        )

    if nivel_parenteses != 0:
        raise ValueError(
            "Os parênteses da sequência não estão balanceados."
        )

    if nivel_colchetes != 0:
        raise ValueError(
            "Os colchetes da sequência não estão balanceados."
        )

    trecho = "".join(
        atual
    ).strip()

    if trecho:
        partes.append(
            trecho
        )

    return partes


def _separar_movimentos_simultaneos(
    texto: str,
) -> list[str]:
    conteudo = texto.strip()

    if conteudo.startswith("(") or conteudo.endswith(")"):
        if not (
            conteudo.startswith("(")
            and conteudo.endswith(")")
        ):
            raise ValueError(
                f"Parênteses inválidos na etapa {texto!r}."
            )

        conteudo = conteudo[
            1:-1
        ].strip()

    partes = [
        parte.strip()
        for parte in re.split(
            r"[,;]",
            conteudo,
        )
        if parte.strip()
    ]

    if not partes:
        raise ValueError(
            "Foi encontrada uma etapa vazia."
        )

    return partes


# -------------------------------------------------------------------
# Interpretação dos movimentos
# -------------------------------------------------------------------

def _interpretar_movimento(
    texto: str,
) -> _MovimentoBruto:
    texto_normalizado = _normalizar_texto(
        texto
    )

    correspondencia = _RE_MOVIMENTO.fullmatch(
        texto_normalizado
    )

    if not correspondencia:
        raise ValueError(
            f"Movimento inválido: {texto_normalizado!r}. "
            "Use formatos como A+, B-, B+ até b2 ou B+(2)."
        )

    atuador = correspondencia.group(
        "atuador"
    ).upper()

    sentido = correspondencia.group(
        "sentido"
    )

    sensor = (
        correspondencia.group("sensor")
        or correspondencia.group("sensor_seta")
    )

    indice = correspondencia.group(
        "indice"
    )

    sensor_destino: str | None

    if sensor is not None:
        numero_sensor = _indice_sensor(
            sensor,
            atuador,
        )

        sensor_destino = _sensor_por_indice(
            atuador,
            numero_sensor,
        )

    elif indice is not None:
        sensor_destino = _sensor_por_indice(
            atuador,
            int(indice),
        )

    else:
        sensor_destino = None

    return _MovimentoBruto(
        atuador=atuador,
        sentido=sentido,
        sensor_destino=sensor_destino,
    )


def _interpretar_etapa(
    texto: str,
) -> _EtapaBruta:
    partes = _separar_movimentos_simultaneos(
        texto
    )

    movimentos = tuple(
        _interpretar_movimento(
            parte
        )
        for parte in partes
    )

    atuadores = [
        movimento.atuador
        for movimento in movimentos
    ]

    if len(set(atuadores)) != len(atuadores):
        raise ValueError(
            "Um mesmo atuador não pode aparecer duas vezes "
            "na mesma etapa."
        )

    return _EtapaBruta(
        movimentos=movimentos,
    )


# -------------------------------------------------------------------
# Interpretação dos loops
# -------------------------------------------------------------------

def _interpretar_fluxo(
    texto: str,
) -> tuple[
    list[_EtapaBruta],
    list[_LoopBruto],
    list[str],
]:
    trechos = _separar_topo(
        texto
    )

    if not trechos:
        raise ValueError(
            "A sequência não pode estar vazia."
        )

    etapas: list[_EtapaBruta] = []
    loops: list[_LoopBruto] = []
    entradas_externas: list[str] = []

    for trecho in trechos:
        trecho_limpo = trecho.strip()

        if trecho_limpo.startswith("["):
            correspondencia = _RE_LOOP.fullmatch(
                trecho_limpo
            )

            if not correspondencia:
                raise ValueError(
                    f"Loop inválido: {trecho!r}. "
                    "Use o formato "
                    "[C+, D+, C-, D-] enquanto e=0."
                )

            conteudo = correspondencia.group(
                "conteudo"
            ).strip()

            if "[" in conteudo or "]" in conteudo:
                raise ValueError(
                    "Loops aninhados ainda não são permitidos."
                )

            etapas_loop_texto = _separar_topo(
                conteudo
            )

            if not etapas_loop_texto:
                raise ValueError(
                    "O loop precisa possuir pelo menos uma etapa."
                )

            inicio = len(
                etapas
            )

            for etapa_texto in etapas_loop_texto:
                etapas.append(
                    _interpretar_etapa(
                        etapa_texto
                    )
                )

            fim = len(
                etapas
            ) - 1

            sensor = correspondencia.group(
                "sensor"
            ).lower()

            repetir_quando = int(
                correspondencia.group(
                    "valor"
                )
            )

            loops.append(
                _LoopBruto(
                    inicio=inicio,
                    fim=fim,
                    sensor=sensor,
                    repetir_quando=repetir_quando,
                )
            )

            if sensor not in entradas_externas:
                entradas_externas.append(
                    sensor
                )

            continue

        if "[" in trecho_limpo or "]" in trecho_limpo:
            raise ValueError(
                f"Colchetes inválidos no trecho {trecho!r}."
            )

        etapas.append(
            _interpretar_etapa(
                trecho_limpo
            )
        )

    return (
        etapas,
        loops,
        entradas_externas,
    )


# -------------------------------------------------------------------
# Identificação dos atuadores e sensores
# -------------------------------------------------------------------

def _movimentos_por_atuador(
    etapas: list[_EtapaBruta],
) -> dict[str, list[_MovimentoBruto]]:
    resultado: dict[
        str,
        list[_MovimentoBruto],
    ] = {}

    for etapa in etapas:
        for movimento in etapa.movimentos:
            resultado.setdefault(
                movimento.atuador,
                [],
            ).append(
                movimento
            )

    return resultado


def _inferir_atuadores(
    etapas: list[_EtapaBruta],
) -> dict[str, AtuadorConfig]:
    movimentos_agrupados = _movimentos_por_atuador(
        etapas
    )

    atuadores: dict[
        str,
        AtuadorConfig,
    ] = {}

    for nome, movimentos in movimentos_agrupados.items():
        primeiro_movimento = movimentos[0]

        indices_explicitos = {
            _indice_sensor(
                movimento.sensor_destino,
                nome,
            )
            for movimento in movimentos
            if movimento.sensor_destino is not None
        }

        # Nenhum destino específico informado:
        # considera atuador tradicional com dois sensores.
        if not indices_explicitos:
            indices = {
                0,
                1,
            }

        else:
            indices = set(
                indices_explicitos
            )

            primeiro_destino = None

            if primeiro_movimento.sensor_destino is not None:
                primeiro_destino = _indice_sensor(
                    primeiro_movimento.sensor_destino,
                    nome,
                )

            # Se o primeiro movimento for positivo, assume-se
            # que o atuador parte da posição mínima.
            if primeiro_movimento.sentido == "+":
                indices.add(
                    0
                )

                if primeiro_destino == 0:
                    raise ValueError(
                        f"O primeiro movimento de {nome} é positivo, "
                        f"mas seu destino foi informado como "
                        f"{_sensor_por_indice(nome, 0)}."
                    )

            # Se o primeiro movimento for negativo, precisa existir
            # pelo menos uma posição superior à posição de destino.
            else:
                if primeiro_destino is None:
                    indices.add(
                        max(
                            indices,
                            default=0,
                        )
                        + 1
                    )

                elif not any(
                    indice > primeiro_destino
                    for indice in indices
                ):
                    indices.add(
                        primeiro_destino + 1
                    )

        if len(indices) < 2:
            menor = min(
                indices,
                default=0,
            )

            indices.add(
                menor + 1
            )

        indices_ordenados = sorted(
            indices
        )

        sensores = tuple(
            _sensor_por_indice(
                nome,
                indice,
            )
            for indice in indices_ordenados
        )

        sensor_inicial = (
            sensores[0]
            if primeiro_movimento.sentido == "+"
            else sensores[-1]
        )

        atuadores[nome] = AtuadorConfig(
            nome=nome,
            sensores=sensores,
            sensor_inicial=sensor_inicial,
        )

    return atuadores


# -------------------------------------------------------------------
# Resolução dos destinos implícitos
# -------------------------------------------------------------------

def _resolver_destinos(
    etapas_brutas: list[_EtapaBruta],
    atuadores: dict[str, AtuadorConfig],
) -> list[EtapaSequencial]:
    estado_atual = {
        nome: configuracao.sensor_inicial
        for nome, configuracao in atuadores.items()
    }

    etapas: list[EtapaSequencial] = []

    for numero_etapa, etapa_bruta in enumerate(
        etapas_brutas,
        start=1,
    ):
        movimentos_resolvidos: list[
            Movimento
        ] = []

        novo_estado = dict(
            estado_atual
        )

        for movimento_bruto in etapa_bruta.movimentos:
            configuracao = atuadores[
                movimento_bruto.atuador
            ]

            sensor_atual = estado_atual[
                movimento_bruto.atuador
            ]

            indice_atual = configuracao.indice_sensor(
                sensor_atual
            )

            if movimento_bruto.sensor_destino is not None:
                sensor_destino = configuracao.sensor_canonico(
                    movimento_bruto.sensor_destino
                )

            elif configuracao.quantidade_posicoes == 2:
                sensor_destino = (
                    configuracao.sensor_maximo
                    if movimento_bruto.sentido == "+"
                    else configuracao.sensor_minimo
                )

            else:
                deslocamento = (
                    1
                    if movimento_bruto.sentido == "+"
                    else -1
                )

                indice_destino = (
                    indice_atual
                    + deslocamento
                )

                if not (
                    0
                    <= indice_destino
                    < configuracao.quantidade_posicoes
                ):
                    raise ValueError(
                        f"Etapa {numero_etapa}: o movimento "
                        f"{movimento_bruto.atuador}"
                        f"{movimento_bruto.sentido} não possui "
                        "um próximo sensor disponível. Informe "
                        "o destino explicitamente, por exemplo "
                        f"{movimento_bruto.atuador}"
                        f"{movimento_bruto.sentido} até "
                        f"{movimento_bruto.atuador.lower()}2."
                    )

                sensor_destino = configuracao.sensores[
                    indice_destino
                ]

            movimento = Movimento(
                atuador=movimento_bruto.atuador,
                sentido=movimento_bruto.sentido,
                sensor_destino=sensor_destino,
            )

            movimentos_resolvidos.append(
                movimento
            )

            novo_estado[
                movimento_bruto.atuador
            ] = sensor_destino

        etapas.append(
            EtapaSequencial(
                movimentos=tuple(
                    movimentos_resolvidos
                )
            )
        )

        estado_atual = novo_estado

    return etapas


# -------------------------------------------------------------------
# API pública
# -------------------------------------------------------------------

def interpretar_entrada(
    texto: str,
    *,
    sinal_partida: str = "S",
) -> ProjetoSequencial:
    """
    Converte uma sequência textual em ProjetoSequencial.

    Exemplos aceitos:

        A+, B+, B-, A-

        A+, B+ até b1, C+, B+ até b2, C-,
        B+ até b3, A-, B- até b0

        A+, B+, [C+, D+, C-, D-] enquanto e=0,
        A-, B-

        A+, (B+, C+), C-, B-, A-

        A+, B+(1), C+, B+(2), C-, B+(3), A-, B-(0)
    """

    texto_normalizado = _normalizar_texto(
        texto
    )

    if not texto_normalizado:
        raise ValueError(
            "A sequência não pode estar vazia."
        )

    (
        etapas_brutas,
        loops_brutos,
        entradas_externas,
    ) = _interpretar_fluxo(
        texto_normalizado
    )

    atuadores = _inferir_atuadores(
        etapas_brutas
    )

    etapas = _resolver_destinos(
        etapas_brutas,
        atuadores,
    )

    loops = [
        LoopConfig(
            inicio=loop.inicio,
            fim=loop.fim,
            sensor=loop.sensor,
            repetir_quando=loop.repetir_quando,
        )
        for loop in loops_brutos
    ]

    projeto = ProjetoSequencial(
        atuadores=atuadores,
        etapas=etapas,
        loops=loops,
        sinal_partida=sinal_partida,
        entradas_externas=entradas_externas,
    )

    projeto.validar()

    return projeto


def parsear_entrada(
    texto: str,
    *,
    sinal_partida: str = "S",
) -> ProjetoSequencial:
    """
    Nome alternativo para interpretar_entrada.
    """

    return interpretar_entrada(
        texto,
        sinal_partida=sinal_partida,
    )


def formatar_projeto(
    projeto: ProjetoSequencial,
) -> str:
    """
    Gera uma representação textual compacta do projeto interpretado.
    """

    projeto.validar()

    loops_por_inicio = {
        loop.inicio: loop
        for loop in projeto.loops
    }

    partes: list[str] = []
    indice = 0

    while indice < len(
        projeto.etapas
    ):
        loop = loops_por_inicio.get(
            indice
        )

        if loop is None:
            partes.append(
                projeto.etapas[
                    indice
                ].descricao
            )

            indice += 1
            continue

        conteudo = ", ".join(
            projeto.etapas[
                posicao
            ].descricao
            for posicao in range(
                loop.inicio,
                loop.fim + 1,
            )
        )

        partes.append(
            f"[{conteudo}] enquanto "
            f"{loop.sensor}="
            f"{loop.repetir_quando}"
        )

        indice = loop.fim + 1

    return ", ".join(
        partes
    )