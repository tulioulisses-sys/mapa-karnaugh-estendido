from __future__ import annotations

"""Gerador organizado do Mapa de Karnaugh Estendido em SVG.

A função pública permanece compatível com a interface do projeto::

    mapa = gerar_mapa_svg(resultado, incluir_titulo=True)
    mapa.svg
    mapa.largura
    mapa.altura

Esta versão combina a organização visual da implementação original com os
recursos acrescentados ao motor atual:

* atuadores tradicionais e multiposição;
* movimentos simultâneos;
* memórias internas;
* um ou mais loops condicionais;
* eixos em código Gray refletido de base mista;
* roteamento ortogonal com trilhos exclusivos;
* posicionamento de rótulos com detecção de colisões;
* retornos de loop em corredores externos dedicados, com conectores internos leves;
* mapa completo limitado por quantidade configurável de células.

O módulo utiliza apenas a biblioteca-padrão do Python.
"""

from dataclasses import dataclass
from heapq import heappop, heappush
from html import escape
from itertools import combinations, count
from math import ceil, prod, sqrt
from typing import Any, Iterable, Iterator, Literal, Mapping, Sequence


# ---------------------------------------------------------------------------
# Aparência
# ---------------------------------------------------------------------------

FUNDO = "#FFFFFF"
GRADE = "#4D5659"
GRADE_SUAVE = "#BCC4C7"
TEXTO = "#111517"
TEXTO_SUAVE = "#667175"
SETA_ATUADOR = "#111719"
SETA_MEMORIA = "#315F7A"
SETA_LOOP = "#146C94"
CONDICAO = "#146C94"
INICIAL = "#7A1730"
FINAL = "#267449"
CELULA_ALCANCADA = "#F1F8F9"
CELULA_INICIAL = "#DDEFF2"
CELULA_DECISAO = "#E5F3F5"

FONTE = "Arial, Helvetica, sans-serif"
LIMITE_PADRAO_CELULAS = 256


# ---------------------------------------------------------------------------
# Estruturas públicas e internas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MapaSVG:
    svg: str
    largura: int
    altura: int


@dataclass(frozen=True)
class Dimensao:
    nome: str
    rotulos: tuple[str, ...]
    tipo: Literal["atuador", "memoria"]
    ordem: int

    @property
    def quantidade(self) -> int:
        return len(self.rotulos)


@dataclass(frozen=True)
class EstadoMapa:
    valores: tuple[int, ...]


@dataclass(frozen=True)
class EventoMapa:
    indice: int
    tipo: Literal["atuador", "memoria"]
    comandos: tuple[str, ...]
    saidas_fisicas: tuple[str, ...]
    origem: EstadoMapa
    destino: EstadoMapa
    etapa_indice: int | None
    literal_condicao: str = ""
    condicoes_externas: tuple[tuple[str, int], ...] = ()

    @property
    def texto(self) -> str:
        if not self.comandos:
            return "?"
        return " ∥ ".join(self.comandos)

    @property
    def texto_condicionado(self) -> str:
        if not self.literal_condicao:
            return self.texto
        return f"{self.texto} · {self.literal_condicao}"

    @property
    def simultaneo(self) -> bool:
        return len(self.comandos) > 1


@dataclass(frozen=True)
class Eixo:
    dimensoes: tuple[Dimensao, ...]
    estados: tuple[tuple[int, ...], ...]
    indice: Mapping[tuple[int, ...], int]

    @property
    def quantidade(self) -> int:
        return len(self.estados)


@dataclass(frozen=True)
class Retangulo:
    x: float
    y: float
    largura: float
    altura: float

    @property
    def direita(self) -> float:
        return self.x + self.largura

    @property
    def inferior(self) -> float:
        return self.y + self.altura

    def expandido(self, margem: float) -> "Retangulo":
        return Retangulo(
            self.x - margem,
            self.y - margem,
            self.largura + 2 * margem,
            self.altura + 2 * margem,
        )

    def cruza(self, outro: "Retangulo") -> bool:
        return not (
            self.direita <= outro.x
            or outro.direita <= self.x
            or self.inferior <= outro.y
            or outro.inferior <= self.y
        )

    def contem(self, outro: "Retangulo", margem: float = 0.0) -> bool:
        return (
            outro.x >= self.x + margem
            and outro.y >= self.y + margem
            and outro.direita <= self.direita - margem
            and outro.inferior <= self.inferior - margem
        )


@dataclass
class Rota:
    evento: EventoMapa
    pontos: list[tuple[float, float]]
    rotulo: str = ""
    caixa_rotulo: Retangulo | None = None
    usa_numero: bool = False


@dataclass
class RotaLoop:
    numero: int
    pontos: list[tuple[float, float]]
    literal: str
    lado: Literal["topo", "direita", "fundo", "esquerda"]
    caixa_rotulo: Retangulo | None = None


Endpoint = tuple[int, Literal["origem", "destino"]]
No = tuple[int, int]
Aresta = tuple[No, No]


@dataclass
class Geometria:
    dimensoes: tuple[Dimensao, ...]
    posicao_dimensao: Mapping[str, int]
    eixo_horizontal: Eixo
    eixo_vertical: Eixo
    grade_x: float
    grade_y: float
    celula_largura: float
    celula_altura: float
    grade_largura: float
    grade_altura: float
    largura: int
    altura_base: int
    lanes: int
    frame_lanes: int
    indice_interno_x: int
    indice_interno_y: int
    x_tracks: list[float]
    y_tracks: list[float]
    margem: float
    corredor: float
    altura_titulo: float
    altura_cabecalho: float
    largura_cabecalho: float
    linhas_sequencia: list[str]
    margem_loop: float

    @property
    def colunas(self) -> int:
        return self.eixo_horizontal.quantidade

    @property
    def linhas(self) -> int:
        return self.eixo_vertical.quantidade

    @property
    def nx(self) -> int:
        return len(self.x_tracks)

    @property
    def ny(self) -> int:
        return len(self.y_tracks)

    @property
    def area_rotas(self) -> Retangulo:
        margem = 8.0
        return Retangulo(
            min(self.x_tracks) - margem,
            min(self.y_tracks) - margem,
            max(self.x_tracks) - min(self.x_tracks) + 2 * margem,
            max(self.y_tracks) - min(self.y_tracks) + 2 * margem,
        )

    @property
    def fim_cabecalho_x(self) -> float:
        return self.grade_x - self.corredor

    @property
    def fim_cabecalho_y(self) -> float:
        return self.grade_y - self.corredor

    def celula(self, estado: EstadoMapa) -> tuple[int, int]:
        valores_h = tuple(
            estado.valores[self.posicao_dimensao[dim.nome]]
            for dim in self.eixo_horizontal.dimensoes
        )
        valores_v = tuple(
            estado.valores[self.posicao_dimensao[dim.nome]]
            for dim in self.eixo_vertical.dimensoes
        )
        return (
            self.eixo_horizontal.indice[valores_h],
            self.eixo_vertical.indice[valores_v],
        )

    def coordenada_no(self, no: No) -> tuple[float, float]:
        return self.x_tracks[no[0]], self.y_tracks[no[1]]

    def no_da_porta(
        self,
        coluna: int,
        linha: int,
        slot: tuple[int, int],
    ) -> No:
        sx, sy = slot
        return (
            self.indice_interno_x + coluna * self.lanes + sx,
            self.indice_interno_y + linha * self.lanes + sy,
        )


# ---------------------------------------------------------------------------
# Utilidades de normalização
# ---------------------------------------------------------------------------


def _texto(valor: Any) -> str:
    return str(valor).strip()


def _nome(valor: Any) -> str:
    return _texto(valor).upper()


def _lista_textos(valor: Any) -> list[str]:
    if valor is None:
        return []
    if isinstance(valor, str):
        return [
            parte.strip()
            for parte in valor.replace("∥", ",").split(",")
            if parte.strip()
        ]
    return [str(item).strip() for item in valor if str(item).strip()]


def _normalizar_literal_condicao(valor: Any) -> str:
    texto = _texto(valor)
    if not texto or texto.casefold() in {"nenhuma", "none", "null", "—"}:
        return ""
    return texto.replace("¬", "'")


def _formatar_condicao(condicoes: Mapping[str, Any] | None) -> str:
    if not condicoes:
        return ""
    partes: list[str] = []
    for sensor, bruto in condicoes.items():
        valor = int(bool(bruto))
        partes.append(str(sensor) if valor else f"{sensor}'")
    return ".".join(partes)


def _largura_texto(texto: str, fonte: float) -> float:
    unidades = 0.0
    for caractere in texto:
        if caractere in " ilI1.,:;|'`":
            unidades += 0.34
        elif caractere in "MW@%&∥":
            unidades += 0.95
        else:
            unidades += 0.62
    return unidades * fonte


def _quebrar_texto(texto: str, largura_maxima: float, fonte: float) -> list[str]:
    palavras = texto.split()
    if not palavras:
        return []
    linhas: list[str] = []
    atual = palavras[0]
    for palavra in palavras[1:]:
        candidato = f"{atual} {palavra}"
        if _largura_texto(candidato, fonte) > largura_maxima:
            linhas.append(atual)
            atual = palavra
        else:
            atual = candidato
    linhas.append(atual)
    return linhas


# ---------------------------------------------------------------------------
# Dimensões e eventos
# ---------------------------------------------------------------------------


