from __future__ import annotations

"""Gerador adaptativo de Mapas de Karnaugh Estendido em SVG.

A função pública continua compatível com as versões anteriores::

    mapa = gerar_mapa_svg(resultado, incluir_titulo=True)
    mapa.svg
    mapa.largura
    mapa.altura

Características desta versão
----------------------------
* dimensões calculadas a partir da quantidade real de transições;
* estados consecutivos compartilham o mesmo ponto de passagem;
* portas, corredores e arestas são reservados para evitar sobreposição;
* corredores externos permitem contornar as bordas do mapa;
* rótulos possuem detecção de colisão e legenda automática de segurança;
* títulos e sequências longas são quebrados em várias linhas;
* o mapa estendido completo é sempre utilizado;
* mapas acima do limite de 256 células exibem um aviso claro, sem tentar
  gerar uma representação alternativa.

O módulo usa somente a biblioteca-padrão do Python.
"""

from dataclasses import dataclass
from heapq import heappop, heappush
from html import escape
from itertools import count, permutations
from math import ceil, sqrt
from typing import Any, Iterable, Iterator, Literal, Mapping, Sequence


# ---------------------------------------------------------------------------
# Aparência
# ---------------------------------------------------------------------------

FUNDO = "#FFFFFF"
GRADE = "#4F4F4F"
GRADE_SUAVE = "#C8C8C8"
TEXTO = "#111111"
TEXTO_SUAVE = "#666666"
SETA_ATUADOR = "#111111"
SETA_MEMORIA = "#335F7A"
SETA_SIMULTANEA = "#111111"
INICIAL = "#7A1024"
FINAL = "#267449"
CAIXA_ESTADO = "#F8F8F8"
BORDA_ESTADO = "#BEBEBE"

FONTE = "Arial, Helvetica, sans-serif"
LIMITE_PADRAO_CELULAS = 1 << 8  # 256 células = 2^8


# ---------------------------------------------------------------------------
# Estruturas públicas e internas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MapaSVG:
    svg: str
    largura: int
    altura: int


@dataclass(frozen=True)
class EventoMapa:
    indice: int
    tipo: Literal["atuador", "memoria"]
    comandos: tuple[str, ...]
    origem_fisica: dict[str, int]
    destino_fisico: dict[str, int]
    origem_memoria: dict[str, int]
    destino_memoria: dict[str, int]

    @property
    def texto(self) -> str:
        if not self.comandos:
            return "?"
        return " ∥ ".join(self.comandos)

    @property
    def simultaneo(self) -> bool:
        return len(self.comandos) > 1


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


Endpoint = tuple[int, Literal["origem", "destino"]]
No = tuple[int, int]
Aresta = tuple[No, No]


@dataclass
class _GeometriaCompleta:
    horizontal: list[str]
    vertical: list[str]
    codigos_coluna: list[tuple[int, ...]]
    codigos_linha: list[tuple[int, ...]]
    indice_coluna: dict[tuple[int, ...], int]
    indice_linha: dict[tuple[int, ...], int]
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
    nivel_vertical: float
    altura_cabecalho: float
    largura_cabecalho: float
    corredor: float
    altura_titulo: float
    linhas_sequencia: list[str]

    @property
    def colunas(self) -> int:
        return len(self.codigos_coluna)

    @property
    def linhas(self) -> int:
        return len(self.codigos_linha)

    @property
    def nx(self) -> int:
        return len(self.x_tracks)

    @property
    def ny(self) -> int:
        return len(self.y_tracks)

    @property
    def area_rotas(self) -> Retangulo:
        margem = 9.0
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

    def celula(
        self,
        fisico: Mapping[str, int],
        memoria: Mapping[str, int],
    ) -> tuple[int, int]:
        codigo_c = _estado_completo(fisico, memoria, self.horizontal)
        codigo_l = _estado_completo(fisico, memoria, self.vertical)
        return self.indice_coluna[codigo_c], self.indice_linha[codigo_l]

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
# Entrada e normalização
# ---------------------------------------------------------------------------


def _nome_normalizado(valor: Any) -> str:
    return str(valor).strip().upper()


def _normalizar_comando(valor: Any) -> str:
    comando = str(valor).strip().replace("−", "-").replace("–", "-")
    if len(comando) >= 2 and comando[-1] in "+-":
        return f"{comando[:-1].strip().upper()}{comando[-1]}"
    return comando.upper()


def _normalizar_estado(
    estado: Mapping[str, int | bool] | None,
    nomes: Iterable[str],
) -> dict[str, int]:
    origem = estado or {}
    chaves = {str(chave).upper(): valor for chave, valor in origem.items()}
    return {nome: int(bool(chaves.get(nome, 0))) for nome in nomes}


def _comandos_da_etapa(etapa: Mapping[str, Any]) -> tuple[str, ...]:
    comandos = etapa.get("comandos") or etapa.get("saidas")
    if comandos:
        if isinstance(comandos, str):
            comandos = comandos.replace("∥", ",").split(",")
        return tuple(
            _normalizar_comando(comando)
            for comando in comandos
            if str(comando).strip()
        )

    texto = str(etapa.get("comando_texto", "")).strip().strip("()")
    if not texto:
        return ()
    return tuple(
        _normalizar_comando(parte)
        for parte in texto.replace("∥", ",").split(",")
        if parte.strip()
    )


def _aplicar_comandos(
    estado: Mapping[str, int],
    comandos: Iterable[str],
) -> dict[str, int]:
    novo = dict(estado)
    for bruto in comandos:
        comando = _normalizar_comando(bruto)
        if len(comando) < 2 or comando[-1] not in "+-":
            continue
        novo[comando[:-1]] = 1 if comando[-1] == "+" else 0
    return novo


def _codigo_memoria(
    etapa: Mapping[str, Any],
    memorias: Sequence[str],
) -> dict[str, int]:
    return _normalizar_estado(etapa.get("codigo_memorias", {}), memorias)


def _eventos_expandidos(resultado: Mapping[str, Any]) -> list[EventoMapa]:
    """Cria a sequência completa de eventos físicos e de memória."""
    atuadores = [_nome_normalizado(nome) for nome in resultado.get("atuadores", [])]
    memorias = [_nome_normalizado(nome) for nome in resultado.get("memorias", [])]

    eventos_prontos = resultado.get("eventos_mapa")
    if eventos_prontos:
        saida: list[EventoMapa] = []

        for indice, bruto in enumerate(eventos_prontos):
            tipo_bruto = str(bruto.get("tipo", "atuador")).strip().lower()
            tipo: Literal["atuador", "memoria"] = (
                "memoria" if tipo_bruto in {"memoria", "memória", "memory"} else "atuador"
            )
            comandos = _comandos_da_etapa(bruto)
            origem_fisica = _normalizar_estado(bruto.get("estado_fisico", {}), atuadores)
            origem_memoria = _normalizar_estado(bruto.get("codigo_memorias", {}), memorias)

            if bruto.get("destino_fisico") is not None:
                destino_fisico = _normalizar_estado(bruto.get("destino_fisico"), atuadores)
            elif tipo == "atuador":
                destino_fisico = _aplicar_comandos(origem_fisica, comandos)
            else:
                destino_fisico = dict(origem_fisica)

            if bruto.get("destino_memoria") is not None:
                destino_memoria = _normalizar_estado(bruto.get("destino_memoria"), memorias)
            elif tipo == "memoria":
                destino_memoria = _aplicar_comandos(origem_memoria, comandos)
            else:
                destino_memoria = dict(origem_memoria)

            saida.append(
                EventoMapa(
                    indice=indice,
                    tipo=tipo,
                    comandos=comandos,
                    origem_fisica=origem_fisica,
                    destino_fisico=destino_fisico,
                    origem_memoria=origem_memoria,
                    destino_memoria=destino_memoria,
                )
            )
        return saida

    etapas = list(resultado.get("etapas", []))
    if not etapas:
        raise ValueError("O resultado não contém etapas nem eventos_mapa para desenhar o mapa.")

    eventos: list[EventoMapa] = []
    for indice_etapa, etapa in enumerate(etapas):
        comandos = _comandos_da_etapa(etapa)
        origem_fisica = _normalizar_estado(etapa.get("estado_antes", {}), atuadores)
        destino_fisico = _normalizar_estado(etapa.get("estado_depois", {}), atuadores)
        if not etapa.get("estado_depois"):
            destino_fisico = _aplicar_comandos(origem_fisica, comandos)
        codigo_atual = _codigo_memoria(etapa, memorias)

        eventos.append(
            EventoMapa(
                indice=len(eventos),
                tipo="atuador",
                comandos=comandos,
                origem_fisica=origem_fisica,
                destino_fisico=destino_fisico,
                origem_memoria=dict(codigo_atual),
                destino_memoria=dict(codigo_atual),
            )
        )

        if indice_etapa + 1 < len(etapas):
            proximo_codigo = _codigo_memoria(etapas[indice_etapa + 1], memorias)
        else:
            proximo_codigo = _codigo_memoria(etapas[0], memorias)

        codigo_corrente = dict(codigo_atual)
        for memoria in memorias:
            atual = codigo_corrente[memoria]
            novo = proximo_codigo[memoria]
            if atual == novo:
                continue

            comando = f"{memoria}{'+' if novo else '-'}"
            destino_codigo = dict(codigo_corrente)
            destino_codigo[memoria] = novo
            eventos.append(
                EventoMapa(
                    indice=len(eventos),
                    tipo="memoria",
                    comandos=(comando,),
                    origem_fisica=dict(destino_fisico),
                    destino_fisico=dict(destino_fisico),
                    origem_memoria=dict(codigo_corrente),
                    destino_memoria=destino_codigo,
                )
            )
            codigo_corrente = destino_codigo

    return eventos