def _sensores_por_atuador(
    resultado: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    atuadores = [_nome(item) for item in resultado.get("atuadores", [])]
    bruto = resultado.get("sensores_por_atuador") or {}
    por_nome = {
        _nome(chave): tuple(str(valor) for valor in valores)
        for chave, valores in bruto.items()
    }

    saida: dict[str, tuple[str, ...]] = {}
    for atuador in atuadores:
        sensores = por_nome.get(atuador)
        if not sensores:
            sensores = (f"{atuador.lower()}0", f"{atuador.lower()}1")
        saida[atuador] = tuple(sensores)
    return saida


def _construir_dimensoes(resultado: Mapping[str, Any]) -> tuple[Dimensao, ...]:
    sensores = _sensores_por_atuador(resultado)
    dimensoes: list[Dimensao] = []

    for ordem, atuador in enumerate(resultado.get("atuadores", [])):
        nome = _nome(atuador)
        dimensoes.append(
            Dimensao(
                nome=nome,
                rotulos=sensores[nome],
                tipo="atuador",
                ordem=ordem,
            )
        )

    base_memoria = len(dimensoes)
    for indice, memoria in enumerate(resultado.get("memorias", [])):
        nome = _nome(memoria)
        dimensoes.append(
            Dimensao(
                nome=nome,
                rotulos=(f"{nome.lower()}0", nome.lower()),
                tipo="memoria",
                ordem=base_memoria + indice,
            )
        )

    if not dimensoes:
        raise ValueError("Nenhum atuador ou memória foi informado ao mapa.")

    return tuple(dimensoes)


def _indice_rotulo(dimensao: Dimensao, valor: Any) -> int:
    procurado = _texto(valor).casefold()
    for indice, rotulo in enumerate(dimensao.rotulos):
        if rotulo.casefold() == procurado:
            return indice

    try:
        indice = int(valor)
    except (TypeError, ValueError):
        indice = -1

    if 0 <= indice < dimensao.quantidade:
        return indice

    raise ValueError(
        f"O valor {valor!r} não pertence à dimensão {dimensao.nome}. "
        f"Valores esperados: {', '.join(dimensao.rotulos)}."
    )


def _estado_de_dados(
    dimensoes: Sequence[Dimensao],
    *,
    sensores_ativos: Mapping[str, Any] | None,
    estado_fisico: Mapping[str, Any] | None,
    codigo_memorias: Mapping[str, Any] | None,
) -> EstadoMapa:
    sensores = {_nome(k): v for k, v in (sensores_ativos or {}).items()}
    fisico = {_nome(k): v for k, v in (estado_fisico or {}).items()}
    memorias = {_nome(k): v for k, v in (codigo_memorias or {}).items()}

    valores: list[int] = []
    for dimensao in dimensoes:
        if dimensao.tipo == "atuador":
            if dimensao.nome in sensores:
                valores.append(_indice_rotulo(dimensao, sensores[dimensao.nome]))
            else:
                valores.append(_indice_rotulo(dimensao, fisico.get(dimensao.nome, 0)))
        else:
            valores.append(1 if bool(memorias.get(dimensao.nome, 0)) else 0)
    return EstadoMapa(tuple(valores))


def _eventos_do_resultado(
    resultado: Mapping[str, Any],
    dimensoes: Sequence[Dimensao],
) -> list[EventoMapa]:
    brutos = list(resultado.get("eventos_mapa") or [])

    if not brutos:
        for indice, etapa in enumerate(resultado.get("etapas", [])):
            brutos.append(
                {
                    "indice": indice,
                    "tipo": "atuador",
                    "comandos": etapa.get("comandos") or etapa.get("comando_texto"),
                    "saidas_fisicas": etapa.get("saidas_fisicas") or etapa.get("comandos"),
                    "estado_fisico": etapa.get("estado_antes", {}),
                    "destino_fisico": etapa.get("estado_depois", {}),
                    "sensores_ativos": etapa.get("sensores_ativos_antes"),
                    "destino_sensores_ativos": etapa.get("sensores_ativos_depois"),
                    "codigo_memorias": etapa.get("codigo_memorias", {}),
                    "destino_memoria": etapa.get("codigo_memorias", {}),
                    "etapa_indice": indice,
                    "condicoes_externas": etapa.get("condicoes_externas", {}),
                    "literal_condicao_externa": etapa.get("literal_condicao_externa", ""),
                }
            )

    eventos: list[EventoMapa] = []
    for indice_padrao, bruto in enumerate(brutos):
        tipo_texto = _texto(bruto.get("tipo", "atuador")).casefold()
        tipo: Literal["atuador", "memoria"] = (
            "memoria"
            if tipo_texto in {"memoria", "memória", "memory"}
            else "atuador"
        )

        comandos = tuple(
            _lista_textos(
                bruto.get("comandos")
                or bruto.get("saidas")
                or bruto.get("comando_texto")
            )
        )
        saidas_fisicas = tuple(
            _lista_textos(
                bruto.get("saidas_fisicas")
                or bruto.get("saidas")
                or comandos
            )
        )

        origem = _estado_de_dados(
            dimensoes,
            sensores_ativos=bruto.get("sensores_ativos"),
            estado_fisico=bruto.get("estado_fisico") or bruto.get("estado_antes"),
            codigo_memorias=bruto.get("codigo_memorias"),
        )
        destino = _estado_de_dados(
            dimensoes,
            sensores_ativos=bruto.get("destino_sensores_ativos"),
            estado_fisico=bruto.get("destino_fisico") or bruto.get("estado_depois"),
            codigo_memorias=bruto.get("destino_memoria")
            or bruto.get("codigo_memorias"),
        )

        condicoes = bruto.get("condicoes_externas") or {}
        literal = _normalizar_literal_condicao(
            bruto.get("literal_condicao_externa")
        )
        if not literal:
            literal = _formatar_condicao(condicoes)

        etapa_indice = bruto.get("etapa_indice")
        if etapa_indice is not None:
            etapa_indice = int(etapa_indice)

        eventos.append(
            EventoMapa(
                indice=indice_padrao,
                tipo=tipo,
                comandos=comandos,
                saidas_fisicas=saidas_fisicas,
                origem=origem,
                destino=destino,
                etapa_indice=etapa_indice,
                literal_condicao=literal,
                condicoes_externas=tuple(
                    (str(k), int(bool(v))) for k, v in condicoes.items()
                ),
            )
        )

    if not eventos:
        raise ValueError("O resultado não contém eventos ou etapas para desenhar o mapa.")
    return eventos


# ---------------------------------------------------------------------------
# Código Gray misto e escolha dos eixos
# ---------------------------------------------------------------------------


def _gray_misto(dimensoes: Sequence[Dimensao]) -> tuple[tuple[int, ...], ...]:
    if not dimensoes:
        return ((),)

    primeira = dimensoes[0]
    resto = _gray_misto(dimensoes[1:])
    saida: list[tuple[int, ...]] = []

    for valor in range(primeira.quantidade):
        bloco = resto if valor % 2 == 0 else tuple(reversed(resto))
        saida.extend((valor, *sufixo) for sufixo in bloco)
    return tuple(saida)


def _produto_dimensoes(dimensoes: Iterable[Dimensao]) -> int:
    quantidades = [dim.quantidade for dim in dimensoes]
    return prod(quantidades) if quantidades else 1


def _escolher_eixos(
    dimensoes: Sequence[Dimensao],
) -> tuple[tuple[Dimensao, ...], tuple[Dimensao, ...]]:
    if len(dimensoes) == 1:
        return (dimensoes[0],), ()

    indices = range(len(dimensoes))
    melhor: tuple[float, tuple[int, ...]] | None = None

    multiposicao = [
        indice
        for indice, dim in enumerate(dimensoes)
        if dim.tipo == "atuador" and dim.quantidade > 2
    ]
    maior_multi = (
        max(multiposicao, key=lambda i: dimensoes[i].quantidade)
        if multiposicao
        else None
    )

    for quantidade in range(1, len(dimensoes)):
        for horizontal_indices in combinations(indices, quantidade):
            hset = set(horizontal_indices)
            horizontal = [dimensoes[i] for i in horizontal_indices]
            vertical = [dimensoes[i] for i in indices if i not in hset]

            largura = _produto_dimensoes(horizontal)
            altura = _produto_dimensoes(vertical)
            proporcao = largura / max(altura, 1)

            custo = abs(proporcao - 1.35) * 5.4
            custo += abs(largura - altura) / max(largura, altura) * 1.8

            for indice, dim in enumerate(dimensoes):
                esta_horizontal = indice in hset
                if dim.tipo == "atuador":
                    preferencia_horizontal = dim.ordem % 2 == 0
                    if esta_horizontal != preferencia_horizontal:
                        custo += 1.15
                else:
                    custo += 0.10 if not esta_horizontal else 0.0

            if maior_multi is not None and maior_multi not in hset:
                custo += 9.0

            custo += max(0, proporcao - 4.2) * 3.5
            custo += max(0, 1 / max(proporcao, 1e-9) - 4.2) * 3.5

            chave = (custo, tuple(horizontal_indices))
            if melhor is None or chave < melhor:
                melhor = chave

    assert melhor is not None
    hset = set(melhor[1])
    horizontal = [dim for i, dim in enumerate(dimensoes) if i in hset]
    vertical = [dim for i, dim in enumerate(dimensoes) if i not in hset]

    def ordenar(eixo: list[Dimensao]) -> tuple[Dimensao, ...]:
        memorias = sorted(
            (dim for dim in eixo if dim.tipo == "memoria"),
            key=lambda dim: dim.ordem,
            reverse=True,
        )
        atuadores = sorted(
            (dim for dim in eixo if dim.tipo == "atuador"),
            key=lambda dim: dim.ordem,
            reverse=True,
        )
        return tuple([*memorias, *atuadores])

    return ordenar(horizontal), ordenar(vertical)


def _montar_eixo(dimensoes: Sequence[Dimensao]) -> Eixo:
    estados = _gray_misto(dimensoes)
    return Eixo(
        dimensoes=tuple(dimensoes),
        estados=estados,
        indice={estado: indice for indice, estado in enumerate(estados)},
    )


# ---------------------------------------------------------------------------
# Sequência e geometria
# ---------------------------------------------------------------------------


def _descricao_movimento(etapa: Mapping[str, Any]) -> str:
    movimentos = etapa.get("movimentos") or []
    if movimentos:
        textos: list[str] = []
        for movimento in movimentos:
            saida = _texto(movimento.get("saida") or movimento.get("comando"))
            destino = _texto(movimento.get("sensor_destino"))
            if destino and (
                movimento.get("requer_parada")
                or "(" in _texto(movimento.get("comando"))
            ):
                textos.append(f"{saida} até {destino}")
            else:
                textos.append(saida)
        return textos[0] if len(textos) == 1 else "(" + ", ".join(textos) + ")"

    return _texto(
        etapa.get("comando_texto")
        or " ∥ ".join(_lista_textos(etapa.get("comandos")))
    )


def _sequencia_formatada(resultado: Mapping[str, Any]) -> str:
    etapas = list(resultado.get("etapas") or [])
    if not etapas:
        eventos = list(resultado.get("eventos_mapa") or [])
        return ", ".join(
            " ∥ ".join(
                _lista_textos(evento.get("comandos") or evento.get("saidas"))
            )
            for evento in eventos
            if _texto(evento.get("tipo", "atuador")).casefold() != "memoria"
        )

    loops = sorted(
        resultado.get("loops") or [],
        key=lambda item: int(item.get("inicio", 0)),
    )
    loops_por_inicio = {int(loop.get("inicio", 0)): loop for loop in loops}

    partes: list[str] = []
    indice = 0
    while indice < len(etapas):
        loop = loops_por_inicio.get(indice)
        if loop is None:
            partes.append(_descricao_movimento(etapas[indice]))
            indice += 1
            continue

        fim = int(loop.get("fim", indice))
        conteudo = ", ".join(
            _descricao_movimento(etapas[posicao])
            for posicao in range(indice, fim + 1)
        )
        sensor = _texto(loop.get("sensor", "e"))
        repetir = int(loop.get("repetir_quando", 0))
        partes.append(f"[{conteudo}] enquanto {sensor}={repetir}")
        indice = fim + 1

    return ", ".join(partes)


def _runs(valores: Sequence[int]) -> list[tuple[int, int, int]]:
    if not valores:
        return []
    saida: list[tuple[int, int, int]] = []
    inicio = 0
    atual = valores[0]
    for indice, valor in enumerate(valores[1:], start=1):
        if valor != atual:
            saida.append((inicio, indice - 1, atual))
            inicio = indice
            atual = valor
    saida.append((inicio, len(valores) - 1, atual))
    return saida


def _maximo_grupos_por_estado(eventos: Sequence[EventoMapa]) -> int:
    _, membros = _grupos_endpoints(eventos)
    contagem: dict[EstadoMapa, int] = {}
    por_indice = {evento.indice: evento for evento in eventos}
    for endpoints in membros.values():
        indice, lado = endpoints[0]
        evento = por_indice[indice]
        estado = evento.origem if lado == "origem" else evento.destino
        contagem[estado] = contagem.get(estado, 0) + 1
    return max(contagem.values(), default=1)


def _construir_geometria(
    resultado: Mapping[str, Any],
    dimensoes: Sequence[Dimensao],
    eventos: Sequence[EventoMapa],
    *,
    incluir_titulo: bool,
    lanes: int,
) -> Geometria:
    horizontal_dims, vertical_dims = _escolher_eixos(dimensoes)
    eixo_h = _montar_eixo(horizontal_dims)
    eixo_v = _montar_eixo(vertical_dims)

    maior_rotulo = max(
        (_largura_texto(evento.texto_condicionado, 13.0) for evento in eventos),
        default=34.0,
    )
    maior_variavel = max(
        (
            _largura_texto(rotulo, 13.0)
            for dim in dimensoes
            for rotulo in dim.rotulos
        ),
        default=28.0,
    )

    passo_x = 13.0
    passo_y = 11.0
    celula_largura = max(
        76.0,
        24.0 + lanes * passo_x,
        min(maior_rotulo + 18.0, 118.0),
    )
    celula_altura = max(54.0, 20.0 + lanes * passo_y)

    margem = 28.0
    nivel_vertical = max(38.0, maior_variavel + 14.0)
    altura_cabecalho = max(56.0, len(horizontal_dims) * 31.0 + 18.0)
    largura_cabecalho = max(58.0, len(vertical_dims) * nivel_vertical + 12.0)

    loops = list(resultado.get("loops") or [])
    wraps_h = 0
    wraps_v = 0
    posicao = {dim.nome: indice for indice, dim in enumerate(dimensoes)}

    def celula_provisoria(estado: EstadoMapa) -> tuple[int, int]:
        h = tuple(estado.valores[posicao[dim.nome]] for dim in horizontal_dims)
        v = tuple(estado.valores[posicao[dim.nome]] for dim in vertical_dims)
        return eixo_h.indice[h], eixo_v.indice[v]

    for evento in eventos:
        c1, l1 = celula_provisoria(evento.origem)
        c2, l2 = celula_provisoria(evento.destino)
        if eixo_h.quantidade > 2 and l1 == l2 and abs(c1 - c2) == eixo_h.quantidade - 1:
            wraps_h += 1
        if eixo_v.quantidade > 2 and c1 == c2 and abs(l1 - l2) == eixo_v.quantidade - 1:
            wraps_v += 1

    necessidade_wrap = max(wraps_h, wraps_v)
    frame_lanes = max(3, min(8, ceil(necessidade_wrap / 2) + 2))
    corredor = frame_lanes * 16.0 + 10.0

    sequencia = _sequencia_formatada(resultado)
    largura_grade_base = eixo_h.quantidade * celula_largura
    largura_prevista = max(760.0, margem + largura_cabecalho + 2 * corredor + largura_grade_base)
    linhas_sequencia = _quebrar_texto(
        f"Sequência: {sequencia}",
        largura_prevista - 90.0,
        15.0,
    )
    altura_titulo = (
        56.0 + max(1, len(linhas_sequencia)) * 20.0
        if incluir_titulo
        else 18.0
    )

    margem_loop = 96.0 + max(0, len(loops) - 1) * 24.0 if loops else 28.0
    grade_x = margem + largura_cabecalho + corredor
    grade_y = altura_titulo + altura_cabecalho + corredor
    grade_largura = eixo_h.quantidade * celula_largura
    grade_altura = eixo_v.quantidade * celula_altura

    largura = int(
        ceil(grade_x + grade_largura + corredor + margem_loop + margem)
    )
    altura_base = int(ceil(grade_y + grade_altura + corredor + margem))

    def tracks_externos(inicio: float, fim: float, quantidade: int) -> list[float]:
        if quantidade <= 0:
            return []
        passo = (fim - inicio) / (quantidade + 1)
        return [inicio + (indice + 1) * passo for indice in range(quantidade)]

    esquerda = tracks_externos(grade_x - corredor, grade_x, frame_lanes)
    direita = tracks_externos(
        grade_x + grade_largura,
        grade_x + grade_largura + corredor,
        frame_lanes,
    )
    topo = tracks_externos(grade_y - corredor, grade_y, frame_lanes)
    fundo = tracks_externos(
        grade_y + grade_altura,
        grade_y + grade_altura + corredor,
        frame_lanes,
    )

    internos_x: list[float] = []
    for coluna in range(eixo_h.quantidade):
        x0 = grade_x + coluna * celula_largura
        for lane in range(lanes):
            internos_x.append(
                x0 + (lane + 1) * celula_largura / (lanes + 1)
            )

    internos_y: list[float] = []
    for linha in range(eixo_v.quantidade):
        y0 = grade_y + linha * celula_altura
        for lane in range(lanes):
            internos_y.append(
                y0 + (lane + 1) * celula_altura / (lanes + 1)
            )

    return Geometria(
        dimensoes=tuple(dimensoes),
        posicao_dimensao=posicao,
        eixo_horizontal=eixo_h,
        eixo_vertical=eixo_v,
        grade_x=grade_x,
        grade_y=grade_y,
        celula_largura=celula_largura,
        celula_altura=celula_altura,
        grade_largura=grade_largura,
        grade_altura=grade_altura,
        largura=largura,
        altura_base=altura_base,
        lanes=lanes,
        frame_lanes=frame_lanes,
        indice_interno_x=len(esquerda),
        indice_interno_y=len(topo),
        x_tracks=esquerda + internos_x + direita,
        y_tracks=topo + internos_y + fundo,
        margem=margem,
        corredor=corredor,
        altura_titulo=altura_titulo,
        altura_cabecalho=altura_cabecalho,
        largura_cabecalho=largura_cabecalho,
        linhas_sequencia=linhas_sequencia,
        margem_loop=margem_loop,
    )


# ---------------------------------------------------------------------------
# Agrupamento de visitas e portas
# ---------------------------------------------------------------------------


class _UniaoBusca:
    def __init__(self, itens: Iterable[Endpoint]) -> None:
        self.pai = {item: item for item in itens}

    def encontrar(self, item: Endpoint) -> Endpoint:
        pai = self.pai[item]
        if pai != item:
            self.pai[item] = self.encontrar(pai)
        return self.pai[item]

    def unir(self, a: Endpoint, b: Endpoint) -> None:
        ra = self.encontrar(a)
        rb = self.encontrar(b)
        if ra != rb:
            self.pai[max(ra, rb)] = min(ra, rb)


def _estado_endpoint(evento: EventoMapa, lado: str) -> EstadoMapa:
    return evento.origem if lado == "origem" else evento.destino


def _grupos_endpoints(
    eventos: Sequence[EventoMapa],
) -> tuple[dict[Endpoint, Endpoint], dict[Endpoint, list[Endpoint]]]:
    endpoints: list[Endpoint] = [
        (evento.indice, lado)
        for evento in eventos
        for lado in ("origem", "destino")
    ]
    uniao = _UniaoBusca(endpoints)

    for atual, proximo in zip(eventos, eventos[1:]):
        if atual.destino == proximo.origem:
            uniao.unir(
                (atual.indice, "destino"),
                (proximo.indice, "origem"),
            )

    if eventos and eventos[-1].destino == eventos[0].origem:
        uniao.unir(
            (eventos[-1].indice, "destino"),
            (eventos[0].indice, "origem"),
        )

    raiz_por_endpoint = {
        endpoint: uniao.encontrar(endpoint) for endpoint in endpoints
    }
    membros: dict[Endpoint, list[Endpoint]] = {}
    for endpoint, raiz in raiz_por_endpoint.items():
        membros.setdefault(raiz, []).append(endpoint)
    return raiz_por_endpoint, membros


def _slots_portas(lanes: int) -> list[tuple[int, int]]:
    centro = (lanes - 1) / 2
    slots = [(x, y) for y in range(lanes) for x in range(lanes)]
    slots.sort(
        key=lambda item: (
            abs(item[0] - centro) + abs(item[1] - centro),
            abs(item[1] - centro),
            abs(item[0] - centro),
            item[1],
            item[0],
        )
    )
    return slots


def _delta_ciclico_assinado(origem: int, destino: int, tamanho: int) -> float:
    if tamanho <= 1 or origem == destino:
        return 0.0
    direto = destino - origem
    alternativo = direto - tamanho if direto > 0 else direto + tamanho
    escolhido = direto if abs(direto) <= abs(alternativo) else alternativo
    return 1.0 if escolhido > 0 else -1.0


def _atribuir_portas(
    geometria: Geometria,
    eventos: Sequence[EventoMapa],
) -> dict[Endpoint, No]:
    raiz_por_endpoint, membros = _grupos_endpoints(eventos)
    por_indice = {evento.indice: evento for evento in eventos}

    celula_raiz: dict[Endpoint, tuple[int, int]] = {}
    for raiz, endpoints in membros.items():
        indice, lado = endpoints[0]
        evento = por_indice[indice]
        celula_raiz[raiz] = geometria.celula(_estado_endpoint(evento, lado))

    vizinhos: dict[Endpoint, list[tuple[int, int]]] = {
        raiz: [] for raiz in membros
    }
    for evento in eventos:
        raiz_o = raiz_por_endpoint[(evento.indice, "origem")]
        raiz_d = raiz_por_endpoint[(evento.indice, "destino")]
        vizinhos[raiz_o].append(celula_raiz[raiz_d])
        vizinhos[raiz_d].append(celula_raiz[raiz_o])

    por_celula: dict[tuple[int, int], list[Endpoint]] = {}
    for raiz, celula in celula_raiz.items():
        por_celula.setdefault(celula, []).append(raiz)

    atribuicao_raiz: dict[Endpoint, No] = {}
    centro = (geometria.lanes - 1) / 2

    for celula, raizes in por_celula.items():
        if len(raizes) > geometria.lanes**2:
            raise RuntimeError("A célula exige mais portas do que a geometria oferece.")

        disponiveis = set(_slots_portas(geometria.lanes))
        raizes.sort(
            key=lambda raiz: (
                -len(vizinhos[raiz]),
                min(membro[0] for membro in membros[raiz]),
            )
        )

        for raiz in raizes:
            alvos = vizinhos[raiz]
            vx = sum(
                _delta_ciclico_assinado(
                    celula[0], alvo[0], geometria.colunas
                )
                for alvo in alvos
            )
            vy = sum(
                _delta_ciclico_assinado(
                    celula[1], alvo[1], geometria.linhas
                )
                for alvo in alvos
            )
            if alvos:
                vx /= len(alvos)
                vy /= len(alvos)

            desejado_x = centro + vx * centro * 0.72
            desejado_y = centro + vy * centro * 0.72

            def pontuacao(slot: tuple[int, int]) -> tuple[float, float, int, int]:
                distancia = (
                    (slot[0] - desejado_x) ** 2
                    + (slot[1] - desejado_y) ** 2
                )
                centroide = abs(slot[0] - centro) + abs(slot[1] - centro)
                return distancia, centroide * 0.12, slot[1], slot[0]

            escolhido = min(disponiveis, key=pontuacao)
            disponiveis.remove(escolhido)
            atribuicao_raiz[raiz] = geometria.no_da_porta(
                celula[0], celula[1], escolhido
            )

    return {
        endpoint: atribuicao_raiz[raiz]
        for endpoint, raiz in raiz_por_endpoint.items()
    }


# ---------------------------------------------------------------------------
# Roteamento ortogonal
# ---------------------------------------------------------------------------


def _vizinhos(no: No, nx: int, ny: int) -> Iterator[tuple[No, str]]:
    x, y = no
    if x > 0:
        yield (x - 1, y), "H"
    if x + 1 < nx:
        yield (x + 1, y), "H"
    if y > 0:
        yield (x, y - 1), "V"
    if y + 1 < ny:
        yield (x, y + 1), "V"


def _aresta(a: No, b: No) -> Aresta:
    return (a, b) if a <= b else (b, a)


def _a_estrela(
    geometria: Geometria,
    inicio: No,
    fim: No,
    nos_ocupados: set[No],
    arestas_ocupadas: set[Aresta],
    *,
    permitir_cruzamentos: bool,
) -> list[No] | None:
    if inicio == fim:
        return [inicio]

    fila: list[tuple[float, int, float, No, str | None]] = []
    sequencia_fila = count()
    heappush(fila, (0.0, next(sequencia_fila), 0.0, inicio, None))

    melhor: dict[tuple[No, str | None], float] = {(inicio, None): 0.0}
    anterior: dict[
        tuple[No, str | None], tuple[No, str | None] | None
    ] = {(inicio, None): None}
    estado_final: tuple[No, str | None] | None = None

    min_x, max_x = sorted((inicio[0], fim[0]))
    min_y, max_y = sorted((inicio[1], fim[1]))

    while fila:
        _, _, custo_atual, no, direcao_anterior = heappop(fila)
        estado = (no, direcao_anterior)
        if custo_atual > melhor.get(estado, float("inf")) + 1e-9:
            continue
        if no == fim:
            estado_final = estado
            break

        for vizinho, direcao in _vizinhos(no, geometria.nx, geometria.ny):
            edge = _aresta(no, vizinho)
            if edge in arestas_ocupadas:
                continue

            if vizinho in nos_ocupados and vizinho not in {inicio, fim}:
                if not permitir_cruzamentos:
                    continue
                penalidade_no = 95.0
            else:
                penalidade_no = 0.0

            x1, y1 = geometria.coordenada_no(no)
            x2, y2 = geometria.coordenada_no(vizinho)
            comprimento = abs(x2 - x1) + abs(y2 - y1)
            curva = 0.0 if direcao_anterior in (None, direcao) else 16.0

            desvio = 0.0
            if not (min_x <= vizinho[0] <= max_x):
                desvio += 1.8
            if not (min_y <= vizinho[1] <= max_y):
                desvio += 1.8

            novo_custo = (
                custo_atual
                + comprimento
                + curva
                + penalidade_no
                + desvio
            )
            heuristica = (
                abs(
                    geometria.x_tracks[vizinho[0]]
                    - geometria.x_tracks[fim[0]]
                )
                + abs(
                    geometria.y_tracks[vizinho[1]]
                    - geometria.y_tracks[fim[1]]
                )
            )
            novo_estado = (vizinho, direcao)
            if novo_custo + 1e-9 < melhor.get(novo_estado, float("inf")):
                melhor[novo_estado] = novo_custo
                anterior[novo_estado] = estado
                heappush(
                    fila,
                    (
                        novo_custo + heuristica,
                        next(sequencia_fila),
                        novo_custo,
                        vizinho,
                        direcao,
                    ),
                )

    if estado_final is None:
        return None

    caminho: list[No] = []
    atual: tuple[No, str | None] | None = estado_final
    while atual is not None:
        caminho.append(atual[0])
        atual = anterior[atual]
    caminho.reverse()
    return caminho


def _juntar_caminhos(partes: Sequence[Sequence[No]]) -> list[No]:
    saida: list[No] = []
    for parte in partes:
        if not parte:
            continue
        if saida and saida[-1] == parte[0]:
            saida.extend(parte[1:])
        else:
            saida.extend(parte)
    return saida


def _caminho_por_waypoints(
    geometria: Geometria,
    pontos: Sequence[No],
    nos_ocupados: set[No],
    arestas_ocupadas: set[Aresta],
    *,
    permitir_cruzamentos: bool,
) -> list[No] | None:
    nos_temp = set(nos_ocupados)
    arestas_temp = set(arestas_ocupadas)
    partes: list[list[No]] = []

    for inicio, fim in zip(pontos, pontos[1:]):
        parte = _a_estrela(
            geometria,
            inicio,
            fim,
            nos_temp,
            arestas_temp,
            permitir_cruzamentos=permitir_cruzamentos,
        )
        if parte is None:
            return None
        partes.append(parte)
        for no in parte[1:-1]:
            nos_temp.add(no)
        for a, b in zip(parte, parte[1:]):
            arestas_temp.add(_aresta(a, b))

    return _juntar_caminhos(partes)


def _candidatos_wrap(
    geometria: Geometria,
    evento: EventoMapa,
    inicio: No,
    fim: No,
) -> list[list[No]]:
    origem = geometria.celula(evento.origem)
    destino = geometria.celula(evento.destino)
    candidatos: list[list[No]] = []

    wrap_h = (
        geometria.colunas > 2
        and origem[1] == destino[1]
        and abs(origem[0] - destino[0]) == geometria.colunas - 1
    )
    wrap_v = (
        geometria.linhas > 2
        and origem[0] == destino[0]
        and abs(origem[1] - destino[1]) == geometria.linhas - 1
    )

    if wrap_h:
        indices_y = list(range(geometria.frame_lanes)) + list(
            range(
                geometria.ny - 1,
                geometria.ny - geometria.frame_lanes - 1,
                -1,
            )
        )
        indices_y.sort(
            key=lambda iy: abs(
                geometria.y_tracks[iy] - geometria.y_tracks[inicio[1]]
            )
        )
        for iy in indices_y:
            candidatos.append([inicio, (inicio[0], iy), (fim[0], iy), fim])

    if wrap_v:
        indices_x = list(range(geometria.frame_lanes)) + list(
            range(
                geometria.nx - 1,
                geometria.nx - geometria.frame_lanes - 1,
                -1,
            )
        )
        indices_x.sort(
            key=lambda ix: abs(
                geometria.x_tracks[ix] - geometria.x_tracks[inicio[0]]
            )
        )
        for ix in indices_x:
            candidatos.append([inicio, (ix, inicio[1]), (ix, fim[1]), fim])

    return candidatos


def _rotear_laco(
    geometria: Geometria,
    inicio: No,
    nos_ocupados: set[No],
    arestas_ocupadas: set[Aresta],
) -> list[No] | None:
    for alcance in (1, 2, 3):
        for dx, dy in (
            (alcance, alcance),
            (-alcance, alcance),
            (alcance, -alcance),
            (-alcance, -alcance),
        ):
            p1 = (inicio[0] + dx, inicio[1])
            p2 = (inicio[0] + dx, inicio[1] + dy)
            p3 = (inicio[0], inicio[1] + dy)
            caminho = [inicio, p1, p2, p3, inicio]
            if any(
                not (0 <= x < geometria.nx and 0 <= y < geometria.ny)
                for x, y in caminho
            ):
                continue
            internos = set(caminho[1:-1])
            if internos & nos_ocupados:
                continue
            edges = {
                _aresta(a, b) for a, b in zip(caminho, caminho[1:])
            }
            if edges & arestas_ocupadas:
                continue
            return caminho
    return None


def _simplificar_pontos(
    pontos: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    if len(pontos) <= 2:
        return pontos
    saida = [pontos[0]]
    for indice in range(1, len(pontos) - 1):
        anterior = saida[-1]
        atual = pontos[indice]
        proximo = pontos[indice + 1]
        vertical = (
            abs(anterior[0] - atual[0]) < 1e-9
            and abs(atual[0] - proximo[0]) < 1e-9
        )
        horizontal = (
            abs(anterior[1] - atual[1]) < 1e-9
            and abs(atual[1] - proximo[1]) < 1e-9
        )
        if not (vertical or horizontal):
            saida.append(atual)
    saida.append(pontos[-1])
    return saida


def _rotear_em_ordem(
    geometria: Geometria,
    eventos: Sequence[EventoMapa],
    portas: Mapping[Endpoint, No],
    ordem: Sequence[EventoMapa],
    *,
    permitir_cruzamentos: bool,
) -> list[Rota] | None:
    nos_ocupados: set[No] = set(portas.values())
    arestas_ocupadas: set[Aresta] = set()
    rotas: dict[int, Rota] = {}

    for evento in ordem:
        inicio = portas[(evento.indice, "origem")]
        fim = portas[(evento.indice, "destino")]

        if inicio == fim:
            caminho = _rotear_laco(
                geometria,
                inicio,
                nos_ocupados,
                arestas_ocupadas,
            )
        else:
            caminho = None
            for waypoints in _candidatos_wrap(
                geometria, evento, inicio, fim
            ):
                caminho = _caminho_por_waypoints(
                    geometria,
                    waypoints,
                    nos_ocupados,
                    arestas_ocupadas,
                    permitir_cruzamentos=permitir_cruzamentos,
                )
                if caminho is not None:
                    break
            if caminho is None:
                caminho = _a_estrela(
                    geometria,
                    inicio,
                    fim,
                    nos_ocupados,
                    arestas_ocupadas,
                    permitir_cruzamentos=permitir_cruzamentos,
                )

        if caminho is None:
            return None

        for no in caminho[1:-1]:
            nos_ocupados.add(no)
        for a, b in zip(caminho, caminho[1:]):
            arestas_ocupadas.add(_aresta(a, b))

        pontos = [geometria.coordenada_no(no) for no in caminho]
        rotas[evento.indice] = Rota(
            evento=evento,
            pontos=_simplificar_pontos(pontos),
        )

    return [rotas[evento.indice] for evento in eventos]


def _rotear_eventos(
    geometria: Geometria,
    eventos: Sequence[EventoMapa],
    portas: Mapping[Endpoint, No],
    *,
    permitir_cruzamentos: bool,
) -> list[Rota] | None:
    def dificuldade(evento: EventoMapa) -> tuple[int, int, int, int]:
        inicio = portas[(evento.indice, "origem")]
        fim = portas[(evento.indice, "destino")]
        distancia = abs(inicio[0] - fim[0]) + abs(inicio[1] - fim[1])
        wrap = int(bool(_candidatos_wrap(geometria, evento, inicio, fim)))
        tipo = 3 if evento.tipo == "memoria" else 2 if evento.simultaneo else 1
        return wrap, distancia, tipo, -evento.indice

    estrategias = [
        sorted(eventos, key=dificuldade, reverse=True),
        list(eventos),
        list(reversed(eventos)),
    ]
    for ordem in estrategias:
        rotas = _rotear_em_ordem(
            geometria,
            eventos,
            portas,
            ordem,
            permitir_cruzamentos=permitir_cruzamentos,
        )
        if rotas is not None:
            return rotas
    return None


# ---------------------------------------------------------------------------
# Rótulos e colisões
# ---------------------------------------------------------------------------


def _segmentos(
    pontos: Sequence[tuple[float, float]],
) -> list[tuple[float, float, float, float]]:
    return [(*a, *b) for a, b in zip(pontos, pontos[1:])]


def _comprimento_segmento(
    segmento: tuple[float, float, float, float],
) -> float:
    x1, y1, x2, y2 = segmento
    return abs(x2 - x1) + abs(y2 - y1)


def _caixa_texto(
    texto: str,
    centro_x: float,
    centro_y: float,
    fonte: float = 12.5,
    padding_x: float = 7.0,
    padding_y: float = 4.0,
) -> Retangulo:
    largura = max(22.0, _largura_texto(texto, fonte) + 2 * padding_x)
    altura = fonte + 2 * padding_y
    return Retangulo(
        centro_x - largura / 2,
        centro_y - altura / 2,
        largura,
        altura,
    )


def _retangulo_cruza_segmento(
    caixa: Retangulo,
    segmento: tuple[float, float, float, float],
    margem: float = 2.0,
) -> bool:
    caixa = caixa.expandido(margem)
    x1, y1, x2, y2 = segmento
    if abs(y1 - y2) < 1e-9:
        minimo, maximo = sorted((x1, x2))
        return caixa.y <= y1 <= caixa.inferior and not (
            maximo <= caixa.x or minimo >= caixa.direita
        )
    minimo, maximo = sorted((y1, y2))
    return caixa.x <= x1 <= caixa.direita and not (
        maximo <= caixa.y or minimo >= caixa.inferior
    )


def _candidatos_rotulo(
    rota: Rota,
    texto: str,
    fonte: float = 12.5,
) -> list[Retangulo]:
    candidatos: list[tuple[float, Retangulo]] = []
    modelo = _caixa_texto(texto, 0, 0, fonte)
    largura = modelo.largura
    altura = modelo.altura

    segmentos = sorted(
        _segmentos(rota.pontos),
        key=_comprimento_segmento,
        reverse=True,
    )
    for ordem_segmento, segmento in enumerate(segmentos):
        x1, y1, x2, y2 = segmento
        comprimento = _comprimento_segmento(segmento)
        if comprimento < 16:
            continue

        for fracao in (0.50, 0.33, 0.67, 0.20, 0.80):
            x = x1 + (x2 - x1) * fracao
            y = y1 + (y2 - y1) * fracao

            requisito = largura + 16 if abs(y1 - y2) < 1e-9 else altura + 16
            if comprimento >= requisito:
                caixa = _caixa_texto(texto, x, y, fonte)
                candidatos.append(
                    (ordem_segmento * 10 + abs(fracao - 0.5), caixa)
                )

            if abs(y1 - y2) < 1e-9:
                deslocamento = altura / 2 + 7
                for sinal in (-1, 1):
                    caixa = _caixa_texto(
                        texto, x, y + sinal * deslocamento, fonte
                    )
                    candidatos.append(
                        (
                            4 + ordem_segmento * 10 + abs(fracao - 0.5),
                            caixa,
                        )
                    )
            else:
                deslocamento = largura / 2 + 9
                for sinal in (1, -1):
                    caixa = _caixa_texto(
                        texto, x + sinal * deslocamento, y, fonte
                    )
                    candidatos.append(
                        (
                            4 + ordem_segmento * 10 + abs(fracao - 0.5),
                            caixa,
                        )
                    )

    candidatos.sort(key=lambda item: item[0])
    return [caixa for _, caixa in candidatos]


def _texto_evento_para_mapa(
    evento: EventoMapa,
    loops: Sequence[Mapping[str, Any]],
) -> str:
    inicios = {
        int(loop.get("inicio", -1)): _texto(loop.get("literal_repeticao"))
        for loop in loops
    }
    literal_repeticao = inicios.get(evento.etapa_indice or -999)
    if (
        literal_repeticao
        and evento.literal_condicao
        and evento.literal_condicao == literal_repeticao
    ):
        return evento.texto
    return evento.texto_condicionado


def _posicionar_rotulos(
    rotas: list[Rota],
    geometria: Geometria,
    portas: Mapping[Endpoint, No],
    loops: Sequence[Mapping[str, Any]],
    rotas_loop: Sequence[RotaLoop] = (),
) -> list[tuple[int, str]]:
    caixas_usadas: list[Retangulo] = []
    legenda: list[tuple[int, str]] = []
    segmentos_por_rota = {
        rota.evento.indice: _segmentos(rota.pontos) for rota in rotas
    }
    todos_segmentos = [
        (rota.evento.indice, segmento)
        for rota in rotas
        for segmento in segmentos_por_rota[rota.evento.indice]
    ]
    area = geometria.area_rotas
    caixas_portas = [
        Retangulo(x - 7, y - 7, 14, 14)
        for x, y in (
            geometria.coordenada_no(no) for no in set(portas.values())
        )
    ]

    def valida(caixa: Retangulo, rota: Rota) -> bool:
        if not area.contem(caixa, margem=2.0):
            return False
        if any(caixa.expandido(3).cruza(outra) for outra in caixas_usadas):
            return False
        if any(caixa.expandido(1).cruza(porta) for porta in caixas_portas):
            return False
        for indice_rota, segmento in todos_segmentos:
            if indice_rota == rota.evento.indice:
                continue
            if _retangulo_cruza_segmento(caixa, segmento, margem=3.0):
                return False
        # Os conectores internos do loop são desenhados de forma leve e
        # tracejada. O fundo branco dos rótulos pode interrompê-los sem
        # prejudicar a leitura; por isso eles não bloqueiam a posição de um
        # rótulo de comando.
        return True

    for rota in rotas:
        texto = _texto_evento_para_mapa(rota.evento, loops)
        escolhida: Retangulo | None = None

        for caixa in _candidatos_rotulo(rota, texto, fonte=12.5):
            if valida(caixa, rota):
                escolhida = caixa
                rota.rotulo = texto
                break

        if escolhida is None:
            numero = len(legenda) + 1
            curto = str(numero)
            for caixa in _candidatos_rotulo(rota, curto, fonte=11.0):
                if valida(caixa, rota):
                    escolhida = caixa
                    rota.rotulo = curto
                    rota.usa_numero = True
                    legenda.append((numero, texto))
                    break

        if escolhida is None:
            numero = len(legenda) + 1
            segmentos = segmentos_por_rota[rota.evento.indice]
            if segmentos:
                segmento = max(segmentos, key=_comprimento_segmento)
                x1, y1, x2, y2 = segmento
                centro_x = (x1 + x2) / 2
                centro_y = (y1 + y2) / 2
            else:
                centro_x, centro_y = rota.pontos[0]

            for raio in range(0, 145, 10):
                offsets = (
                    (0, -raio),
                    (raio, 0),
                    (0, raio),
                    (-raio, 0),
                )
                for dx, dy in offsets:
                    caixa = _caixa_texto(
                        str(numero),
                        centro_x + dx,
                        centro_y + dy,
                        11.0,
                    )
                    if valida(caixa, rota):
                        escolhida = caixa
                        rota.rotulo = str(numero)
                        rota.usa_numero = True
                        legenda.append((numero, texto))
                        break
                if escolhida is not None:
                    break

        if escolhida is None:
            ponto = rota.pontos[len(rota.pontos) // 2]
            escolhida = _caixa_texto(str(len(legenda) + 1), *ponto, 11.0)
            numero = len(legenda) + 1
            rota.rotulo = str(numero)
            rota.usa_numero = True
            legenda.append((numero, texto))

        rota.caixa_rotulo = escolhida
        caixas_usadas.append(escolhida)

    return legenda


# ---------------------------------------------------------------------------
# Cabeçalhos, grade e elementos SVG
# ---------------------------------------------------------------------------


def _cabecalho_horizontal(geometria: Geometria, corpo: list[str]) -> None:
    dimensoes = geometria.eixo_horizontal.dimensoes
    estados = geometria.eixo_horizontal.estados
    if not dimensoes:
        return

    y_base = geometria.fim_cabecalho_y
    interna = len(dimensoes) - 1
    dim_interna = dimensoes[interna]

    for coluna, estado in enumerate(estados):
        x = geometria.grade_x + (coluna + 0.5) * geometria.celula_largura
        corpo.append(
            f'<text x="{x:.2f}" y="{y_base - 12:.2f}" text-anchor="middle" '
            f'font-family="{FONTE}" font-size="13" font-weight="700" fill="{TEXTO}">'
            f'{escape(dim_interna.rotulos[estado[interna]])}</text>'
        )

    for profundidade in range(len(dimensoes) - 1):
        dim = dimensoes[profundidade]
        valores = [estado[profundidade] for estado in estados]
        nivel = len(dimensoes) - 2 - profundidade
        y = y_base - 45.0 - nivel * 31.0
        for inicio, fim, valor in _runs(valores):
            x1 = geometria.grade_x + inicio * geometria.celula_largura + 7
            x2 = geometria.grade_x + (fim + 1) * geometria.celula_largura - 7
            centro = (x1 + x2) / 2
            corpo.append(
                f'<path d="M{x1:.2f},{y + 12:.2f} V{y + 2:.2f} H{x2:.2f} V{y + 12:.2f}" '
                f'fill="none" stroke="{GRADE}" stroke-width="1.0"/>'
            )
            corpo.append(
                f'<text x="{centro:.2f}" y="{y - 4:.2f}" text-anchor="middle" '
                f'font-family="{FONTE}" font-size="13" font-weight="700" fill="{TEXTO}">'
                f'{escape(dim.rotulos[valor])}</text>'
            )


def _cabecalho_vertical(geometria: Geometria, corpo: list[str]) -> None:
    dimensoes = geometria.eixo_vertical.dimensoes
    estados = geometria.eixo_vertical.estados
    if not dimensoes:
        return

    x_base = geometria.fim_cabecalho_x
    interna = len(dimensoes) - 1
    dim_interna = dimensoes[interna]

    for linha, estado in enumerate(estados):
        y = geometria.grade_y + (linha + 0.5) * geometria.celula_altura + 4
        corpo.append(
            f'<text x="{x_base - 12:.2f}" y="{y:.2f}" text-anchor="end" '
            f'font-family="{FONTE}" font-size="13" font-weight="700" fill="{TEXTO}">'
            f'{escape(dim_interna.rotulos[estado[interna]])}</text>'
        )

    for profundidade in range(len(dimensoes) - 1):
        dim = dimensoes[profundidade]
        valores = [estado[profundidade] for estado in estados]
        nivel = len(dimensoes) - 2 - profundidade
        x = x_base - 48.0 - nivel * 48.0
        for inicio, fim, valor in _runs(valores):
            y1 = geometria.grade_y + inicio * geometria.celula_altura + 7
            y2 = geometria.grade_y + (fim + 1) * geometria.celula_altura - 7
            centro = (y1 + y2) / 2
            corpo.append(
                f'<path d="M{x + 12:.2f},{y1:.2f} H{x + 2:.2f} V{y2:.2f} H{x + 12:.2f}" '
                f'fill="none" stroke="{GRADE}" stroke-width="1.0"/>'
            )
            corpo.append(
                f'<text x="{x - 4:.2f}" y="{centro + 4:.2f}" text-anchor="end" '
                f'font-family="{FONTE}" font-size="13" font-weight="700" fill="{TEXTO}">'
                f'{escape(dim.rotulos[valor])}</text>'
            )


def _celulas_decisao(
    geometria: Geometria,
    eventos: Sequence[EventoMapa],
    loops: Sequence[Mapping[str, Any]],
) -> set[tuple[int, int]]:
    saida: set[tuple[int, int]] = set()
    for loop in loops:
        fim = int(loop.get("fim", -1))
        candidatos = [
            evento
            for evento in eventos
            if evento.tipo == "atuador" and evento.etapa_indice == fim
        ]
        if candidatos:
            saida.add(geometria.celula(candidatos[-1].destino))
    return saida


def _grade(
    geometria: Geometria,
    eventos: Sequence[EventoMapa],
    loops: Sequence[Mapping[str, Any]],
    corpo: list[str],
) -> None:
    visitadas: set[tuple[int, int]] = set()
    for evento in eventos:
        visitadas.add(geometria.celula(evento.origem))
        visitadas.add(geometria.celula(evento.destino))

    inicial = geometria.celula(eventos[0].origem)
    decisoes = _celulas_decisao(geometria, eventos, loops)

    for linha in range(geometria.linhas):
        for coluna in range(geometria.colunas):
            x = geometria.grade_x + coluna * geometria.celula_largura
            y = geometria.grade_y + linha * geometria.celula_altura
            celula = (coluna, linha)
            if celula == inicial:
                fill = CELULA_INICIAL
            elif celula in decisoes:
                fill = CELULA_DECISAO
            elif celula in visitadas:
                fill = CELULA_ALCANCADA
            else:
                fill = FUNDO
            corpo.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{geometria.celula_largura:.2f}" '
                f'height="{geometria.celula_altura:.2f}" fill="{fill}" '
                f'stroke="{GRADE_SUAVE}" stroke-width="0.75"/>'
            )

    corpo.append(
        f'<rect x="{geometria.grade_x:.2f}" y="{geometria.grade_y:.2f}" '
        f'width="{geometria.grade_largura:.2f}" height="{geometria.grade_altura:.2f}" '
        f'fill="none" stroke="{GRADE}" stroke-width="1.35"/>'
    )


def _path_svg(pontos: Sequence[tuple[float, float]]) -> str:
    if not pontos:
        return ""
    partes = [f"M{pontos[0][0]:.2f},{pontos[0][1]:.2f}"]
    partes.extend(f"L{x:.2f},{y:.2f}" for x, y in pontos[1:])
    return " ".join(partes)


def _cor_evento(evento: EventoMapa) -> str:
    return SETA_MEMORIA if evento.tipo == "memoria" else SETA_ATUADOR


def _evento_da_etapa(
    eventos: Sequence[EventoMapa],
    etapa_indice: int,
    *,
    primeiro: bool,
) -> EventoMapa | None:
    encontrados = [
        evento
        for evento in eventos
        if evento.tipo == "atuador" and evento.etapa_indice == etapa_indice
    ]
    if not encontrados:
        return None
    return encontrados[0] if primeiro else encontrados[-1]


def _indice_track(valor: float, tracks: Sequence[float]) -> int | None:
    if not tracks:
        return None
    indice = min(range(len(tracks)), key=lambda i: abs(tracks[i] - valor))
    if abs(tracks[indice] - valor) > 1e-5:
        return None
    return indice


def _nos_do_segmento(
    geometria: Geometria,
    inicio: tuple[float, float],
    fim: tuple[float, float],
) -> list[No]:
    ix1 = _indice_track(inicio[0], geometria.x_tracks)
    iy1 = _indice_track(inicio[1], geometria.y_tracks)
    ix2 = _indice_track(fim[0], geometria.x_tracks)
    iy2 = _indice_track(fim[1], geometria.y_tracks)
    if None in {ix1, iy1, ix2, iy2}:
        return []

    assert ix1 is not None and iy1 is not None
    assert ix2 is not None and iy2 is not None

    if ix1 == ix2:
        passo = 1 if iy2 >= iy1 else -1
        return [(ix1, iy) for iy in range(iy1, iy2 + passo, passo)]
    if iy1 == iy2:
        passo = 1 if ix2 >= ix1 else -1
        return [(ix, iy1) for ix in range(ix1, ix2 + passo, passo)]
    return []


def _nos_da_rota(
    geometria: Geometria,
    pontos: Sequence[tuple[float, float]],
) -> list[No]:
    saida: list[No] = []
    for inicio, fim in zip(pontos, pontos[1:]):
        trecho = _nos_do_segmento(geometria, inicio, fim)
        if not trecho:
            continue
        if saida and saida[-1] == trecho[0]:
            saida.extend(trecho[1:])
        else:
            saida.extend(trecho)
    if not saida and pontos:
        ix = _indice_track(pontos[0][0], geometria.x_tracks)
        iy = _indice_track(pontos[0][1], geometria.y_tracks)
        if ix is not None and iy is not None:
            saida.append((ix, iy))
    return saida


def _ocupacao_das_rotas(
    geometria: Geometria,
    rotas: Sequence[Rota],
    portas: Mapping[Endpoint, No],
) -> tuple[set[No], set[Aresta]]:
    nos: set[No] = set(portas.values())
    arestas: set[Aresta] = set()
    for rota in rotas:
        caminho = _nos_da_rota(geometria, rota.pontos)
        nos.update(caminho)
        arestas.update(_aresta(a, b) for a, b in zip(caminho, caminho[1:]))
    return nos, arestas


def _segmento_externo(
    geometria: Geometria,
    lado: Literal["topo", "direita", "fundo", "esquerda"],
    trilho: int,
    origem: No,
    destino: No,
) -> tuple[No, No, list[No]]:
    if lado in {"topo", "fundo"}:
        portal_origem = (origem[0], trilho)
        portal_destino = (destino[0], trilho)
        if portal_origem == portal_destino:
            alternativas = [
                destino[0] + deslocamento
                for deslocamento in (1, -1, 2, -2)
                if 0 <= destino[0] + deslocamento < geometria.nx
            ]
            if alternativas:
                portal_destino = (alternativas[0], trilho)
        passo = 1 if portal_destino[0] >= portal_origem[0] else -1
        externo = [
            (ix, trilho)
            for ix in range(
                portal_origem[0],
                portal_destino[0] + passo,
                passo,
            )
        ]
    else:
        portal_origem = (trilho, origem[1])
        portal_destino = (trilho, destino[1])
        if portal_origem == portal_destino:
            alternativas = [
                destino[1] + deslocamento
                for deslocamento in (1, -1, 2, -2)
                if 0 <= destino[1] + deslocamento < geometria.ny
            ]
            if alternativas:
                portal_destino = (trilho, alternativas[0])
        passo = 1 if portal_destino[1] >= portal_origem[1] else -1
        externo = [
            (trilho, iy)
            for iy in range(
                portal_origem[1],
                portal_destino[1] + passo,
                passo,
            )
        ]
    return portal_origem, portal_destino, externo


def _custo_caminho_loop(
    geometria: Geometria,
    caminho: Sequence[No],
    lado: Literal["topo", "direita", "fundo", "esquerda"],
) -> float:
    comprimento = 0.0
    curvas = 0
    direcao_anterior: str | None = None
    for a, b in zip(caminho, caminho[1:]):
        x1, y1 = geometria.coordenada_no(a)
        x2, y2 = geometria.coordenada_no(b)
        comprimento += abs(x2 - x1) + abs(y2 - y1)
        direcao = "H" if a[1] == b[1] else "V"
        if direcao_anterior is not None and direcao != direcao_anterior:
            curvas += 1
        direcao_anterior = direcao

    # A direita costuma possuir mais área livre; topo e fundo ainda são
    # preferíveis quando encurtam bastante os conectores internos.
    penalidade_lado = {
        "direita": 0.0,
        "topo": 8.0,
        "fundo": 12.0,
        "esquerda": 18.0,
    }[lado]
    return comprimento + curvas * 12.0 + penalidade_lado


def _montar_candidato_loop(
    geometria: Geometria,
    origem: No,
    destino: No,
    lado: Literal["topo", "direita", "fundo", "esquerda"],
    trilho: int,
    nos_ocupados: set[No],
    arestas_ocupadas: set[Aresta],
    *,
    permitir_cruzamentos: bool,
) -> list[No] | None:
    portal_origem, portal_destino, externo = _segmento_externo(
        geometria,
        lado,
        trilho,
        origem,
        destino,
    )

    arestas_externas = {
        _aresta(a, b) for a, b in zip(externo, externo[1:])
    }
    internos_externos = set(externo[1:-1])
    if arestas_externas & arestas_ocupadas:
        return None
    if internos_externos & nos_ocupados and not permitir_cruzamentos:
        return None

    # Tentativa 1: conector de saída, corredor externo e conector de retorno.
    caminho_saida = _a_estrela(
        geometria,
        origem,
        portal_origem,
        nos_ocupados | internos_externos,
        arestas_ocupadas | arestas_externas,
        permitir_cruzamentos=permitir_cruzamentos,
    )
    if caminho_saida is not None:
        nos_temp = nos_ocupados | internos_externos | set(caminho_saida[1:-1])
        arestas_temp = arestas_ocupadas | arestas_externas | {
            _aresta(a, b) for a, b in zip(caminho_saida, caminho_saida[1:])
        }
        caminho_retorno = _a_estrela(
            geometria,
            portal_destino,
            destino,
            nos_temp,
            arestas_temp,
            permitir_cruzamentos=permitir_cruzamentos,
        )
        if caminho_retorno is not None:
            return _juntar_caminhos(
                [caminho_saida, externo, caminho_retorno]
            )

    # Tentativa 2: planeja primeiro a reentrada. Em mapas compactos, isso
    # evita que o primeiro conector ocupe a única passagem livre do segundo.
    caminho_retorno = _a_estrela(
        geometria,
        portal_destino,
        destino,
        nos_ocupados | internos_externos,
        arestas_ocupadas | arestas_externas,
        permitir_cruzamentos=permitir_cruzamentos,
    )
    if caminho_retorno is None:
        return None

    nos_temp = nos_ocupados | internos_externos | set(caminho_retorno[1:-1])
    arestas_temp = arestas_ocupadas | arestas_externas | {
        _aresta(a, b) for a, b in zip(caminho_retorno, caminho_retorno[1:])
    }
    caminho_saida = _a_estrela(
        geometria,
        origem,
        portal_origem,
        nos_temp,
        arestas_temp,
        permitir_cruzamentos=permitir_cruzamentos,
    )
    if caminho_saida is None:
        return None
    return _juntar_caminhos([caminho_saida, externo, caminho_retorno])


def _literal_do_loop(loop: Mapping[str, Any]) -> str:
    literal = _texto(loop.get("literal_repeticao"))
    if literal:
        return literal
    sensor = _texto(loop.get("sensor", "e"))
    repetir = int(loop.get("repetir_quando", 0))
    return sensor if repetir else f"{sensor}'"


def _caixa_rotulo_loop(
    geometria: Geometria,
    pontos: Sequence[tuple[float, float]],
    literal: str,
) -> Retangulo | None:
    externos: list[tuple[float, tuple[float, float, float, float]]] = []
    esquerda = geometria.grade_x
    direita = geometria.grade_x + geometria.grade_largura
    topo = geometria.grade_y
    fundo = geometria.grade_y + geometria.grade_altura

    for segmento in _segmentos(pontos):
        x1, y1, x2, y2 = segmento
        horizontal = abs(y1 - y2) < 1e-9
        fora = (
            (horizontal and (y1 < topo - 1 or y1 > fundo + 1))
            or (not horizontal and (x1 < esquerda - 1 or x1 > direita + 1))
        )
        if fora:
            externos.append((_comprimento_segmento(segmento), segmento))

    if not externos:
        return None

    _, segmento = max(externos, key=lambda item: item[0])
    x1, y1, x2, y2 = segmento
    centro_x = (x1 + x2) / 2
    centro_y = (y1 + y2) / 2
    return _caixa_texto(
        literal,
        centro_x,
        centro_y,
        fonte=13.0,
        padding_x=8.0,
        padding_y=4.0,
    )


def _segmentos_se_cruzam(
    primeiro: tuple[float, float, float, float],
    segundo: tuple[float, float, float, float],
    *,
    tolerancia: float = 1e-6,
) -> bool:
    x1, y1, x2, y2 = primeiro
    x3, y3, x4, y4 = segundo
    h1 = abs(y1 - y2) <= tolerancia
    h2 = abs(y3 - y4) <= tolerancia

    if h1 and h2:
        if abs(y1 - y3) > tolerancia:
            return False
        a1, a2 = sorted((x1, x2))
        b1, b2 = sorted((x3, x4))
        return min(a2, b2) - max(a1, b1) > tolerancia

    if not h1 and not h2:
        if abs(x1 - x3) > tolerancia:
            return False
        a1, a2 = sorted((y1, y2))
        b1, b2 = sorted((y3, y4))
        return min(a2, b2) - max(a1, b1) > tolerancia

    horizontal = primeiro if h1 else segundo
    vertical = segundo if h1 else primeiro
    hx1, hy, hx2, _ = horizontal
    vx, vy1, _, vy2 = vertical
    minimo_x, maximo_x = sorted((hx1, hx2))
    minimo_y, maximo_y = sorted((vy1, vy2))
    return (
        minimo_x - tolerancia <= vx <= maximo_x + tolerancia
        and minimo_y - tolerancia <= hy <= maximo_y + tolerancia
    )


def _ponto_proximo(
    ponto: tuple[float, float],
    referencia: tuple[float, float],
    tolerancia: float = 2.0,
) -> bool:
    return (
        abs(ponto[0] - referencia[0]) <= tolerancia
        and abs(ponto[1] - referencia[1]) <= tolerancia
    )


def _intersecao_apenas_em_endpoint(
    primeiro: tuple[float, float, float, float],
    segundo: tuple[float, float, float, float],
    endpoints_validos: Sequence[tuple[float, float]],
) -> bool:
    pontos_primeiro = ((primeiro[0], primeiro[1]), (primeiro[2], primeiro[3]))
    pontos_segundo = ((segundo[0], segundo[1]), (segundo[2], segundo[3]))
    for p1 in pontos_primeiro:
        for p2 in pontos_segundo:
            if _ponto_proximo(p1, p2) and any(
                _ponto_proximo(p1, endpoint)
                for endpoint in endpoints_validos
            ):
                return True
    return False


def _rota_loop_por_corredor_direito(
    geometria: Geometria,
    origem: tuple[float, float],
    destino: tuple[float, float],
    celula_origem: tuple[int, int],
    celula_destino: tuple[int, int],
    numero: int,
    segmentos_ocupados: Sequence[tuple[float, float, float, float]],
    caixas_portas: Sequence[Retangulo],
) -> list[tuple[float, float]]:
    limite_grade = geometria.grade_x + geometria.grade_largura
    portal_x = limite_grade + 9.0
    corredor_x = (
        limite_grade
        + geometria.corredor
        + 28.0
        + numero * 24.0
    )

    def trilhos_da_celula(celula: tuple[int, int]) -> tuple[float, float]:
        _, linha = celula
        topo = geometria.grade_y + linha * geometria.celula_altura
        fundo = topo + geometria.celula_altura
        afastamento = min(7.0, geometria.celula_altura * 0.14)
        return topo + afastamento, fundo - afastamento

    trilhos_origem = trilhos_da_celula(celula_origem)
    trilhos_destino = trilhos_da_celula(celula_destino)
    candidatos: list[tuple[float, list[tuple[float, float]]]] = []

    for y_saida in trilhos_origem:
        for y_entrada in trilhos_destino:
            if (
                celula_origem[1] == celula_destino[1]
                and abs(y_saida - y_entrada) < 1.0
                and len(set(trilhos_origem + trilhos_destino)) > 1
            ):
                continue
            pontos = _simplificar_pontos(
                [
                    origem,
                    (origem[0], y_saida),
                    (portal_x, y_saida),
                    (corredor_x, y_saida),
                    (corredor_x, y_entrada),
                    (portal_x, y_entrada),
                    (destino[0], y_entrada),
                    destino,
                ]
            )
            segmentos = _segmentos(pontos)
            comprimento = sum(
                _comprimento_segmento(segmento)
                for segmento in segmentos
            )

            cruzamentos = 0
            sobreposicoes = 0
            endpoints = (origem, destino)
            for segmento_loop in segmentos:
                for segmento_existente in segmentos_ocupados:
                    if not _segmentos_se_cruzam(
                        segmento_loop,
                        segmento_existente,
                    ):
                        continue
                    if _intersecao_apenas_em_endpoint(
                        segmento_loop,
                        segmento_existente,
                        endpoints,
                    ):
                        continue

                    h1 = abs(segmento_loop[1] - segmento_loop[3]) < 1e-6
                    h2 = abs(segmento_existente[1] - segmento_existente[3]) < 1e-6
                    paralelos = h1 == h2
                    if paralelos:
                        sobreposicoes += 1
                    else:
                        cruzamentos += 1

            portas_tocadas = 0
            for caixa in caixas_portas:
                if any(
                    _retangulo_cruza_segmento(
                        caixa,
                        segmento,
                        margem=1.5,
                    )
                    for segmento in segmentos
                ):
                    centro = (
                        caixa.x + caixa.largura / 2,
                        caixa.y + caixa.altura / 2,
                    )
                    if not any(
                        _ponto_proximo(centro, endpoint, 8.0)
                        for endpoint in endpoints
                    ):
                        portas_tocadas += 1

            mesma_faixa = abs(y_saida - y_entrada) < 1.0
            penalidade_faixa = 90.0 if mesma_faixa else 0.0
            custo = (
                comprimento
                + cruzamentos * 260.0
                + sobreposicoes * 420.0
                + portas_tocadas * 130.0
                + penalidade_faixa
            )
            candidatos.append((custo, pontos))

    return min(candidatos, key=lambda item: item[0])[1]


def _rotear_loops_externos(
    geometria: Geometria,
    eventos: Sequence[EventoMapa],
    portas: Mapping[Endpoint, No],
    loops: Sequence[Mapping[str, Any]],
    rotas: Sequence[Rota],
) -> list[RotaLoop]:
    if not loops:
        return []

    segmentos_ocupados = [
        segmento
        for rota in rotas
        for segmento in _segmentos(rota.pontos)
    ]
    caixas_portas = [
        Retangulo(x - 6.5, y - 6.5, 13.0, 13.0)
        for x, y in (
            geometria.coordenada_no(no)
            for no in set(portas.values())
        )
    ]
    saida: list[RotaLoop] = []

    for numero, loop in enumerate(loops):
        inicio_etapa = int(loop.get("inicio", 0))
        fim_etapa = int(loop.get("fim", inicio_etapa))
        primeiro = _evento_da_etapa(eventos, inicio_etapa, primeiro=True)
        ultimo = _evento_da_etapa(eventos, fim_etapa, primeiro=False)
        if primeiro is None or ultimo is None:
            continue

        no_origem = portas[(ultimo.indice, "destino")]
        no_destino = portas[(primeiro.indice, "origem")]
        origem = geometria.coordenada_no(no_origem)
        destino = geometria.coordenada_no(no_destino)
        celula_origem = geometria.celula(ultimo.destino)
        celula_destino = geometria.celula(primeiro.origem)

        pontos = _rota_loop_por_corredor_direito(
            geometria,
            origem,
            destino,
            celula_origem,
            celula_destino,
            numero,
            segmentos_ocupados,
            caixas_portas,
        )
        literal = _literal_do_loop(loop)
        rota_loop = RotaLoop(
            numero=numero,
            pontos=pontos,
            literal=literal,
            lado="direita",
        )
        rota_loop.caixa_rotulo = _caixa_rotulo_loop(
            geometria,
            pontos,
            literal,
        )
        saida.append(rota_loop)
        segmentos_ocupados.extend(_segmentos(pontos))

    return saida


def _path_svg_arredondado(
    pontos: Sequence[tuple[float, float]],
    raio: float = 8.0,
) -> str:
    if not pontos:
        return ""
    if len(pontos) < 3:
        return _path_svg(pontos)

    partes = [f"M{pontos[0][0]:.2f},{pontos[0][1]:.2f}"]
    for indice in range(1, len(pontos) - 1):
        anterior = pontos[indice - 1]
        atual = pontos[indice]
        proximo = pontos[indice + 1]

        dx1 = atual[0] - anterior[0]
        dy1 = atual[1] - anterior[1]
        dx2 = proximo[0] - atual[0]
        dy2 = proximo[1] - atual[1]
        comprimento1 = abs(dx1) + abs(dy1)
        comprimento2 = abs(dx2) + abs(dy2)
        arredondamento = min(raio, comprimento1 / 2, comprimento2 / 2)

        if arredondamento <= 0.1 or (
            (abs(dx1) < 1e-9 and abs(dx2) < 1e-9)
            or (abs(dy1) < 1e-9 and abs(dy2) < 1e-9)
        ):
            partes.append(f"L{atual[0]:.2f},{atual[1]:.2f}")
            continue

        antes_x = atual[0] - (dx1 / comprimento1) * arredondamento
        antes_y = atual[1] - (dy1 / comprimento1) * arredondamento
        depois_x = atual[0] + (dx2 / comprimento2) * arredondamento
        depois_y = atual[1] + (dy2 / comprimento2) * arredondamento
        partes.append(f"L{antes_x:.2f},{antes_y:.2f}")
        partes.append(
            f"Q{atual[0]:.2f},{atual[1]:.2f} "
            f"{depois_x:.2f},{depois_y:.2f}"
        )

    partes.append(f"L{pontos[-1][0]:.2f},{pontos[-1][1]:.2f}")
    return " ".join(partes)


def _segmento_fora_da_grade(
    geometria: Geometria,
    segmento: tuple[float, float, float, float],
) -> bool:
    x1, y1, x2, y2 = segmento
    esquerda = geometria.grade_x
    direita = geometria.grade_x + geometria.grade_largura
    topo = geometria.grade_y
    fundo = geometria.grade_y + geometria.grade_altura
    return (
        (x1 < esquerda - 1 and x2 < esquerda - 1)
        or (x1 > direita + 1 and x2 > direita + 1)
        or (y1 < topo - 1 and y2 < topo - 1)
        or (y1 > fundo + 1 and y2 > fundo + 1)
    )


def _parte_externa_do_segmento(
    geometria: Geometria,
    inicio: tuple[float, float],
    fim: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    esquerda = geometria.grade_x
    direita = geometria.grade_x + geometria.grade_largura
    topo = geometria.grade_y
    fundo = geometria.grade_y + geometria.grade_altura
    x1, y1 = inicio
    x2, y2 = fim
    horizontal = abs(y1 - y2) < 1e-9

    if horizontal:
        if y1 < topo - 1 or y1 > fundo + 1:
            return inicio, fim
        if x1 <= direita < x2:
            return (direita, y1), fim
        if x2 <= direita < x1:
            return inicio, (direita, y1)
        if x1 >= esquerda > x2:
            return (esquerda, y1), fim
        if x2 >= esquerda > x1:
            return inicio, (esquerda, y1)
        if (x1 > direita and x2 > direita) or (
            x1 < esquerda and x2 < esquerda
        ):
            return inicio, fim
        return None

    if x1 < esquerda - 1 or x1 > direita + 1:
        return inicio, fim
    if y1 <= fundo < y2:
        return (x1, fundo), fim
    if y2 <= fundo < y1:
        return inicio, (x1, fundo)
    if y1 >= topo > y2:
        return (x1, topo), fim
    if y2 >= topo > y1:
        return inicio, (x1, topo)
    if (y1 > fundo and y2 > fundo) or (y1 < topo and y2 < topo):
        return inicio, fim
    return None


def _agrupar_segmentos_externos(
    geometria: Geometria,
    pontos: Sequence[tuple[float, float]],
) -> list[list[tuple[float, float]]]:
    grupos: list[list[tuple[float, float]]] = []
    atual: list[tuple[float, float]] = []

    for inicio, fim in zip(pontos, pontos[1:]):
        parte = _parte_externa_do_segmento(
            geometria,
            inicio,
            fim,
        )
        if parte is None:
            if atual:
                grupos.append(atual)
                atual = []
            continue

        parte_inicio, parte_fim = parte
        if not atual:
            atual = [parte_inicio, parte_fim]
        elif _ponto_proximo(atual[-1], parte_inicio, 0.2):
            atual.append(parte_fim)
        else:
            grupos.append(atual)
            atual = [parte_inicio, parte_fim]

    if atual:
        grupos.append(atual)
    return grupos


def _desenhar_loops(
    geometria: Geometria,
    rotas_loop: Sequence[RotaLoop],
    corpo: list[str],
) -> None:
    for rota in rotas_loop:
        d_completo = _path_svg_arredondado(rota.pontos, raio=7.0)

        # Dentro da grade, o conector é leve e tracejado. Assim ele informa
        # de onde o retorno sai e onde reentra, sem encobrir os comandos.
        corpo.append(
            f'<path d="{d_completo}" fill="none" stroke="{SETA_LOOP}" '
            f'stroke-width="1.25" stroke-opacity="0.68" '
            f'stroke-dasharray="5 4" stroke-linecap="round" '
            f'stroke-linejoin="round"/>'
        )

        # O trecho realmente externo recebe destaque contínuo e um halo
        # branco discreto. Ele funciona como o corredor principal do loop.
        for grupo in _agrupar_segmentos_externos(
            geometria,
            rota.pontos,
        ):
            d_externo = _path_svg_arredondado(grupo, raio=8.0)
            corpo.append(
                f'<path d="{d_externo}" fill="none" stroke="{FUNDO}" '
                f'stroke-width="4.6" stroke-linecap="round" '
                f'stroke-linejoin="round"/>'
            )
            corpo.append(
                f'<path d="{d_externo}" fill="none" stroke="{SETA_LOOP}" '
                f'stroke-width="1.9" stroke-linecap="round" '
                f'stroke-linejoin="round"/>'
            )

        # A seta é aplicada apenas na reentrada do loop. Isso evita várias
        # pontas de seta competindo com as transições internas do mapa.
        if len(rota.pontos) >= 2:
            trecho_final = rota.pontos[-2:]
            d_final = _path_svg(trecho_final)
            corpo.append(
                f'<path d="{d_final}" fill="none" stroke="{SETA_LOOP}" '
                f'stroke-width="1.65" stroke-linecap="round" '
                f'marker-end="url(#arrow-loop)"/>'
            )


def _desenhar_detalhes_loops(
    rotas_loop: Sequence[RotaLoop],
    corpo: list[str],
) -> None:
    for rota in rotas_loop:
        if rota.pontos:
            x1, y1 = rota.pontos[0]
            corpo.append(
                f'<circle cx="{x1:.2f}" cy="{y1:.2f}" r="4.5" '
                f'fill="{FUNDO}" stroke="{CONDICAO}" stroke-width="1.5"/>'
            )

        caixa = rota.caixa_rotulo
        if caixa is None:
            continue
        cx = caixa.x + caixa.largura / 2
        cy = caixa.y + caixa.altura / 2 + 4.0
        corpo.append(
            f'<rect x="{caixa.x:.2f}" y="{caixa.y:.2f}" '
            f'width="{caixa.largura:.2f}" height="{caixa.altura:.2f}" '
            f'rx="4" fill="{FUNDO}" fill-opacity="0.98" '
            f'stroke="{SETA_LOOP}" stroke-opacity="0.20" stroke-width="0.8"/>'
        )
        corpo.append(
            f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" '
            f'font-family="{FONTE}" font-size="13" font-weight="700" '
            f'fill="{CONDICAO}">{escape(rota.literal)}</text>'
        )


def _desenhar_partida_e_fim(
    geometria: Geometria,
    eventos: Sequence[EventoMapa],
    portas: Mapping[Endpoint, No],
    corpo: list[str],
) -> None:
    primeiro = eventos[0]
    no_inicial = portas[(primeiro.indice, "origem")]
    inicio_x, inicio_y = geometria.coordenada_no(no_inicial)

    origem_x = geometria.fim_cabecalho_x + 8.0
    origem_y = geometria.fim_cabecalho_y + 8.0
    corpo.append(
        f'<path d="M{origem_x:.2f},{origem_y:.2f} L{inicio_x:.2f},{inicio_y:.2f}" '
        f'fill="none" stroke="{SETA_ATUADOR}" stroke-width="1.45" marker-end="url(#arrow-act)"/>'
    )
    corpo.append(
        f'<text x="{origem_x - 2:.2f}" y="{origem_y - 10:.2f}" text-anchor="middle" '
        f'font-family="{FONTE}" font-size="15" font-weight="700" fill="{TEXTO}">S</text>'
    )

    ultimo = eventos[-1]
    no_final = portas[(ultimo.indice, "destino")]
    final_x, final_y = geometria.coordenada_no(no_final)
    mesmo = abs(final_x - inicio_x) < 0.1 and abs(final_y - inicio_y) < 0.1

    if mesmo:
        corpo.append(
            f'<circle cx="{inicio_x:.2f}" cy="{inicio_y:.2f}" r="8.0" fill="{FUNDO}" '
            f'stroke="{FINAL}" stroke-width="2.0"/>'
        )
        corpo.append(
            f'<circle cx="{inicio_x:.2f}" cy="{inicio_y:.2f}" r="3.8" fill="{INICIAL}"/>'
        )
    else:
        corpo.append(
            f'<circle cx="{inicio_x:.2f}" cy="{inicio_y:.2f}" r="4.2" fill="{INICIAL}"/>'
        )
        corpo.append(
            f'<circle cx="{final_x:.2f}" cy="{final_y:.2f}" r="6.5" fill="{FUNDO}" '
            f'stroke="{FINAL}" stroke-width="2.0"/>'
        )


def _renderizar_rotulo(corpo: list[str], rota: Rota) -> None:
    if rota.caixa_rotulo is None:
        return
    caixa = rota.caixa_rotulo
    cor = _cor_evento(rota.evento)
    cx = caixa.x + caixa.largura / 2
    cy = caixa.y + caixa.altura / 2 + 4.0

    if rota.usa_numero:
        raio = min(8.5, caixa.altura / 2)
        corpo.append(
            f'<circle cx="{cx:.2f}" cy="{caixa.y + caixa.altura / 2:.2f}" r="{raio:.2f}" '
            f'fill="{FUNDO}" stroke="{cor}" stroke-width="0.9"/>'
        )
        corpo.append(
            f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" '
            f'font-family="{FONTE}" font-size="10.5" font-weight="700" fill="{TEXTO}">'
            f'{escape(rota.rotulo)}</text>'
        )
        return

    texto = rota.rotulo
    corpo.append(
        f'<rect x="{caixa.x:.2f}" y="{caixa.y:.2f}" width="{caixa.largura:.2f}" '
        f'height="{caixa.altura:.2f}" rx="3" fill="{FUNDO}" fill-opacity="0.93"/>'
    )

    if " · " in texto:
        comando, condicao = texto.rsplit(" · ", 1)
        largura_comando = _largura_texto(comando, 12.5)
        largura_sep = _largura_texto(" · ", 12.5)
        largura_cond = _largura_texto(condicao, 12.5)
        total = largura_comando + largura_sep + largura_cond
        inicio = cx - total / 2
        corpo.append(
            f'<text x="{inicio:.2f}" y="{cy:.2f}" font-family="{FONTE}" '
            f'font-size="12.5" font-weight="700" fill="{TEXTO}">'
            f'{escape(comando)}<tspan fill="{TEXTO_SUAVE}"> · </tspan>'
            f'<tspan fill="{CONDICAO}">{escape(condicao)}</tspan></text>'
        )
    else:
        corpo.append(
            f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" '
            f'font-family="{FONTE}" font-size="12.5" font-weight="700" fill="{TEXTO}">'
            f'{escape(texto)}</text>'
        )


def _altura_legendas(
    geometria: Geometria,
    legenda_numerica: Sequence[tuple[int, str]],
    quantidade_itens_visuais: int,
) -> tuple[int, int, int]:
    largura_disponivel = geometria.largura - 2 * geometria.margem
    colunas_visual = 3 if largura_disponivel >= 760 else 2
    linhas_visual = ceil(quantidade_itens_visuais / colunas_visual)
    altura_visual = 34 + linhas_visual * 25

    if legenda_numerica:
        maior_item = max(
            _largura_texto(f"{numero}. {texto}", 11.5)
            for numero, texto in legenda_numerica
        ) + 22
        colunas_numerica = max(
            1,
            min(4, int(largura_disponivel // max(185.0, maior_item))),
        )
        linhas_numerica = ceil(len(legenda_numerica) / colunas_numerica)
        altura_numerica = 32 + linhas_numerica * 23
    else:
        colunas_numerica = 1
        altura_numerica = 0

    return altura_visual, altura_numerica, colunas_numerica


def _desenhar_legendas(
    geometria: Geometria,
    legenda_numerica: Sequence[tuple[int, str]],
    altura_visual: int,
    altura_numerica: int,
    colunas_numerica: int,
    corpo: list[str],
    *,
    possui_memoria: bool,
    possui_loop: bool,
) -> None:
    largura_disponivel = geometria.largura - 2 * geometria.margem
    base = geometria.altura_base
    corpo.append(
        f'<line x1="{geometria.margem:.2f}" y1="{base + 2:.2f}" '
        f'x2="{geometria.largura - geometria.margem:.2f}" y2="{base + 2:.2f}" '
        f'stroke="{GRADE_SUAVE}" stroke-width="1"/>'
    )
    corpo.append(
        f'<text x="{geometria.margem:.2f}" y="{base + 20:.2f}" '
        f'font-family="{FONTE}" font-size="11.5" font-weight="700" fill="{TEXTO}">Legenda</text>'
    )

    itens_lista = [("atuador", "Movimento de atuador")]
    if possui_memoria:
        itens_lista.append(("memoria", "Mudança de memória"))
    if possui_loop:
        itens_lista.append(("loop", "Retorno do loop"))
    itens_lista.extend((("inicial", "Estado inicial"), ("final", "Estado final")))
    itens = tuple(itens_lista)
    colunas_visual = 3 if largura_disponivel >= 760 else 2
    largura_item = largura_disponivel / colunas_visual

    for indice, (tipo, texto) in enumerate(itens):
        linha = indice // colunas_visual
        coluna = indice % colunas_visual
        x_item = geometria.margem + coluna * largura_item + 4
        y_item = base + 42 + linha * 25
        x_simbolo = x_item + 16
        x_texto = x_item + 43

        if tipo == "atuador":
            corpo.append(
                f'<line x1="{x_simbolo - 12:.2f}" y1="{y_item - 4:.2f}" '
                f'x2="{x_simbolo + 12:.2f}" y2="{y_item - 4:.2f}" '
                f'stroke="{SETA_ATUADOR}" stroke-width="1.7" marker-end="url(#arrow-act)"/>'
            )
        elif tipo == "memoria":
            corpo.append(
                f'<line x1="{x_simbolo - 12:.2f}" y1="{y_item - 4:.2f}" '
                f'x2="{x_simbolo + 12:.2f}" y2="{y_item - 4:.2f}" '
                f'stroke="{SETA_MEMORIA}" stroke-width="1.7" stroke-dasharray="6 4" '
                f'marker-end="url(#arrow-mem)"/>'
            )
        elif tipo == "loop":
            corpo.append(
                f'<path d="M{x_simbolo - 12:.2f},{y_item - 4:.2f} '
                f'C{x_simbolo - 3:.2f},{y_item - 14:.2f} '
                f'{x_simbolo + 6:.2f},{y_item + 4:.2f} '
                f'{x_simbolo + 12:.2f},{y_item - 4:.2f}" fill="none" '
                f'stroke="{SETA_LOOP}" stroke-width="1.7" marker-end="url(#arrow-loop)"/>'
            )
        elif tipo == "inicial":
            corpo.append(
                f'<circle cx="{x_simbolo:.2f}" cy="{y_item - 4:.2f}" r="4.2" fill="{INICIAL}"/>'
            )
        else:
            corpo.append(
                f'<circle cx="{x_simbolo:.2f}" cy="{y_item - 4:.2f}" r="6.2" '
                f'fill="{FUNDO}" stroke="{FINAL}" stroke-width="1.8"/>'
            )

        corpo.append(
            f'<text x="{x_texto:.2f}" y="{y_item:.2f}" font-family="{FONTE}" '
            f'font-size="11" fill="{TEXTO}">{escape(texto)}</text>'
        )

    if not legenda_numerica:
        return

    base_num = geometria.altura_base + altura_visual
    corpo.append(
        f'<line x1="{geometria.margem:.2f}" y1="{base_num + 1:.2f}" '
        f'x2="{geometria.largura - geometria.margem:.2f}" y2="{base_num + 1:.2f}" '
        f'stroke="{GRADE_SUAVE}" stroke-width="1"/>'
    )
    corpo.append(
        f'<text x="{geometria.margem:.2f}" y="{base_num + 19:.2f}" '
        f'font-family="{FONTE}" font-size="11.5" font-weight="700" fill="{TEXTO}">'
        f'Rótulos numerados</text>'
    )

    largura_coluna = largura_disponivel / colunas_numerica
    for indice, (numero, texto) in enumerate(legenda_numerica):
        linha = indice // colunas_numerica
        coluna = indice % colunas_numerica
        x = geometria.margem + coluna * largura_coluna
        y = base_num + 41 + linha * 23
        corpo.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FONTE}" font-size="11.5" '
            f'fill="{TEXTO}"><tspan font-weight="700">{numero}.</tspan> '
            f'{escape(texto)}</text>'
        )


# ---------------------------------------------------------------------------
# Renderização principal
# ---------------------------------------------------------------------------


def _renderizar_mapa(
    resultado: Mapping[str, Any],
    dimensoes: Sequence[Dimensao],
    eventos: list[EventoMapa],
    *,
    incluir_titulo: bool,
) -> MapaSVG:
    max_grupos = _maximo_grupos_por_estado(eventos)
    lanes_inicial = max(3, ceil(sqrt(max_grupos)) + 2)
    lanes_final = max(lanes_inicial, min(13, lanes_inicial + 6))

    geometria: Geometria | None = None
    rotas: list[Rota] | None = None
    portas: dict[Endpoint, No] | None = None

    for lanes in range(lanes_inicial, lanes_final + 1):
        geometria_teste = _construir_geometria(
            resultado,
            dimensoes,
            eventos,
            incluir_titulo=incluir_titulo,
            lanes=lanes,
        )
        try:
            portas_teste = _atribuir_portas(geometria_teste, eventos)
        except RuntimeError:
            continue

        rotas_teste = _rotear_eventos(
            geometria_teste,
            eventos,
            portas_teste,
            permitir_cruzamentos=False,
        )
        if rotas_teste is not None:
            geometria = geometria_teste
            rotas = rotas_teste
            portas = portas_teste
            break

    if geometria is None or rotas is None or portas is None:
        lanes = min(15, max(lanes_final + 1, lanes_inicial + 3))
        geometria = _construir_geometria(
            resultado,
            dimensoes,
            eventos,
            incluir_titulo=incluir_titulo,
            lanes=lanes,
        )
        portas = _atribuir_portas(geometria, eventos)
        rotas = _rotear_eventos(
            geometria,
            eventos,
            portas,
            permitir_cruzamentos=True,
        )
        if rotas is None:
            raise RuntimeError(
                "Não foi possível organizar todas as transições do mapa sem comprometer a leitura."
            )

    loops = list(resultado.get("loops") or [])
    rotas_loop = _rotear_loops_externos(
        geometria,
        eventos,
        portas,
        loops,
        rotas,
    )
    legenda_numerica = _posicionar_rotulos(
        rotas,
        geometria,
        portas,
        loops,
        rotas_loop,
    )
    possui_memoria = any(evento.tipo == "memoria" for evento in eventos)
    possui_loop = bool(loops)
    quantidade_itens_visuais = 3 + int(possui_memoria) + int(possui_loop)
    altura_visual, altura_numerica, colunas_numerica = _altura_legendas(
        geometria,
        legenda_numerica,
        quantidade_itens_visuais,
    )
    altura = geometria.altura_base + altura_visual + altura_numerica

    corpo: list[str] = []

    if incluir_titulo:
        corpo.append(
            f'<text x="{geometria.largura / 2:.2f}" y="31" text-anchor="middle" '
            f'font-family="{FONTE}" font-size="22" font-weight="700" fill="{TEXTO}">'
            f'Mapa de Karnaugh Estendido</text>'
        )
        y = 57.0
        for linha in geometria.linhas_sequencia:
            corpo.append(
                f'<text x="{geometria.largura / 2:.2f}" y="{y:.2f}" text-anchor="middle" '
                f'font-family="{FONTE}" font-size="14" font-weight="500" fill="{TEXTO}">'
                f'{escape(linha)}</text>'
            )
            y += 19.0

    _cabecalho_horizontal(geometria, corpo)
    _cabecalho_vertical(geometria, corpo)
    _grade(geometria, eventos, loops, corpo)

    # Retornos de loop usam corredores externos dedicados. Os pequenos
    # conectores até a grade são roteados evitando as transições existentes.
    _desenhar_loops(geometria, rotas_loop, corpo)

    # Halo branco diferencia cruzamentos residuais.
    for rota in rotas:
        corpo.append(
            f'<path d="{_path_svg(rota.pontos)}" fill="none" stroke="{FUNDO}" '
            f'stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    for rota in rotas:
        cor = _cor_evento(rota.evento)
        tracejado = (
            ' stroke-dasharray="6 4"' if rota.evento.tipo == "memoria" else ""
        )
        marcador = "arrow-mem" if rota.evento.tipo == "memoria" else "arrow-act"
        corpo.append(
            f'<path d="{_path_svg(rota.pontos)}" fill="none" stroke="{cor}" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"'
            f'{tracejado} marker-end="url(#{marcador})"/>'
        )

    _desenhar_partida_e_fim(geometria, eventos, portas, corpo)

    for rota in rotas:
        _renderizar_rotulo(corpo, rota)

    # Rótulo e ponto de decisão do loop são desenhados por último para
    # permanecerem legíveis, sem cobrir as setas de comando.
    _desenhar_detalhes_loops(rotas_loop, corpo)

    _desenhar_legendas(
        geometria,
        legenda_numerica,
        altura_visual,
        altura_numerica,
        colunas_numerica,
        corpo,
        possui_memoria=possui_memoria,
        possui_loop=possui_loop,
    )

    definicoes = f"""
    <defs>
        <marker id="arrow-act" markerWidth="6" markerHeight="6" refX="5.3" refY="3"
                orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L6,3 L0,6 z" fill="{SETA_ATUADOR}"/>
        </marker>
        <marker id="arrow-mem" markerWidth="6" markerHeight="6" refX="5.3" refY="3"
                orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L6,3 L0,6 z" fill="{SETA_MEMORIA}"/>
        </marker>
        <marker id="arrow-loop" markerWidth="6" markerHeight="6" refX="5.3" refY="3"
                orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L6,3 L0,6 z" fill="{SETA_LOOP}"/>
        </marker>
    </defs>
    """

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {geometria.largura} {altura}" '
        f'width="{geometria.largura}" height="{altura}" '
        f'role="img" aria-label="Mapa de Karnaugh Estendido">'
        f'<rect width="{geometria.largura}" height="{altura}" fill="{FUNDO}"/>'
        + definicoes
        + "".join(corpo)
        + "</svg>"
    )
    return MapaSVG(svg=svg, largura=geometria.largura, altura=altura)


# ---------------------------------------------------------------------------
# Avisos e API pública
# ---------------------------------------------------------------------------


def _svg_aviso(titulo: str, mensagem: str, detalhe: str = "") -> MapaSVG:
    largura = 900
    altura = 330
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'width="{largura}" height="{altura}" role="img" aria-label="{escape(titulo)}">'
        f'<rect width="{largura}" height="{altura}" fill="{FUNDO}"/>'
        f'<rect x="38" y="34" width="824" height="258" rx="13" fill="#FFF8F2" '
        f'stroke="#A33A24" stroke-width="2"/>'
        f'<circle cx="92" cy="93" r="26" fill="#A33A24"/>'
        f'<text x="92" y="103" text-anchor="middle" font-family="{FONTE}" '
        f'font-size="31" font-weight="700" fill="#FFFFFF">!</text>'
        f'<text x="136" y="84" font-family="{FONTE}" font-size="25" '
        f'font-weight="700" fill="#7A2417">{escape(titulo)}</text>'
        f'<text x="72" y="157" font-family="{FONTE}" font-size="16" fill="{TEXTO}">'
        f'{escape(mensagem)}</text>'
        f'<text x="72" y="205" font-family="{FONTE}" font-size="14" fill="{TEXTO_SUAVE}">'
        f'{escape(detalhe)}</text>'
        f'</svg>'
    )
    return MapaSVG(svg=svg, largura=largura, altura=altura)


def gerar_mapa_svg(
    resultado: Mapping[str, Any],
    *,
    incluir_titulo: bool = True,
    modo: Literal["auto", "completo", "alcancaveis"] = "auto",
    limite_mapa_completo: int | None = None,
    limite_celulas: int = LIMITE_PADRAO_CELULAS,
) -> MapaSVG:
    """Gera o Mapa de Karnaugh Estendido em SVG.

    ``resultado`` deve ser, preferencialmente, o dicionário retornado por
    ``src.solver.resolver_site``. O formato anterior do projeto continua
    aceito quando fornece ``etapas`` e os estados correspondentes.

    O mapa usa a quantidade real de posições de cada atuador. Um atuador B com
    ``b0, b1, b2, b3`` ocupa quatro estados no eixo, e não quatro variáveis
    booleanas independentes.
    """

    if modo not in {"auto", "completo", "alcancaveis"}:
        raise ValueError("modo deve ser 'auto', 'completo' ou 'alcancaveis'.")
    if limite_celulas < 1:
        raise ValueError("limite_celulas deve ser maior que zero.")

    dimensoes = _construir_dimensoes(resultado)
    total_celulas = _produto_dimensoes(dimensoes)

    if limite_mapa_completo is not None:
        if limite_mapa_completo < 0:
            raise ValueError("limite_mapa_completo não pode ser negativo.")
        limite_legado = 1 << limite_mapa_completo
        limite_celulas = min(limite_celulas, limite_legado)

    if total_celulas > limite_celulas:
        descricao = " × ".join(
            f"{dim.nome}({dim.quantidade})" for dim in dimensoes
        )
        return _svg_aviso(
            "Mapa muito grande para exibição",
            f"O mapa teria {total_celulas} células, acima do limite de {limite_celulas}.",
            f"Dimensões consideradas: {descricao}.",
        )

    eventos = _eventos_do_resultado(resultado, dimensoes)
    return _renderizar_mapa(
        resultado,
        dimensoes,
        eventos,
        incluir_titulo=incluir_titulo,
    )


__all__ = [
    "MapaSVG",
    "gerar_mapa_svg",
    "LIMITE_PADRAO_CELULAS",
]