# ---------------------------------------------------------------------------
# Ordem Gray e escolha dos eixos
# ---------------------------------------------------------------------------


def _gray(quantidade_bits: int) -> list[tuple[int, ...]]:
    if quantidade_bits == 0:
        return [()]
    return [
        tuple((valor >> deslocamento) & 1 for deslocamento in reversed(range(quantidade_bits)))
        for valor in (indice ^ (indice >> 1) for indice in range(1 << quantidade_bits))
    ]


def _runs(valores: list[int]) -> list[tuple[int, int, int]]:
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


def _estado_completo(
    fisico: Mapping[str, int],
    memoria: Mapping[str, int],
    variaveis: Sequence[str],
) -> tuple[int, ...]:
    valores = {**fisico, **memoria}
    return tuple(int(valores.get(nome, 0)) for nome in variaveis)


def _estado_endpoint(evento: EventoMapa, lado: str, variaveis: Sequence[str]) -> tuple[int, ...]:
    if lado == "origem":
        return _estado_completo(evento.origem_fisica, evento.origem_memoria, variaveis)
    return _estado_completo(evento.destino_fisico, evento.destino_memoria, variaveis)


def _distancia_ciclica(a: int, b: int, tamanho: int) -> int:
    direta = abs(a - b)
    return min(direta, tamanho - direta) if tamanho > 1 else 0


def _frequencia_mudancas(
    eventos: Sequence[EventoMapa],
    variaveis: Sequence[str],
) -> dict[str, int]:
    frequencia = {nome: 0 for nome in variaveis}
    for evento in eventos:
        origem = {**evento.origem_fisica, **evento.origem_memoria}
        destino = {**evento.destino_fisico, **evento.destino_memoria}
        for nome in variaveis:
            if int(origem.get(nome, 0)) != int(destino.get(nome, 0)):
                frequencia[nome] += 1
    return frequencia


def _avaliar_eixos(
    horizontal: tuple[str, ...],
    vertical: tuple[str, ...],
    eventos: Sequence[EventoMapa],
    memorias: set[str],
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    colunas = _gray(len(horizontal))
    linhas = _gray(len(vertical))
    idx_c = {codigo: i for i, codigo in enumerate(colunas)}
    idx_l = {codigo: i for i, codigo in enumerate(linhas)}

    custo = 0.0
    usos: dict[tuple[str, int, int, int], int] = {}
    for evento in eventos:
        c1 = idx_c[_estado_completo(evento.origem_fisica, evento.origem_memoria, horizontal)]
        c2 = idx_c[_estado_completo(evento.destino_fisico, evento.destino_memoria, horizontal)]
        l1 = idx_l[_estado_completo(evento.origem_fisica, evento.origem_memoria, vertical)]
        l2 = idx_l[_estado_completo(evento.destino_fisico, evento.destino_memoria, vertical)]

        dx = _distancia_ciclica(c1, c2, len(colunas))
        dy = _distancia_ciclica(l1, l2, len(linhas))
        distancia = dx + dy
        custo += distancia
        if dx and dy:
            custo += 1.6
        if evento.simultaneo:
            custo += 0.35 * max(0, distancia - 1)

        if l1 == l2:
            chave = ("H", l1, min(c1, c2), max(c1, c2))
            usos[chave] = usos.get(chave, 0) + 1
        elif c1 == c2:
            chave = ("V", c1, min(l1, l2), max(l1, l2))
            usos[chave] = usos.get(chave, 0) + 1

        if len(colunas) > 2 and l1 == l2 and abs(c1 - c2) == len(colunas) - 1:
            custo += 0.45
        if len(linhas) > 2 and c1 == c2 and abs(l1 - l2) == len(linhas) - 1:
            custo += 0.45

    custo += sum((quantidade - 1) ** 2 * 1.35 for quantidade in usos.values())

    # Memórias nas posições externas tornam os cabeçalhos mais legíveis.
    for eixo in (horizontal, vertical):
        for posicao, nome in enumerate(eixo):
            if nome in memorias:
                custo += posicao * 0.75

    largura = 1 << len(horizontal)
    altura = 1 << len(vertical)
    custo += abs(largura / max(altura, 1) - 1.45) * 0.32
    return custo, horizontal, vertical


def _eixos_estilo_professor(
    atuadores: Sequence[str],
    memorias: Sequence[str],
) -> tuple[list[str], list[str]]:
    """Replica a lógica visual mais comum das figuras de apostila/professor.

    Atuadores alternam entre eixo horizontal e vertical: A,C,E... ficam no
    horizontal (de fora para dentro) e B,D,F... no vertical. As memórias são
    colocadas primeiro nos anéis externos, priorizando a memória mais recente
    no topo. Ex.:
        A,B com X   -> horizontal = [X, A], vertical = [B]
        A,B,C com X,Y -> horizontal = [Y, C, A], vertical = [X, B]
        A,B,C,D com X,Y -> horizontal = [Y, C, A], vertical = [X, D, B]
    """
    atu = [_nome_normalizado(a) for a in atuadores]
    mem = [_nome_normalizado(m) for m in memorias]

    pares = atu[0::2]     # A, C, E...
    impares = atu[1::2]   # B, D, F...
    horizontal = list(reversed(pares))
    vertical = list(reversed(impares))

    if mem:
        horizontal.insert(0, mem[-1])
    if len(mem) >= 2:
        vertical.insert(0, mem[0])

    extras = mem[1:-1] if len(mem) > 2 else []
    for indice, memoria in enumerate(reversed(extras), start=1):
        if indice % 2 == 1:
            vertical.insert(0, memoria)
        else:
            horizontal.insert(0, memoria)

    if not horizontal and vertical:
        horizontal = [vertical.pop()]
    if not vertical and horizontal and len(horizontal) > 1:
        vertical = [horizontal.pop()]
    return horizontal, vertical


def _escolher_eixos(
    variaveis: list[str],
    eventos: Sequence[EventoMapa],
    memorias: set[str],
) -> tuple[list[str], list[str]]:
    quantidade = len(variaveis)
    if quantidade == 1:
        return [variaveis[0]], []

    quantidade_horizontal = ceil(quantidade / 2)
    if quantidade <= 7:
        melhor: tuple[float, tuple[str, ...], tuple[str, ...]] | None = None
        for permutacao in permutations(sorted(variaveis)):
            candidato = _avaliar_eixos(
                tuple(permutacao[:quantidade_horizontal]),
                tuple(permutacao[quantidade_horizontal:]),
                eventos,
                memorias,
            )
            if melhor is None or candidato < melhor:
                melhor = candidato
        assert melhor is not None
        return list(melhor[1]), list(melhor[2])

    frequencia = _frequencia_mudancas(eventos, variaveis)
    ordenadas = sorted(variaveis, key=lambda nome: (-frequencia[nome], nome))
    horizontal: list[str] = []
    vertical: list[str] = []
    for indice, nome in enumerate(ordenadas):
        if len(horizontal) < quantidade_horizontal and (
            len(vertical) >= quantidade - quantidade_horizontal or indice % 2 == 0
        ):
            horizontal.append(nome)
        else:
            vertical.append(nome)
    return list(reversed(horizontal)), list(reversed(vertical))


# ---------------------------------------------------------------------------
# Grupos de passagem e portas
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


def _grupos_endpoints(
    eventos: Sequence[EventoMapa],
    variaveis: Sequence[str],
) -> tuple[dict[Endpoint, Endpoint], dict[Endpoint, list[Endpoint]]]:
    endpoints: list[Endpoint] = [
        (evento.indice, lado)
        for evento in eventos
        for lado in ("origem", "destino")
    ]
    uniao = _UniaoBusca(endpoints)

    for atual, proximo in zip(eventos, eventos[1:]):
        if _estado_endpoint(atual, "destino", variaveis) == _estado_endpoint(
            proximo, "origem", variaveis
        ):
            uniao.unir((atual.indice, "destino"), (proximo.indice, "origem"))

    if eventos and _estado_endpoint(eventos[-1], "destino", variaveis) == _estado_endpoint(
        eventos[0], "origem", variaveis
    ):
        uniao.unir((eventos[-1].indice, "destino"), (eventos[0].indice, "origem"))

    raiz_por_endpoint = {endpoint: uniao.encontrar(endpoint) for endpoint in endpoints}
    membros: dict[Endpoint, list[Endpoint]] = {}
    for endpoint, raiz in raiz_por_endpoint.items():
        membros.setdefault(raiz, []).append(endpoint)
    return raiz_por_endpoint, membros


def _maximo_grupos_por_estado(
    eventos: Sequence[EventoMapa],
    variaveis: Sequence[str],
) -> int:
    _, membros = _grupos_endpoints(eventos, variaveis)
    contagem: dict[tuple[int, ...], int] = {}
    por_indice = {evento.indice: evento for evento in eventos}
    for raiz, endpoints in membros.items():
        indice, lado = endpoints[0]
        estado = _estado_endpoint(por_indice[indice], lado, variaveis)
        contagem[estado] = contagem.get(estado, 0) + 1
    return max(contagem.values(), default=1)


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
    geometria: _GeometriaCompleta,
    eventos: Sequence[EventoMapa],
    variaveis: Sequence[str],
) -> dict[Endpoint, No]:
    """Atribui uma porta única a cada visita a um estado.

    O destino de uma transição e a origem da transição seguinte compartilham
    a mesma porta quando representam exatamente o mesmo estado. Isso deixa o
    percurso cronológico visualmente contínuo.
    """
    raiz_por_endpoint, membros = _grupos_endpoints(eventos, variaveis)
    por_indice = {evento.indice: evento for evento in eventos}

    celula_raiz: dict[Endpoint, tuple[int, int]] = {}
    for raiz, endpoints in membros.items():
        indice, lado = endpoints[0]
        evento = por_indice[indice]
        if lado == "origem":
            celula = geometria.celula(evento.origem_fisica, evento.origem_memoria)
        else:
            celula = geometria.celula(evento.destino_fisico, evento.destino_memoria)
        celula_raiz[raiz] = celula

    vizinhos: dict[Endpoint, list[tuple[int, int]]] = {raiz: [] for raiz in membros}
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
        raizes.sort(key=lambda raiz: (-len(vizinhos[raiz]), min(m[0] for m in membros[raiz])))

        for raiz in raizes:
            alvos = vizinhos[raiz]
            vx = sum(
                _delta_ciclico_assinado(celula[0], alvo[0], geometria.colunas)
                for alvo in alvos
            )
            vy = sum(
                _delta_ciclico_assinado(celula[1], alvo[1], geometria.linhas)
                for alvo in alvos
            )
            if alvos:
                vx /= len(alvos)
                vy /= len(alvos)

            desejado_x = centro + vx * centro * 0.72
            desejado_y = centro + vy * centro * 0.72

            def pontuacao(slot: tuple[int, int]) -> tuple[float, float, int, int]:
                distancia = (slot[0] - desejado_x) ** 2 + (slot[1] - desejado_y) ** 2
                centroide = abs(slot[0] - centro) + abs(slot[1] - centro)
                return distancia, centroide * 0.12, slot[1], slot[0]

            escolhido = min(disponiveis, key=pontuacao)
            disponiveis.remove(escolhido)
            atribuicao_raiz[raiz] = geometria.no_da_porta(celula[0], celula[1], escolhido)

    return {
        endpoint: atribuicao_raiz[raiz]
        for endpoint, raiz in raiz_por_endpoint.items()
    }


# ---------------------------------------------------------------------------
# Geometria adaptativa
# ---------------------------------------------------------------------------


def _largura_texto(texto: str, fonte: float) -> float:
    # Aproximação conservadora para Arial/Helvetica sem depender de biblioteca gráfica.
    unidades = 0.0
    for caractere in texto:
        if caractere in " ilI1.,:;|'":
            unidades += 0.34
        elif caractere in "MW@%&∥":
            unidades += 0.95
        else:
            unidades += 0.64
    return unidades * fonte


def _quebrar_itens(
    itens: Sequence[str],
    largura_maxima: float,
    fonte: float,
    separador: str = ", ",
) -> list[str]:
    if not itens:
        return []
    linhas: list[str] = []
    atual = ""
    for item in itens:
        candidato = item if not atual else atual + separador + item
        if atual and _largura_texto(candidato, fonte) > largura_maxima:
            linhas.append(atual)
            atual = item
        else:
            atual = candidato
    if atual:
        linhas.append(atual)
    return linhas


def _construir_geometria(
    horizontal: list[str],
    vertical: list[str],
    eventos: Sequence[EventoMapa],
    incluir_titulo: bool,
    lanes: int,
    linhas_sequencia: Sequence[str] | None = None,
) -> _GeometriaCompleta:
    codigos_coluna = _gray(len(horizontal))
    codigos_linha = _gray(len(vertical))
    indice_coluna = {codigo: indice for indice, codigo in enumerate(codigos_coluna)}
    indice_linha = {codigo: indice for indice, codigo in enumerate(codigos_linha)}

    maior_rotulo = max((_largura_texto(evento.texto, 14.0) for evento in eventos), default=32.0)
    maior_variavel = max((_largura_texto(nome.lower() + "0", 15.0) for nome in horizontal + vertical), default=24.0)

    passo_x = 16.0
    passo_y = 14.0
    celula_largura = max(56.0, 24.0 + lanes * passo_x, min(maior_rotulo + 18.0, 122.0))
    celula_altura = max(38.0, 18.0 + lanes * passo_y)

    margem = 28.0
    nivel_vertical = max(34.0, maior_variavel + 10.0)
    nivel_horizontal = 23.0
    altura_cabecalho = max(54.0, len(horizontal) * nivel_horizontal + 10.0)
    largura_cabecalho = max(54.0, max(1, len(vertical)) * nivel_vertical)

    # Corredores externos são dimensionados pela quantidade de transições
    # que realmente precisam contornar a borda cíclica do código Gray. Isso
    # mantém mapas simples compactos sem retirar espaço dos casos difíceis.
    wraps_h = 0
    wraps_v = 0
    for evento in eventos:
        origem_c = indice_coluna[_estado_completo(evento.origem_fisica, evento.origem_memoria, horizontal)]
        destino_c = indice_coluna[_estado_completo(evento.destino_fisico, evento.destino_memoria, horizontal)]
        origem_l = indice_linha[_estado_completo(evento.origem_fisica, evento.origem_memoria, vertical)]
        destino_l = indice_linha[_estado_completo(evento.destino_fisico, evento.destino_memoria, vertical)]
        if len(codigos_coluna) > 2 and origem_l == destino_l and abs(origem_c - destino_c) == len(codigos_coluna) - 1:
            wraps_h += 1
        if len(codigos_linha) > 2 and origem_c == destino_c and abs(origem_l - destino_l) == len(codigos_linha) - 1:
            wraps_v += 1

    necessidade_wrap = max(wraps_h, wraps_v)
    frame_lanes = max(2, min(7, ceil(necessidade_wrap / 2) + 1))
    corredor = frame_lanes * 18.0 + 8.0

    linhas = list(linhas_sequencia or [])
    if incluir_titulo:
        altura_titulo = 66.0 + max(1, len(linhas)) * 18.0 + 8.0
    else:
        altura_titulo = 24.0

    grade_x = margem + largura_cabecalho + corredor
    grade_y = altura_titulo + altura_cabecalho + corredor
    grade_largura = len(codigos_coluna) * celula_largura
    grade_altura = len(codigos_linha) * celula_altura

    largura = int(ceil(grade_x + grade_largura + corredor + margem))
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
    for coluna in range(len(codigos_coluna)):
        x0 = grade_x + coluna * celula_largura
        for lane in range(lanes):
            internos_x.append(x0 + (lane + 1) * celula_largura / (lanes + 1))

    internos_y: list[float] = []
    for linha in range(len(codigos_linha)):
        y0 = grade_y + linha * celula_altura
        for lane in range(lanes):
            internos_y.append(y0 + (lane + 1) * celula_altura / (lanes + 1))

    return _GeometriaCompleta(
        horizontal=horizontal,
        vertical=vertical,
        codigos_coluna=codigos_coluna,
        codigos_linha=codigos_linha,
        indice_coluna=indice_coluna,
        indice_linha=indice_linha,
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
        nivel_vertical=nivel_vertical,
        altura_cabecalho=altura_cabecalho,
        largura_cabecalho=largura_cabecalho,
        corredor=corredor,
        altura_titulo=altura_titulo,
        linhas_sequencia=linhas,
    )


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
    geometria: _GeometriaCompleta,
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
    anterior: dict[tuple[No, str | None], tuple[No, str | None] | None] = {
        (inicio, None): None
    }
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
                penalidade_no = 80.0
            else:
                penalidade_no = 0.0

            x1, y1 = geometria.coordenada_no(no)
            x2, y2 = geometria.coordenada_no(vizinho)
            comprimento = abs(x2 - x1) + abs(y2 - y1)
            curva = 0.0 if direcao_anterior in (None, direcao) else 17.0

            desvio = 0.0
            if not (min_x <= vizinho[0] <= max_x):
                desvio += 2.0
            if not (min_y <= vizinho[1] <= max_y):
                desvio += 2.0

            novo_custo = custo_atual + comprimento + curva + penalidade_no + desvio
            heuristica = (
                abs(geometria.x_tracks[vizinho[0]] - geometria.x_tracks[fim[0]])
                + abs(geometria.y_tracks[vizinho[1]] - geometria.y_tracks[fim[1]])
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
    geometria: _GeometriaCompleta,
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
    geometria: _GeometriaCompleta,
    evento: EventoMapa,
    inicio: No,
    fim: No,
) -> list[list[No]]:
    origem = geometria.celula(evento.origem_fisica, evento.origem_memoria)
    destino = geometria.celula(evento.destino_fisico, evento.destino_memoria)
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
            range(geometria.ny - 1, geometria.ny - geometria.frame_lanes - 1, -1)
        )
        indices_y.sort(
            key=lambda iy: abs(geometria.y_tracks[iy] - geometria.y_tracks[inicio[1]])
        )
        for iy in indices_y:
            candidatos.append([inicio, (inicio[0], iy), (fim[0], iy), fim])

    if wrap_v:
        indices_x = list(range(geometria.frame_lanes)) + list(
            range(geometria.nx - 1, geometria.nx - geometria.frame_lanes - 1, -1)
        )
        indices_x.sort(
            key=lambda ix: abs(geometria.x_tracks[ix] - geometria.x_tracks[inicio[0]])
        )
        for ix in indices_x:
            candidatos.append([inicio, (ix, inicio[1]), (ix, fim[1]), fim])

    return candidatos


def _rotear_laco(
    geometria: _GeometriaCompleta,
    inicio: No,
    nos_ocupados: set[No],
    arestas_ocupadas: set[Aresta],
) -> list[No] | None:
    for alcance in (1, 2, 3):
        for dx, dy in ((alcance, alcance), (-alcance, alcance), (alcance, -alcance), (-alcance, -alcance)):
            p1 = (inicio[0] + dx, inicio[1])
            p2 = (inicio[0] + dx, inicio[1] + dy)
            p3 = (inicio[0], inicio[1] + dy)
            caminho = [inicio, p1, p2, p3, inicio]
            if any(not (0 <= x < geometria.nx and 0 <= y < geometria.ny) for x, y in caminho):
                continue
            internos = set(caminho[1:-1])
            if internos & nos_ocupados:
                continue
            edges = {_aresta(a, b) for a, b in zip(caminho, caminho[1:])}
            if edges & arestas_ocupadas:
                continue
            return caminho
    return None


def _simplificar_pontos(pontos: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(pontos) <= 2:
        return pontos
    saida = [pontos[0]]
    for indice in range(1, len(pontos) - 1):
        anterior = saida[-1]
        atual = pontos[indice]
        proximo = pontos[indice + 1]
        vertical = abs(anterior[0] - atual[0]) < 1e-9 and abs(atual[0] - proximo[0]) < 1e-9
        horizontal = abs(anterior[1] - atual[1]) < 1e-9 and abs(atual[1] - proximo[1]) < 1e-9
        if not (vertical or horizontal):
            saida.append(atual)
    saida.append(pontos[-1])
    return saida


def _rotear_em_ordem(
    geometria: _GeometriaCompleta,
    eventos: Sequence[EventoMapa],
    portas: Mapping[Endpoint, No],
    ordem: Sequence[EventoMapa],
    *,
    permitir_cruzamentos: bool,
) -> list[Rota] | None:
    # Todas as portas são obstáculos, exceto quando são início/fim da rota atual.
    nos_ocupados: set[No] = set(portas.values())
    arestas_ocupadas: set[Aresta] = set()
    rotas: dict[int, Rota] = {}

    for evento in ordem:
        inicio = portas[(evento.indice, "origem")]
        fim = portas[(evento.indice, "destino")]

        if inicio == fim:
            caminho = _rotear_laco(geometria, inicio, nos_ocupados, arestas_ocupadas)
        else:
            caminho = None
            for waypoints in _candidatos_wrap(geometria, evento, inicio, fim):
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
        rotas[evento.indice] = Rota(evento=evento, pontos=_simplificar_pontos(pontos))

    return [rotas[evento.indice] for evento in eventos]


def _rotear_eventos(
    geometria: _GeometriaCompleta,
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
# Rótulos e detecção de colisões
# ---------------------------------------------------------------------------


def _segmentos(pontos: Sequence[tuple[float, float]]) -> list[tuple[float, float, float, float]]:
    return [(a[0], a[1], b[0], b[1]) for a, b in zip(pontos, pontos[1:])]


def _comprimento_segmento(segmento: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = segmento
    return abs(x2 - x1) + abs(y2 - y1)


def _caixa_texto(
    texto: str,
    centro_x: float,
    centro_y: float,
    fonte: float = 14.0,
    padding_x: float = 8.0,
    padding_y: float = 5.0,
) -> Retangulo:
    largura = max(24.0, _largura_texto(texto, fonte) + 2 * padding_x)
    altura = fonte + 2 * padding_y
    return Retangulo(centro_x - largura / 2, centro_y - altura / 2, largura, altura)


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


def _candidatos_rotulo(rota: Rota, texto: str, fonte: float = 14.0) -> list[Retangulo]:
    candidatos: list[tuple[float, Retangulo]] = []
    largura = _caixa_texto(texto, 0, 0, fonte).largura
    altura = _caixa_texto(texto, 0, 0, fonte).altura

    segmentos = sorted(_segmentos(rota.pontos), key=_comprimento_segmento, reverse=True)
    for ordem_segmento, segmento in enumerate(segmentos):
        x1, y1, x2, y2 = segmento
        comprimento = _comprimento_segmento(segmento)
        if comprimento < 18:
            continue

        for fracao in (0.50, 0.34, 0.66, 0.20, 0.80):
            x = x1 + (x2 - x1) * fracao
            y = y1 + (y2 - y1) * fracao

            # Primeira opção: rótulo centralizado na própria linha. O fundo
            # branco abre uma interrupção limpa no traço.
            requisito = largura + 20 if abs(y1 - y2) < 1e-9 else altura + 20
            if comprimento >= requisito:
                caixa = _caixa_texto(texto, x, y, fonte)
                candidatos.append((ordem_segmento * 10 + abs(fracao - 0.5), caixa))

            if abs(y1 - y2) < 1e-9:
                deslocamento = altura / 2 + 9
                for sinal in (-1, 1):
                    caixa = _caixa_texto(texto, x, y + sinal * deslocamento, fonte)
                    candidatos.append((5 + ordem_segmento * 10 + abs(fracao - 0.5), caixa))
            else:
                deslocamento = largura / 2 + 11
                for sinal in (1, -1):
                    caixa = _caixa_texto(texto, x + sinal * deslocamento, y, fonte)
                    candidatos.append((5 + ordem_segmento * 10 + abs(fracao - 0.5), caixa))

    candidatos.sort(key=lambda item: item[0])
    return [caixa for _, caixa in candidatos]


def _posicionar_rotulos(
    rotas: list[Rota],
    geometria: _GeometriaCompleta,
    portas: Mapping[Endpoint, No],
) -> list[tuple[int, str]]:
    caixas_usadas: list[Retangulo] = []
    legenda: list[tuple[int, str]] = []
    segmentos_por_rota = {rota.evento.indice: _segmentos(rota.pontos) for rota in rotas}
    todos_segmentos = [
        (rota.evento.indice, segmento)
        for rota in rotas
        for segmento in segmentos_por_rota[rota.evento.indice]
    ]
    area = geometria.area_rotas
    caixas_portas = [
        Retangulo(x - 8, y - 8, 16, 16)
        for x, y in (geometria.coordenada_no(no) for no in set(portas.values()))
    ]

    def valida(caixa: Retangulo, rota: Rota) -> bool:
        if not area.contem(caixa, margem=2.0):
            return False
        if any(caixa.expandido(4).cruza(outra) for outra in caixas_usadas):
            return False
        if any(caixa.expandido(2).cruza(porta) for porta in caixas_portas):
            return False
        for indice_rota, segmento in todos_segmentos:
            if indice_rota == rota.evento.indice:
                continue
            if _retangulo_cruza_segmento(caixa, segmento, margem=4.0):
                return False
        return True

    for rota in rotas:
        texto = rota.evento.texto
        escolhida: Retangulo | None = None

        for caixa in _candidatos_rotulo(rota, texto, fonte=14.0):
            if valida(caixa, rota):
                escolhida = caixa
                rota.rotulo = texto
                break

        if escolhida is None:
            numero = len(legenda) + 1
            curto = str(numero)
            for caixa in _candidatos_rotulo(rota, curto, fonte=12.0):
                if valida(caixa, rota):
                    escolhida = caixa
                    rota.rotulo = curto
                    rota.usa_numero = True
                    legenda.append((numero, texto))
                    break

        if escolhida is None:
            # Busca radial de último recurso ao redor do maior segmento.
            numero = len(legenda) + 1
            segmento = max(segmentos_por_rota[rota.evento.indice], key=_comprimento_segmento)
            x1, y1, x2, y2 = segmento
            centro_x = (x1 + x2) / 2
            centro_y = (y1 + y2) / 2
            for raio in range(0, 181, 12):
                offsets = ((0, -raio), (raio, 0), (0, raio), (-raio, 0))
                for dx, dy in offsets:
                    caixa = _caixa_texto(str(numero), centro_x + dx, centro_y + dy, 12.0)
                    if valida(caixa, rota):
                        escolhida = caixa
                        break
                if escolhida is not None:
                    break

            if escolhida is None:
                # Como a área de rotas possui corredores externos exclusivos,
                # esta posição quase nunca é necessária. Ainda assim, mantém
                # o SVG válido e transfere a leitura completa para a legenda.
                escolhida = _caixa_texto(str(numero), centro_x, centro_y, 12.0)

            rota.rotulo = str(numero)
            rota.usa_numero = True
            legenda.append((numero, texto))

        rota.caixa_rotulo = escolhida
        caixas_usadas.append(escolhida)

    return legenda


# ---------------------------------------------------------------------------
# Elementos SVG do mapa completo
# ---------------------------------------------------------------------------


def _cabecalhos_completos(geometria: _GeometriaCompleta, corpo: list[str]) -> None:
    horizontal = geometria.horizontal
    vertical = geometria.vertical
    y_base = geometria.fim_cabecalho_y
    x_base = geometria.fim_cabecalho_x

    if horizontal:
        for profundidade, variavel in enumerate(horizontal[:-1]):
            valores = [codigo[profundidade] for codigo in geometria.codigos_coluna]
            y = y_base - 34 - (len(horizontal) - 2 - profundidade) * 33
            for inicio, fim, valor in _runs(valores):
                x1 = geometria.grade_x + inicio * geometria.celula_largura + 8
                x2 = geometria.grade_x + (fim + 1) * geometria.celula_largura - 8
                centro = (x1 + x2) / 2
                corpo.append(
                    f'<path d="M{x1:.2f},{y + 12:.2f} V{y + 2:.2f} H{x2:.2f} V{y + 12:.2f}" '
                    f'fill="none" stroke="{GRADE}" stroke-width="1.0"/>'
                )
                corpo.append(
                    f'<text x="{centro:.2f}" y="{y - 4:.2f}" text-anchor="middle" '
                    f'font-family="{FONTE}" font-size="12" font-weight="700" fill="{TEXTO}">'
                    f'{escape(variavel.lower())}{valor}</text>'
                )

        interna = horizontal[-1]
        for coluna, codigo in enumerate(geometria.codigos_coluna):
            x = geometria.grade_x + (coluna + 0.5) * geometria.celula_largura
            corpo.append(
                f'<text x="{x:.2f}" y="{y_base - 9:.2f}" text-anchor="middle" '
                f'font-family="{FONTE}" font-size="12" font-weight="700" fill="{TEXTO}">'
                f'{escape(interna.lower())}{codigo[-1]}</text>'
            )

    if vertical:
        for profundidade, variavel in enumerate(vertical[:-1]):
            valores = [codigo[profundidade] for codigo in geometria.codigos_linha]
            x1 = geometria.margem + profundidade * geometria.nivel_vertical
            for inicio, fim, valor in _runs(valores):
                y1 = geometria.grade_y + inicio * geometria.celula_altura
                y2 = geometria.grade_y + (fim + 1) * geometria.celula_altura
                corpo.append(
                    f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{geometria.nivel_vertical:.2f}" '
                    f'height="{y2 - y1:.2f}" fill="none" stroke="{GRADE}" stroke-width="1.0"/>'
                )
                corpo.append(
                    f'<text x="{x1 + geometria.nivel_vertical / 2:.2f}" y="{(y1 + y2) / 2 + 5:.2f}" '
                    f'text-anchor="middle" font-family="{FONTE}" font-size="12" font-weight="700" '
                    f'fill="{TEXTO}">{escape(variavel.lower())}{valor}</text>'
                )

        interna = vertical[-1]
        x_interno = x_base - geometria.nivel_vertical
        for linha, codigo in enumerate(geometria.codigos_linha):
            y = geometria.grade_y + linha * geometria.celula_altura
            corpo.append(
                f'<rect x="{x_interno:.2f}" y="{y:.2f}" width="{geometria.nivel_vertical:.2f}" '
                f'height="{geometria.celula_altura:.2f}" fill="none" stroke="{GRADE}" stroke-width="1.0"/>'
            )
            corpo.append(
                f'<text x="{x_interno + geometria.nivel_vertical / 2:.2f}" '
                f'y="{y + geometria.celula_altura / 2 + 5:.2f}" text-anchor="middle" '
                f'font-family="{FONTE}" font-size="12" font-weight="700" fill="{TEXTO}">'
                f'{escape(interna.lower())}{codigo[-1]}</text>'
            )

    canto = min(54.0, geometria.nivel_vertical)
    canto_x = x_base - canto
    canto_y = y_base - canto
    corpo.append(
        f'<rect x="{canto_x:.2f}" y="{canto_y:.2f}" width="{canto:.2f}" height="{canto:.2f}" '
        f'fill="{FUNDO}" stroke="{GRADE}" stroke-width="0.9"/>'
    )
    corpo.append(
        f'<path d="M{canto_x:.2f},{canto_y:.2f} L{canto_x + canto:.2f},{canto_y + canto:.2f}" '
        f'stroke="{GRADE}" stroke-width="0.9"/>'
    )
    corpo.append(
        f'<text x="{canto_x + canto - 9:.2f}" y="{canto_y + 20:.2f}" text-anchor="end" '
        f'font-family="{FONTE}" font-size="12" font-weight="700" fill="{TEXTO}">S</text>'
    )


def _grade_completa(geometria: _GeometriaCompleta, corpo: list[str]) -> None:
    for coluna in range(geometria.colunas + 1):
        x = geometria.grade_x + coluna * geometria.celula_largura
        corpo.append(
            f'<line x1="{x:.2f}" y1="{geometria.grade_y:.2f}" x2="{x:.2f}" '
            f'y2="{geometria.grade_y + geometria.grade_altura:.2f}" '
            f'stroke="{GRADE}" stroke-width="0.75"/>'
        )
    for linha in range(geometria.linhas + 1):
        y = geometria.grade_y + linha * geometria.celula_altura
        corpo.append(
            f'<line x1="{geometria.grade_x:.2f}" y1="{y:.2f}" '
            f'x2="{geometria.grade_x + geometria.grade_largura:.2f}" y2="{y:.2f}" '
            f'stroke="{GRADE}" stroke-width="0.75"/>'
        )


def _path_svg(pontos: Sequence[tuple[float, float]]) -> str:
    if not pontos:
        return ""
    partes = [f"M{pontos[0][0]:.2f},{pontos[0][1]:.2f}"]
    partes.extend(f"L{x:.2f},{y:.2f}" for x, y in pontos[1:])
    return " ".join(partes)


def _cor_evento(evento: EventoMapa) -> str:
    if evento.tipo == "memoria":
        return SETA_MEMORIA
    if evento.simultaneo:
        return SETA_SIMULTANEA
    return SETA_ATUADOR


def _renderizar_mapa_completo(
    resultado: Mapping[str, Any],
    eventos: list[EventoMapa],
    atuadores: list[str],
    memorias: list[str],
    *,
    incluir_titulo: bool,
) -> MapaSVG:
    variaveis = atuadores + memorias
    horizontal, vertical = _eixos_estilo_professor(atuadores, memorias)

    max_grupos = _maximo_grupos_por_estado(eventos, variaveis)
    lanes_inicial = max(3, ceil(sqrt(max_grupos)) + 2)
    lanes_final = max(lanes_inicial, min(14, lanes_inicial + 6))

    geometria: _GeometriaCompleta | None = None
    rotas: list[Rota] | None = None
    portas: dict[Endpoint, No] | None = None

    for lanes in range(lanes_inicial, lanes_final + 1):
        geometria_provisoria = _construir_geometria(
            horizontal,
            vertical,
            eventos,
            incluir_titulo,
            lanes,
            [],
        )
        itens_titulo = [evento.texto for evento in eventos if evento.tipo == "atuador"]
        linhas_titulo = _quebrar_itens(
            itens_titulo,
            geometria_provisoria.largura - 90,
            16.0,
        )
        geometria_teste = _construir_geometria(
            horizontal,
            vertical,
            eventos,
            incluir_titulo,
            lanes,
            linhas_titulo,
        )

        try:
            portas_teste = _atribuir_portas(geometria_teste, eventos, variaveis)
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
        # Última tentativa: permite apenas cruzamentos pontuais. As arestas
        # continuam exclusivas, portanto nenhuma linha fica desenhada sobre outra.
        lanes = min(16, max(lanes_final + 1, lanes_inicial + 3))
        geometria_provisoria = _construir_geometria(
            horizontal, vertical, eventos, incluir_titulo, lanes, []
        )
        linhas_titulo = _quebrar_itens(
            [evento.texto for evento in eventos if evento.tipo == "atuador"],
            geometria_provisoria.largura - 90,
            16.0,
        )
        geometria = _construir_geometria(
            horizontal, vertical, eventos, incluir_titulo, lanes, linhas_titulo
        )
        portas = _atribuir_portas(geometria, eventos, variaveis)
        rotas = _rotear_eventos(
            geometria,
            eventos,
            portas,
            permitir_cruzamentos=True,
        )
        if rotas is None:
            raise RuntimeError(
                "Não foi possível organizar todas as transições do mapa completo "
                "sem comprometer a leitura."
            )

    legenda = _posicionar_rotulos(rotas, geometria, portas)

    largura_disponivel = geometria.largura - 2 * geometria.margem

    # Legenda visual fixa: sempre explica linhas, memórias e marcadores.
    if largura_disponivel >= 860:
        colunas_legenda_visual = 4
    elif largura_disponivel >= 470:
        colunas_legenda_visual = 2
    else:
        colunas_legenda_visual = 1
    linhas_legenda_visual = ceil(4 / colunas_legenda_visual)
    altura_legenda_visual = 42 + linhas_legenda_visual * 29

    # Legenda numérica só aparece quando algum rótulo precisou ser abreviado.
    if legenda:
        maior_item = max(_largura_texto(f"{n}. {t}", 12.0) for n, t in legenda) + 24
        colunas_legenda = max(1, min(4, int(largura_disponivel // max(190.0, maior_item))))
        linhas_legenda = ceil(len(legenda) / colunas_legenda)
        altura_legenda_rotulos = 34 + linhas_legenda * 26
    else:
        colunas_legenda = 1
        altura_legenda_rotulos = 0

    altura = geometria.altura_base + altura_legenda_visual + altura_legenda_rotulos
    corpo: list[str] = []

    if incluir_titulo:
        corpo.append(
            f'<text x="{geometria.largura / 2:.2f}" y="38" text-anchor="middle" '
            f'font-family="{FONTE}" font-size="26" font-weight="700" fill="{TEXTO}">'
            f'Mapa de Karnaugh Estendido</text>'
        )
        y = 72.0
        for indice_linha, linha in enumerate(geometria.linhas_sequencia):
            prefixo = "Sequência: " if indice_linha == 0 else ""
            corpo.append(
                f'<text x="{geometria.largura / 2:.2f}" y="{y:.2f}" text-anchor="middle" '
                f'font-family="{FONTE}" font-size="14" font-weight="700" fill="{TEXTO}">'
                f'{escape(prefixo + linha)}</text>'
            )
            y += 22.0

    _cabecalhos_completos(geometria, corpo)
    _grade_completa(geometria, corpo)

    primeiro = eventos[0]
    inicio_no = portas[(primeiro.indice, "origem")]
    inicio_x, inicio_y = geometria.coordenada_no(inicio_no)
    canto = min(54.0, geometria.nivel_vertical)
    canto_x = geometria.fim_cabecalho_x - canto
    canto_y = geometria.fim_cabecalho_y - canto
    corpo.append(
        f'<path d="M{canto_x + 10:.2f},{canto_y + 10:.2f} '
        f'L{inicio_x - 12:.2f},{inicio_y - 8:.2f}" fill="none" '
        f'stroke="{SETA_ATUADOR}" stroke-width="1.4" marker-end="url(#arrow-act)"/>'
    )

    # Halo e linha são separados para tornar cruzamentos residuais inequívocos.
    for rota in rotas:
        corpo.append(
            f'<path d="{_path_svg(rota.pontos)}" fill="none" stroke="{FUNDO}" '
            f'stroke-width="4.4" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    for rota in rotas:
        cor = _cor_evento(rota.evento)
        tracejado = ' stroke-dasharray="7 5"' if rota.evento.tipo == "memoria" else ""
        marcador = "arrow-mem" if rota.evento.tipo == "memoria" else "arrow-act"
        corpo.append(
            f'<path d="{_path_svg(rota.pontos)}" fill="none" stroke="{cor}" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"'
            f'{tracejado} marker-end="url(#{marcador})"/>'
        )

    for rota in rotas:
        if rota.caixa_rotulo is None:
            continue
        caixa = rota.caixa_rotulo
        cor = _cor_evento(rota.evento)
        cx = caixa.x + caixa.largura / 2
        cy = caixa.y + caixa.altura / 2 + (4.0 if rota.usa_numero else 4.5)
        if rota.usa_numero:
            raio = min(9.0, caixa.altura / 2)
            corpo.append(
                f'<circle cx="{cx:.2f}" cy="{caixa.y + caixa.altura / 2:.2f}" r="{raio:.2f}" '
                f'fill="{FUNDO}" stroke="{cor}" stroke-width="0.8"/>'
            )
            corpo.append(
                f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" font-family="{FONTE}" '
                f'font-size="11" font-weight="700" fill="{TEXTO}">{escape(rota.rotulo)}</text>'
            )
        else:
            corpo.append(
                f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" font-family="{FONTE}" '
                f'font-size="12" font-weight="700" fill="{TEXTO}" '
                f'stroke="{FUNDO}" stroke-width="3.4" paint-order="stroke fill" stroke-linejoin="round">'
                f'{escape(rota.rotulo)}</text>'
            )

    ultimo = eventos[-1]
    final_no = portas[(ultimo.indice, "destino")]
    final_x, final_y = geometria.coordenada_no(final_no)
    mesmo = abs(final_x - inicio_x) < 0.1 and abs(final_y - inicio_y) < 0.1
    if mesmo:
        corpo.append(
            f'<circle cx="{inicio_x:.2f}" cy="{inicio_y:.2f}" r="9" fill="{FUNDO}" '
            f'stroke="{FINAL}" stroke-width="2.2"/>'
        )
        corpo.append(
            f'<circle cx="{inicio_x:.2f}" cy="{inicio_y:.2f}" r="4.5" fill="{INICIAL}"/>'
        )
    else:
        corpo.append(
            f'<circle cx="{inicio_x:.2f}" cy="{inicio_y:.2f}" r="5" fill="{INICIAL}"/>'
        )
        corpo.append(
            f'<circle cx="{final_x:.2f}" cy="{final_y:.2f}" r="7" fill="{FUNDO}" '
            f'stroke="{FINAL}" stroke-width="2.2"/>'
        )

    # Legenda visual fixa.
    base_legenda = geometria.altura_base
    corpo.append(
        f'<line x1="{geometria.margem:.2f}" y1="{base_legenda + 3:.2f}" '
        f'x2="{geometria.largura - geometria.margem:.2f}" y2="{base_legenda + 3:.2f}" '
        f'stroke="{GRADE_SUAVE}" stroke-width="1"/>'
    )
    corpo.append(
        f'<text x="{geometria.margem:.2f}" y="{base_legenda + 23:.2f}" '
        f'font-family="{FONTE}" font-size="12" font-weight="700" fill="{TEXTO}">Legenda</text>'
    )

    itens_visuais = (
        ("atuador", "Movimento de atuador"),
        ("memoria", "Mudança de memória interna"),
        ("inicial", "Estado inicial"),
        ("final", "Estado final"),
    )
    largura_item = largura_disponivel / colunas_legenda_visual
    for indice, (tipo_item, texto_item) in enumerate(itens_visuais):
        linha_item = indice // colunas_legenda_visual
        coluna_item = indice % colunas_legenda_visual
        x_item = geometria.margem + coluna_item * largura_item + 4
        y_item = base_legenda + 47 + linha_item * 29
        x_simbolo = x_item + 18
        x_texto = x_item + 48

        if tipo_item == "atuador":
            corpo.append(
                f'<line x1="{x_simbolo - 14:.2f}" y1="{y_item - 4:.2f}" '
                f'x2="{x_simbolo + 14:.2f}" y2="{y_item - 4:.2f}" '
                f'stroke="{SETA_ATUADOR}" stroke-width="1.75" marker-end="url(#arrow-act)"/>'
            )
        elif tipo_item == "memoria":
            corpo.append(
                f'<line x1="{x_simbolo - 14:.2f}" y1="{y_item - 4:.2f}" '
                f'x2="{x_simbolo + 14:.2f}" y2="{y_item - 4:.2f}" '
                f'stroke="{SETA_MEMORIA}" stroke-width="1.75" stroke-dasharray="7 5" '
                f'marker-end="url(#arrow-mem)"/>'
            )
        elif tipo_item == "inicial":
            corpo.append(
                f'<circle cx="{x_simbolo:.2f}" cy="{y_item - 4:.2f}" r="5" fill="{INICIAL}"/>'
            )
        else:
            corpo.append(
                f'<circle cx="{x_simbolo:.2f}" cy="{y_item - 4:.2f}" r="7" '
                f'fill="{FUNDO}" stroke="{FINAL}" stroke-width="2"/>'
            )

        corpo.append(
            f'<text x="{x_texto:.2f}" y="{y_item:.2f}" font-family="{FONTE}" '
            f'font-size="11.5" fill="{TEXTO}">{escape(texto_item)}</text>'
        )

    if legenda:
        base_rotulos = geometria.altura_base + altura_legenda_visual
        corpo.append(
            f'<line x1="{geometria.margem:.2f}" y1="{base_rotulos + 2:.2f}" '
            f'x2="{geometria.largura - geometria.margem:.2f}" y2="{base_rotulos + 2:.2f}" '
            f'stroke="{GRADE_SUAVE}" stroke-width="1"/>'
        )
        corpo.append(
            f'<text x="{geometria.margem:.2f}" y="{base_rotulos + 22:.2f}" '
            f'font-family="{FONTE}" font-size="12" font-weight="700" fill="{TEXTO}">'
            f'Rótulos numerados</text>'
        )
        largura_coluna = largura_disponivel / colunas_legenda
        for indice, (numero, texto) in enumerate(legenda):
            linha = indice // colunas_legenda
            coluna = indice % colunas_legenda
            x = geometria.margem + coluna * largura_coluna
            y = base_rotulos + 46 + linha * 26
            corpo.append(
                f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FONTE}" font-size="12" '
                f'fill="{TEXTO}"><tspan font-weight="700">{numero}.</tspan> '
                f'{escape(texto)}</text>'
            )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {geometria.largura} {altura}" '
        f'width="{geometria.largura}" height="{altura}" role="img" '
        f'aria-label="Mapa de Karnaugh Estendido">'
        f'<defs>'
        f'<marker id="arrow-act" markerWidth="6" markerHeight="6" refX="5.3" refY="3" '
        f'orient="auto" markerUnits="strokeWidth"><path d="M0,0 L6,3 L0,6 z" fill="{SETA_ATUADOR}"/></marker>'
        f'<marker id="arrow-mem" markerWidth="6" markerHeight="6" refX="5.3" refY="3" '
        f'orient="auto" markerUnits="strokeWidth"><path d="M0,0 L6,3 L0,6 z" fill="{SETA_MEMORIA}"/></marker>'
        f'</defs><rect width="{geometria.largura}" height="{altura}" fill="{FUNDO}"/>'
        + "".join(corpo)
        + "</svg>"
    )
    return MapaSVG(svg=svg, largura=geometria.largura, altura=altura)


# ---------------------------------------------------------------------------
# Vista escalável dos estados alcançáveis
# ---------------------------------------------------------------------------


def _texto_estado(
    fisico: Mapping[str, int],
    memoria: Mapping[str, int],
    atuadores: Sequence[str],
    memorias: Sequence[str],
) -> tuple[str, str]:
    linha_fisica = "  ".join(f"{nome.lower()}{int(fisico.get(nome, 0))}" for nome in atuadores)
    linha_memoria = "  ".join(f"{nome.lower()}{int(memoria.get(nome, 0))}" for nome in memorias)
    return linha_fisica or "—", linha_memoria


def _renderizar_estados_alcancaveis(
    eventos: list[EventoMapa],
    atuadores: list[str],
    memorias: list[str],
    *,
    incluir_titulo: bool,
) -> MapaSVG:
    """Representação cronológica em serpentina, sem cruzamentos."""
    estados: list[tuple[dict[str, int], dict[str, int]]] = [
        (dict(eventos[0].origem_fisica), dict(eventos[0].origem_memoria))
    ]
    estados.extend(
        (dict(evento.destino_fisico), dict(evento.destino_memoria))
        for evento in eventos
    )

    textos = [_texto_estado(f, m, atuadores, memorias) for f, m in estados]
    largura_texto = max(
        max(_largura_texto(fisico, 13), _largura_texto(memoria, 12))
        for fisico, memoria in textos
    )
    largura_no = max(170.0, largura_texto + 34.0)
    altura_no = 72.0 if memorias else 54.0
    gap_x = 104.0
    gap_y = 122.0
    margem = 44.0
    largura_alvo = 1780.0

    max_colunas = max(1, int((largura_alvo - 2 * margem + gap_x) // (largura_no + gap_x)))
    colunas = max(1, min(7, max_colunas, len(estados)))
    linhas = ceil(len(estados) / colunas)

    largura_conteudo = colunas * largura_no + max(0, colunas - 1) * gap_x
    itens_titulo = [evento.texto for evento in eventos if evento.tipo == "atuador"]
    linhas_titulo = _quebrar_itens(itens_titulo, max(largura_conteudo, 500) - 60, 16.0)
    topo = 116.0 + max(0, len(linhas_titulo) - 1) * 22.0 if incluir_titulo else 34.0

    largura = int(ceil(2 * margem + largura_conteudo))
    altura = int(ceil(topo + linhas * altura_no + max(0, linhas - 1) * gap_y + 54))

    centros: list[tuple[float, float]] = []
    for indice in range(len(estados)):
        linha = indice // colunas
        posicao = indice % colunas
        coluna_visual = posicao if linha % 2 == 0 else colunas - 1 - posicao
        x = margem + largura_no / 2 + coluna_visual * (largura_no + gap_x)
        y = topo + altura_no / 2 + linha * (altura_no + gap_y)
        centros.append((x, y))

    corpo: list[str] = []
    if incluir_titulo:
        corpo.append(
            f'<text x="{largura / 2:.2f}" y="38" text-anchor="middle" font-family="{FONTE}" '
            f'font-size="26" font-weight="700" fill="{TEXTO}">Mapa dos estados alcançáveis</text>'
        )
        y = 72.0
        for linha in linhas_titulo:
            corpo.append(
                f'<text x="{largura / 2:.2f}" y="{y:.2f}" text-anchor="middle" '
                f'font-family="{FONTE}" font-size="14" font-weight="700" fill="{TEXTO}">'
                f'{escape(linha)}</text>'
            )
            y += 22.0

    # Setas antes dos cartões.
    for indice, evento in enumerate(eventos):
        x1, y1 = centros[indice]
        x2, y2 = centros[indice + 1]
        if abs(y1 - y2) < 1e-9:
            sinal = 1 if x2 > x1 else -1
            inicio_x = x1 + sinal * largura_no / 2
            fim_x = x2 - sinal * largura_no / 2
            caminho = f"M{inicio_x:.2f},{y1:.2f} H{fim_x:.2f}"
            label_x = (inicio_x + fim_x) / 2
            label_y = y1 - altura_no / 2 - 18
        else:
            # A serpentina garante que a troca de linha ocorre na mesma coluna.
            sinal = 1 if y2 > y1 else -1
            inicio_y = y1 + sinal * altura_no / 2
            fim_y = y2 - sinal * altura_no / 2
            caminho = f"M{x1:.2f},{inicio_y:.2f} V{fim_y:.2f}"
            largura_rotulo = _caixa_texto(evento.texto, 0, 0, 13.0).largura
            lado = -1 if x1 > largura / 2 else 1
            label_x = x1 + lado * (largura_no / 2 + largura_rotulo / 2 + 12)
            label_y = (inicio_y + fim_y) / 2

        cor = _cor_evento(evento)
        tracejado = ' stroke-dasharray="7 5"' if evento.tipo == "memoria" else ""
        marcador = "reach-mem" if evento.tipo == "memoria" else "reach-act"
        corpo.append(
            f'<path d="{caminho}" fill="none" stroke="{FUNDO}" stroke-width="6" '
            f'stroke-linecap="round"/>'
        )
        corpo.append(
            f'<path d="{caminho}" fill="none" stroke="{cor}" stroke-width="1.75" '
            f'stroke-linecap="round"{tracejado} marker-end="url(#{marcador})"/>'
        )
        caixa = _caixa_texto(evento.texto, label_x, label_y, 13.0)
        corpo.append(
            f'<rect x="{caixa.x:.2f}" y="{caixa.y:.2f}" width="{caixa.largura:.2f}" '
            f'height="{caixa.altura:.2f}" rx="4" fill="{FUNDO}" stroke="{cor}" stroke-width="0.75"/>'
        )
        corpo.append(
            f'<text x="{label_x:.2f}" y="{label_y + 4.5:.2f}" text-anchor="middle" '
            f'font-family="{FONTE}" font-size="12" font-weight="700" fill="{TEXTO}">'
            f'{escape(evento.texto)}</text>'
        )

    for indice, (((fisico, memoria), (fisico_texto, memoria_texto)), (cx, cy)) in enumerate(
        zip(zip(estados, textos), centros)
    ):
        x = cx - largura_no / 2
        y = cy - altura_no / 2
        corpo.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{largura_no:.2f}" height="{altura_no:.2f}" '
            f'rx="9" fill="{CAIXA_ESTADO}" stroke="{BORDA_ESTADO}" stroke-width="1.0"/>'
        )
        corpo.append(
            f'<text x="{cx:.2f}" y="{cy - (8 if memorias else -5):.2f}" text-anchor="middle" '
            f'font-family="{FONTE}" font-size="12" font-weight="700" fill="{TEXTO}">'
            f'{escape(fisico_texto)}</text>'
        )
        if memorias:
            corpo.append(
                f'<text x="{cx:.2f}" y="{cy + 17:.2f}" text-anchor="middle" font-family="{FONTE}" '
                f'font-size="12" fill="{TEXTO_SUAVE}">{escape(memoria_texto)}</text>'
            )
        corpo.append(
            f'<text x="{x + 9:.2f}" y="{y + 16:.2f}" font-family="{FONTE}" font-size="10" '
            f'fill="{TEXTO_SUAVE}">{indice}</text>'
        )

    inicio_x, inicio_y = centros[0]
    final_x, final_y = centros[-1]
    linha_final = (len(estados) - 1) // colunas
    lado_final = 1 if linha_final % 2 == 0 else -1
    corpo.append(
        f'<circle cx="{inicio_x - largura_no / 2 + 12:.2f}" cy="{inicio_y:.2f}" r="4.8" fill="{INICIAL}"/>'
    )
    corpo.append(
        f'<circle cx="{final_x + lado_final * (largura_no / 2 - 12):.2f}" cy="{final_y:.2f}" r="7" '
        f'fill="{FUNDO}" stroke="{FINAL}" stroke-width="2.2"/>'
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'width="{largura}" height="{altura}" role="img" aria-label="Estados alcançáveis">'
        f'<defs>'
        f'<marker id="reach-act" markerWidth="6" markerHeight="6" refX="5.3" refY="3" '
        f'orient="auto" markerUnits="strokeWidth"><path d="M0,0 L6,3 L0,6 z" fill="{SETA_ATUADOR}"/></marker>'
        f'<marker id="reach-mem" markerWidth="6" markerHeight="6" refX="5.3" refY="3" '
        f'orient="auto" markerUnits="strokeWidth"><path d="M0,0 L6,3 L0,6 z" fill="{SETA_MEMORIA}"/></marker>'
        f'</defs><rect width="{largura}" height="{altura}" fill="{FUNDO}"/>'
        + "".join(corpo)
        + "</svg>"
    )
    return MapaSVG(svg=svg, largura=largura, altura=altura)


def _renderizar_aviso_limite(
    total_variaveis: int,
    total_celulas: int,
    limite_celulas: int,
) -> MapaSVG:
    """Retorna um SVG informativo no lugar de um mapa acima do limite."""
    largura = 860
    altura = 350
    max_variaveis = max(0, limite_celulas.bit_length() - 1)

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'width="{largura}" height="{altura}" role="img" aria-label="Limite do mapa atingido">'
        f'<rect width="{largura}" height="{altura}" fill="{FUNDO}"/>'
        f'<rect x="38" y="34" width="784" height="282" rx="12" fill="#FFF8F2" '
        f'stroke="#A33A24" stroke-width="2"/>'
        f'<circle cx="92" cy="91" r="25" fill="#A33A24"/>'
        f'<text x="92" y="101" text-anchor="middle" font-family="{FONTE}" '
        f'font-size="30" font-weight="700" fill="#FFFFFF">!</text>'
        f'<text x="132" y="82" font-family="{FONTE}" font-size="25" '
        f'font-weight="700" fill="#7A2417">Mapa muito grande para exibição</text>'
        f'<text x="132" y="113" font-family="{FONTE}" font-size="15" fill="{TEXTO}">'
        f'O mapa estendido teria {total_celulas} células (2^{total_variaveis}).</text>'
        f'<line x1="72" y1="143" x2="788" y2="143" stroke="#D8B1A7" stroke-width="1"/>'
        f'<text x="72" y="180" font-family="{FONTE}" font-size="17" '
        f'font-weight="700" fill="{TEXTO}">Limite permitido: {limite_celulas} células (2^{max_variaveis}).</text>'
        f'<text x="72" y="214" font-family="{FONTE}" font-size="15" fill="{TEXTO}">'
        f'Isso corresponde a, no máximo, {max_variaveis} variáveis no total:</text>'
        f'<text x="72" y="241" font-family="{FONTE}" font-size="15" '
        f'font-weight="700" fill="{TEXTO}">atuadores + memórias internas ≤ {max_variaveis}</text>'
        f'<text x="72" y="279" font-family="{FONTE}" font-size="13" fill="{TEXTO_SUAVE}">'
        f'O gráfico alternativo de estados não é utilizado; apenas o Mapa de Karnaugh Estendido completo é exibido.</text>'
        f'</svg>'
    )
    return MapaSVG(svg=svg, largura=largura, altura=altura)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def gerar_mapa_svg(
    resultado: Mapping[str, Any],
    *,
    incluir_titulo: bool = True,
    modo: Literal["auto", "completo", "alcancaveis"] = "auto",
    limite_mapa_completo: int | None = None,
    limite_celulas: int = LIMITE_PADRAO_CELULAS,
) -> MapaSVG:
    """Gera exclusivamente o Mapa de Karnaugh Estendido completo.

    O mapa é exibido até ``limite_celulas``. Por padrão, o limite é de
    256 células (2^8), isto é, no máximo oito variáveis considerando a soma
    de atuadores e memórias internas.

    ``modo`` permanece na assinatura por compatibilidade com a interface
    anterior. Os valores ``auto``, ``completo`` e ``alcancaveis`` produzem o
    mesmo comportamento: o mapa estendido completo. A visualização de estados
    alcançáveis não é mais utilizada.

    ``limite_mapa_completo`` também foi mantido para compatibilidade. Quando
    informado, é interpretado como limite legado de variáveis e combinado com
    ``limite_celulas``.
    """
    atuadores = [_nome_normalizado(nome) for nome in resultado.get("atuadores", [])]
    memorias = [_nome_normalizado(nome) for nome in resultado.get("memorias", [])]

    if not atuadores:
        raise ValueError("Nenhum atuador foi informado ao gerador do mapa.")
    if modo not in {"auto", "completo", "alcancaveis"}:
        raise ValueError("modo deve ser 'auto', 'completo' ou 'alcancaveis'.")
    if limite_celulas < 1:
        raise ValueError("limite_celulas deve ser maior que zero.")

    if limite_mapa_completo is not None:
        if limite_mapa_completo < 0:
            raise ValueError("limite_mapa_completo não pode ser negativo.")
        limite_legado = 1 << limite_mapa_completo
        limite_celulas = min(limite_celulas, limite_legado)

    total_variaveis = len(atuadores) + len(memorias)
    total_celulas = 1 << total_variaveis

    if total_celulas > limite_celulas:
        return _renderizar_aviso_limite(
            total_variaveis=total_variaveis,
            total_celulas=total_celulas,
            limite_celulas=limite_celulas,
        )

    eventos = _eventos_expandidos(resultado)
    if not eventos:
        raise ValueError("Nenhum evento foi encontrado para desenhar o mapa.")

    try:
        return _renderizar_mapa_completo(
            resultado,
            eventos,
            atuadores,
            memorias,
            incluir_titulo=incluir_titulo,
        )
    except RuntimeError as erro:
        raise RuntimeError(
            "O mapa está dentro do limite de células, mas não foi possível "
            "organizar todas as transições sem comprometer a leitura."
        ) from erro


__all__ = ["LIMITE_PADRAO_CELULAS", "MapaSVG", "gerar_mapa_svg"]