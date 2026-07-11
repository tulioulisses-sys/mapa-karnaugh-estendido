# engine.py
"""Solucionador do Método do Mapa de Karnaugh Estendido.

Esta versão segue a construção apresentada na apostila e no artigo
"Método de projeto ótimo para circuitos sequenciais fluídicos":

1. monta os conjuntos máximos de sinais (estados de todos os sensores);
2. procura a menor quantidade de memórias capaz de diferenciar os passos;
3. prefere a colocação tradicional das memórias do método;
4. insere X+, X-, Y+, Y- etc. na sequência;
5. usa o sinal produzido pelo passo anterior como condição básica;
6. faz a qualificação progressiva entre comando e contracomando;
7. acrescenta qualificadores para eliminar pontos perigosos;
8. apresenta também as equações completas das memórias X, Y, ...

Exemplos aceitos:

    A+, B+, B-, A-
    A+, B+, B-, C+, B+, B-, C-, A-
    A+, B+, (C-, D+), (D-, A-)

Dependência:

    pip install sympy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations, permutations
import re
from typing import Mapping, Optional

from sympy import And, Not, Or, Symbol, false, true


VERSAO = "engine2-metodo-apostila-artigo-7.0"

# Quantidade de alternativas mantidas pela busca para cada estado dinâmico.
# O aumento deste valor torna a busca mais abrangente, porém mais lenta.
_LIMITE_ALTERNATIVAS = 1200
_LIMITE_MEMORIAS = 8


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Acao:
    atuador: str
    sentido: str

    @property
    def destino(self) -> int:
        return 1 if self.sentido == "+" else 0

    @property
    def nome(self) -> str:
        return f"{self.atuador}{self.sentido}"


@dataclass
class Etapa:
    indice: int
    acoes: tuple[Acao, ...]
    antes: tuple[int, ...]
    depois: tuple[int, ...]
    intermediarios: tuple[tuple[int, ...], ...]
    fase: int = 0
    codigo: tuple[int, ...] = ()


@dataclass
class Evento:
    indice: int
    tipo: str  # "atuador" ou "memoria"
    saidas: tuple[str, ...]
    fisico: tuple[int, ...]
    codigo: tuple[int, ...]
    etapa_indice: Optional[int] = None
    acoes: tuple[Acao, ...] = ()
    intermediarios: tuple[tuple[int, ...], ...] = ()

    # Condição mínima produzida pelo passo anterior.
    base: object = true

    # Equação final do evento.
    termo: object = true

    # Todos os fatores na ordem em que aparecem
    # na equação final.
    fatores_ordenados: list[object] = field(
        default_factory=list
    )

    # Fatores acrescentados para diferenciar
    # comando e contracomando.
    qualificadores_contracomando: list[object] = field(
        default_factory=list
    )

    # Fatores acrescentados posteriormente para
    # eliminar pontos perigosos.
    qualificadores_complementares: list[object] = field(
        default_factory=list
    )

    # Estados nos quais a equação qualificada poderia
    # disparar indevidamente antes da complementação.
    pontos_perigosos: list[tuple[int, ...]] = field(
        default_factory=list
    )


@dataclass(frozen=True)
class Ponto:
    evento: int
    valores: tuple[int, ...]


@dataclass(frozen=True)
class CaminhoCandidato:
    mesma_fonte: int
    max_ligadas: int
    soma_ligadas: int
    mudancas: int
    posicoes_mudanca: tuple[int, ...]
    bits_mudanca: tuple[int, ...]
    codigos: tuple[int, ...]
    fechamento: tuple[int, ...]

    @property
    def chave(self):
        # Prioridades coerentes com a construção da apostila:
        # 1) menos comandos de memória;
        # 2) reutilizar o mesmo sinal para ligar/desligar uma memória;
        # 3) manter menos memórias simultaneamente acionadas;
        # 4) reduzir o tempo total em que as memórias ficam ligadas.
        return (
            self.mudancas,
            -self.mesma_fonte,
            self.max_ligadas,
            self.soma_ligadas,
            self.posicoes_mudanca,
            self.bits_mudanca,
            self.codigos,
            self.fechamento,
        )


@dataclass
class Resultado:
    atuadores: tuple[str, ...]
    estado_inicial: dict[str, int]
    etapas: list[Etapa]

    # Eventos lógicos, incluindo os comandos das memórias.
    eventos: tuple[Evento, ...]

    memorias: tuple[str, ...]
    expressoes: dict[str, object]
    equacoes: dict[str, str]
    equacoes_memorias: dict[str, str]
    validacoes: tuple[str, ...]
    observacoes: tuple[str, ...] = ()

    def resumo(self) -> str:
        linhas = ["ETAPAS E FASES"]

        for etapa in self.etapas:
            acoes = " e ".join(acao.nome for acao in etapa.acoes)
            antes = _estado_texto(etapa.antes, self.atuadores)
            depois = _estado_texto(etapa.depois, self.atuadores)
            codigo = _codigo_texto(etapa.codigo, self.memorias)
            sufixo = f" {codigo}" if codigo else ""

            linhas.append(
                f"{etapa.indice + 1:>2}: {acoes:<20} "
                f"{antes} -> {depois}  F{etapa.fase}{sufixo}"
            )

        linhas += [
            "\nMEMÓRIAS",
            ", ".join(self.memorias) if self.memorias else "Nenhuma",
            "\nEQUAÇÕES",
        ]

        linhas += [
            f"{saida} = {equacao}"
            for saida, equacao in self.equacoes.items()
        ]

        if self.equacoes_memorias:
            linhas.append("\nEQUAÇÕES COMPLETAS DAS MEMÓRIAS")
            linhas += [
                f"{memoria} = {equacao}"
                for memoria, equacao in self.equacoes_memorias.items()
            ]
            linhas.append(
                "  Forma utilizada: M = (M+ + m1).¬(M-), com prioridade de RESET."
            )

        linhas.append("\nVALIDAÇÃO")
        linhas += [f"✓ {texto}" for texto in self.validacoes]

        if self.observacoes:
            linhas.append("\nOBSERVAÇÕES")
            linhas += [f"- {texto}" for texto in self.observacoes]

        return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Leitura e simulação da sequência
# ---------------------------------------------------------------------------


_RE_ACAO = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\s*([+-])$")


def _separar_topo(texto: str) -> list[str]:
    partes: list[str] = []
    atual: list[str] = []
    nivel = 0

    for caractere in texto:
        if caractere == "(":
            nivel += 1
            atual.append(caractere)
        elif caractere == ")":
            nivel -= 1
            if nivel < 0:
                raise ValueError("Parênteses não balanceados.")
            atual.append(caractere)
        elif caractere in ",;" and nivel == 0:
            trecho = "".join(atual).strip()
            if trecho:
                partes.append(trecho)
            atual = []
        else:
            atual.append(caractere)

    if nivel != 0:
        raise ValueError("Parênteses não balanceados.")

    trecho = "".join(atual).strip()
    if trecho:
        partes.append(trecho)

    return partes


def interpretar_sequencia(entrada) -> list[tuple[Acao, ...]]:
    """Converte texto ou listas em grupos de ações simultâneas."""
    itens = _separar_topo(entrada) if isinstance(entrada, str) else list(entrada)

    if not itens:
        raise ValueError("A sequência não pode ser vazia.")

    etapas: list[tuple[Acao, ...]] = []

    for item in itens:
        if isinstance(item, str):
            texto = item.strip().replace("−", "-").replace("–", "-")

            if texto.startswith("(") != texto.endswith(")"):
                raise ValueError(f"Parênteses inválidos em {item!r}.")

            partes = (
                re.split(r"[,;]", texto[1:-1])
                if texto.startswith("(") and texto.endswith(")")
                else [texto]
            )
        else:
            partes = list(item)

        acoes: list[Acao] = []
        usados: set[str] = set()

        for parte in partes:
            texto_acao = str(parte).strip().replace("−", "-").replace("–", "-")
            match = _RE_ACAO.fullmatch(texto_acao)

            if not match:
                raise ValueError(f"Comando inválido: {parte!r}.")

            atuador, sentido = match.groups()
            atuador = atuador.upper()

            if atuador in usados:
                raise ValueError(
                    f"O atuador {atuador} aparece duas vezes na mesma etapa."
                )

            usados.add(atuador)
            acoes.append(Acao(atuador, sentido))

        if not acoes:
            raise ValueError("Foi encontrada uma etapa vazia.")

        etapas.append(tuple(acoes))

    return etapas


def construir_etapas(
    sequencia,
    estado_inicial: Optional[Mapping[str, int]] = None,
) -> tuple[tuple[str, ...], dict[str, int], list[Etapa]]:
    grupos = interpretar_sequencia(sequencia)

    atuadores: list[str] = []
    for grupo in grupos:
        for acao in grupo:
            if acao.atuador not in atuadores:
                atuadores.append(acao.atuador)

    inicial = {atuador: 0 for atuador in atuadores}

    if estado_inicial:
        for nome, valor in estado_inicial.items():
            nome = str(nome).upper()

            if nome not in inicial:
                raise ValueError(f"O atuador {nome} não aparece na sequência.")

            if valor not in (0, 1, False, True):
                raise ValueError("As posições iniciais devem ser 0 ou 1.")

            inicial[nome] = int(valor)

    posicao = {nome: i for i, nome in enumerate(atuadores)}
    estado = tuple(inicial[nome] for nome in atuadores)
    etapas: list[Etapa] = []

    for indice, grupo in enumerate(grupos):
        antes = estado
        depois = list(antes)

        for acao in grupo:
            i = posicao[acao.atuador]

            if antes[i] == acao.destino:
                raise ValueError(
                    f"Etapa {indice + 1}: foi solicitado {acao.nome}, mas o "
                    f"atuador já está na posição {acao.destino}."
                )

            depois[i] = acao.destino

        depois_tupla = tuple(depois)
        intermediarios: set[tuple[int, ...]] = set()

        for quantidade in range(1, len(grupo)):
            for concluidas in combinations(range(len(grupo)), quantidade):
                parcial = list(antes)

                for k in concluidas:
                    acao = grupo[k]
                    parcial[posicao[acao.atuador]] = acao.destino

                intermediarios.add(tuple(parcial))

        etapas.append(
            Etapa(
                indice=indice,
                acoes=grupo,
                antes=antes,
                depois=depois_tupla,
                intermediarios=tuple(sorted(intermediarios)),
            )
        )
        estado = depois_tupla

    return tuple(atuadores), inicial, etapas


# ---------------------------------------------------------------------------
# Conflitos entre conjuntos máximos de sinais
# ---------------------------------------------------------------------------


def _saidas_atuadores(etapas: list[Etapa]) -> tuple[str, ...]:
    saidas: list[str] = []

    for etapa in etapas:
        for acao in etapa.acoes:
            if acao.nome not in saidas:
                saidas.append(acao.nome)

    return tuple(saidas)


def _ultimo_sentido(etapas: list[Etapa], atuador: str) -> Optional[str]:
    for etapa in reversed(etapas):
        for acao in etapa.acoes:
            if acao.atuador == atuador:
                return acao.sentido
    return None


def _rotulos_originais(
    etapas: list[Etapa],
    ciclo: bool,
) -> dict[str, list[str]]:
    """Rótulos 1/0/X dos comandos físicos antes das memórias."""
    resultado: dict[str, list[str]] = {}

    for saida in _saidas_atuadores(etapas):
        atuador, sentido = saida[:-1], saida[-1]
        oposto = "-" if sentido == "+" else "+"
        ultimo = _ultimo_sentido(etapas, atuador) if ciclo else None
        rotulos: list[str] = []

        for etapa in etapas:
            atual = next(
                (a.sentido for a in etapa.acoes if a.atuador == atuador),
                None,
            )

            if atual == sentido:
                rotulos.append("1")
            elif atual == oposto:
                rotulos.append("0")
            elif ultimo is None or ultimo == oposto:
                rotulos.append("0")
            else:
                rotulos.append("X")

            if atual is not None:
                ultimo = atual

        resultado[saida] = rotulos

    return resultado


def _arestas_conflito(
    etapas: list[Etapa],
    rotulos: dict[str, list[str]],
) -> set[tuple[int, int]]:
    """Passos com mesmo conjunto máximo e decisões incompatíveis."""
    ativos = [set((etapa.antes,) + etapa.intermediarios) for etapa in etapas]
    arestas: set[tuple[int, int]] = set()

    for i, j in combinations(range(len(etapas)), 2):
        if not (ativos[i] & ativos[j]):
            continue

        if any(
            {rotulos[saida][i], rotulos[saida][j]} == {"0", "1"}
            for saida in rotulos
        ):
            arestas.add((i, j))

    return arestas


def _maior_clique_aproximada(
    quantidade: int,
    arestas: set[tuple[int, int]],
) -> int:
    """Limite inferior simples para a quantidade de códigos distintos."""
    vizinhos = {i: set() for i in range(quantidade)}
    for a, b in arestas:
        vizinhos[a].add(b)
        vizinhos[b].add(a)

    melhor = 1 if quantidade else 0

    for inicio in sorted(vizinhos, key=lambda i: len(vizinhos[i]), reverse=True):
        clique = [inicio]
        candidatos = sorted(
            vizinhos[inicio],
            key=lambda i: len(vizinhos[i]),
            reverse=True,
        )

        for candidato in candidatos:
            if all(candidato in vizinhos[outro] for outro in clique):
                clique.append(candidato)

        melhor = max(melhor, len(clique))

    return melhor


# ---------------------------------------------------------------------------
# Busca da colocação das memórias conforme o método
# ---------------------------------------------------------------------------


def _inteiro_para_codigo(valor: int, quantidade: int) -> tuple[int, ...]:
    return tuple((valor >> i) & 1 for i in range(quantidade))


def _nomes_memorias(quantidade: int, atuadores: tuple[str, ...]) -> tuple[str, ...]:
    if quantidade <= 0:
        return ()

    candidatos = list("XYZWVUTSRQPONMLKJIHGFEDCBA")
    nomes: list[str] = []

    for candidato in candidatos:
        if candidato not in atuadores:
            nomes.append(candidato)
        if len(nomes) == quantidade:
            return tuple(nomes)

    indice = 1
    while len(nomes) < quantidade:
        nome = f"M{indice}"
        if nome not in atuadores:
            nomes.append(nome)
        indice += 1

    return tuple(nomes)


def _manter_melhores(
    candidatos: list[CaminhoCandidato],
    limite: int,
) -> tuple[CaminhoCandidato, ...]:
    unicos: dict[tuple[tuple[int, ...], tuple[int, ...]], CaminhoCandidato] = {}

    for candidato in candidatos:
        chave = (candidato.codigos, candidato.fechamento)
        anterior = unicos.get(chave)
        if anterior is None or candidato.chave < anterior.chave:
            unicos[chave] = candidato

    ordenados = sorted(unicos.values(), key=lambda item: item.chave)
    return tuple(ordenados[:limite])


def _buscar_caminhos_memorias(
    etapas: list[Etapa],
    arestas: set[tuple[int, int]],
    quantidade_memorias: int,
    *,
    limite: int,
) -> tuple[CaminhoCandidato, ...]:
    """Obtém as melhores colocações de SET/RESET para uma quantidade de memórias.

    A busca percorre códigos binários adjacentes, permitindo no máximo uma
    mudança de memória entre dois passos físicos. No fechamento, podem ocorrer
    vários RESETs sucessivos, como previsto no artigo.
    """
    n = len(etapas)
    m = quantidade_memorias

    if n == 0:
        return ()

    if m == 0:
        if arestas:
            return ()
        return (
            CaminhoCandidato(
                mesma_fonte=0,
                max_ligadas=0,
                soma_ligadas=0,
                mudancas=0,
                posicoes_mudanca=(),
                bits_mudanca=(),
                codigos=tuple(0 for _ in etapas),
                fechamento=(0,),
            ),
        )

    mascara_total = (1 << m) - 1

    anteriores: list[list[int]] = [[] for _ in range(n)]
    ultimo_conflito = [-1] * n

    for a, b in arestas:
        if a > b:
            a, b = b, a
        anteriores[b].append(a)
        ultimo_conflito[a] = max(ultimo_conflito[a], b)

    ids_fontes: dict[tuple[tuple[str, int], ...], int] = {}
    fontes_etapas: list[int] = []

    for etapa in etapas:
        assinatura = tuple((acao.atuador, acao.destino) for acao in etapa.acoes)
        if assinatura not in ids_fontes:
            ids_fontes[assinatura] = len(ids_fontes)
        fontes_etapas.append(ids_fontes[assinatura])

    def atualizar_fronteira(
        fronteira: tuple[tuple[int, int], ...],
        indice: int,
        codigo: int,
    ) -> tuple[tuple[int, int], ...]:
        mapa = dict(fronteira)

        if ultimo_conflito[indice] > indice:
            mapa[indice] = codigo

        return tuple(
            sorted(
                (j, valor)
                for j, valor in mapa.items()
                if ultimo_conflito[j] > indice
            )
        )

    def codigo_valido(
        indice: int,
        codigo: int,
        fronteira: tuple[tuple[int, int], ...],
    ) -> bool:
        mapa = dict(fronteira)
        return all(mapa[j] != codigo for j in anteriores[indice])

    @lru_cache(maxsize=None)
    def dp(
        indice: int,
        codigo_atual: int,
        fronteira: tuple[tuple[int, int], ...],
        usados: int,
        ultima_fonte_set: tuple[int, ...],
        max_ligadas: int,
    ) -> tuple[CaminhoCandidato, ...]:
        if indice == n:
            if usados != mascara_total:
                return ()

            ativos = [bit for bit in range(m) if (codigo_atual >> bit) & 1]
            candidatos_finais: list[CaminhoCandidato] = []

            for ordem_reset in permutations(ativos):
                codigo = codigo_atual
                fontes_set = list(ultima_fonte_set)
                mesma_fonte = 0
                caminho = [codigo]
                bits: list[int] = []
                posicoes: list[int] = []
                fonte_atual = fontes_etapas[-1]

                for bit in ordem_reset:
                    if fontes_set[bit] == fonte_atual:
                        mesma_fonte += 1

                    fontes_set[bit] = -1
                    codigo ^= 1 << bit
                    caminho.append(codigo)
                    bits.append(bit)
                    posicoes.append(n)

                    # Um RESET posterior passa a ser provocado pelo estado
                    # produzido pelo comando de memória anterior.
                    fonte_atual = -(bit + 1)

                if codigo != 0:
                    continue

                candidatos_finais.append(
                    CaminhoCandidato(
                        mesma_fonte=mesma_fonte,
                        max_ligadas=max_ligadas,
                        soma_ligadas=0,
                        mudancas=len(ordem_reset),
                        posicoes_mudanca=tuple(posicoes),
                        bits_mudanca=tuple(bits),
                        codigos=(),
                        fechamento=tuple(caminho),
                    )
                )

            return _manter_melhores(candidatos_finais, limite)

        proximos_codigos = [codigo_atual]
        proximos_codigos.extend(codigo_atual ^ (1 << bit) for bit in range(m))
        candidatos: list[CaminhoCandidato] = []

        for novo_codigo in proximos_codigos:
            if not codigo_valido(indice, novo_codigo, fronteira):
                continue

            diferenca = codigo_atual ^ novo_codigo
            usados_novos = usados
            fontes_set = list(ultima_fonte_set)
            mesma_fonte_local = 0
            bits_locais: tuple[int, ...] = ()
            posicoes_locais: tuple[int, ...] = ()

            if diferenca:
                bit = diferenca.bit_length() - 1
                valor_novo = (novo_codigo >> bit) & 1

                if valor_novo:
                    if not ((usados >> bit) & 1):
                        # Quebra de simetria: X deve aparecer antes de Y,
                        # Y antes de Z, e assim sucessivamente.
                        if bit != usados.bit_count():
                            continue
                        usados_novos |= 1 << bit

                    fontes_set[bit] = fontes_etapas[indice - 1]
                else:
                    if fontes_set[bit] == fontes_etapas[indice - 1]:
                        mesma_fonte_local = 1
                    fontes_set[bit] = -1

                bits_locais = (bit,)
                posicoes_locais = (indice,)

            fronteira_nova = atualizar_fronteira(
                fronteira,
                indice,
                novo_codigo,
            )

            subcandidatos = dp(
                indice + 1,
                novo_codigo,
                fronteira_nova,
                usados_novos,
                tuple(fontes_set),
                max(max_ligadas, novo_codigo.bit_count()),
            )

            for sub in subcandidatos:
                candidatos.append(
                    CaminhoCandidato(
                        mesma_fonte=mesma_fonte_local + sub.mesma_fonte,
                        max_ligadas=sub.max_ligadas,
                        soma_ligadas=novo_codigo.bit_count() + sub.soma_ligadas,
                        mudancas=len(bits_locais) + sub.mudancas,
                        posicoes_mudanca=(
                            posicoes_locais + sub.posicoes_mudanca
                        ),
                        bits_mudanca=bits_locais + sub.bits_mudanca,
                        codigos=(novo_codigo,) + sub.codigos,
                        fechamento=sub.fechamento,
                    )
                )

        return _manter_melhores(candidatos, limite)

    fronteira_inicial = atualizar_fronteira((), 0, 0)
    resultados: list[CaminhoCandidato] = []

    for sub in dp(
        1,
        0,
        fronteira_inicial,
        0,
        tuple(-1 for _ in range(m)),
        0,
    ):
        resultados.append(
            CaminhoCandidato(
                mesma_fonte=sub.mesma_fonte,
                max_ligadas=sub.max_ligadas,
                soma_ligadas=sub.soma_ligadas,
                mudancas=sub.mudancas,
                posicoes_mudanca=sub.posicoes_mudanca,
                bits_mudanca=sub.bits_mudanca,
                codigos=(0,) + sub.codigos,
                fechamento=sub.fechamento,
            )
        )

    return _manter_melhores(resultados, limite)


def _nos_de_conflito(
    arestas: set[tuple[int, int]],
) -> tuple[int, ...]:
    """Passos físicos que precisam de códigos de fase distintos."""
    return tuple(sorted({indice for aresta in arestas for indice in aresta}))


def _chave_metodo_candidato(
    candidato: CaminhoCandidato,
    arestas: set[tuple[int, int]],
) -> tuple:
    """Ordena colocações de memória conforme a construção do método.

    Entre caminhos com a mesma quantidade de memórias, a apostila mantém
    uma região de memória enquanto ela continua válida e evita ativar várias
    memórias simultaneamente nos conjuntos máximos que precisam ser
    diferenciados. Essa regra reproduz, entre outros, os exemplos:

      A+, B+, B-, A-
      A+, A-, B+, B-, C+, C-
      A+, B+, B-, C+, B+, B-, C-, A-
    """
    nos = _nos_de_conflito(arestas)
    codigos = tuple(candidato.codigos[indice] for indice in nos)

    mudancas_regiao = sum(
        anterior != posterior
        for anterior, posterior in zip(codigos, codigos[1:])
    )
    quantidade_regioes = len(set(codigos))
    peso_total = sum(codigo.bit_count() for codigo in codigos)
    peso_maximo = max((codigo.bit_count() for codigo in codigos), default=0)

    return (
        quantidade_regioes,
        mudancas_regiao,
        peso_total,
        peso_maximo,
        codigos,
        candidato.chave,
    )


def _atribuir_candidato(
    etapas: list[Etapa],
    candidato: CaminhoCandidato,
    quantidade_memorias: int,
) -> dict[int, tuple[tuple[int, ...], ...]]:
    codigos = [
        _inteiro_para_codigo(valor, quantidade_memorias)
        for valor in candidato.codigos
    ]

    mapa_fases: dict[tuple[int, ...], int] = {}

    for etapa, codigo in zip(etapas, codigos):
        etapa.codigo = codigo
        if codigo not in mapa_fases:
            mapa_fases[codigo] = len(mapa_fases)
        etapa.fase = mapa_fases[codigo]

    caminhos: dict[int, tuple[tuple[int, ...], ...]] = {}

    for i in range(len(etapas) - 1):
        atual = codigos[i]
        proximo = codigos[i + 1]
        caminhos[i] = (atual,) if atual == proximo else (atual, proximo)

    fechamento = tuple(
        _inteiro_para_codigo(valor, quantidade_memorias)
        for valor in candidato.fechamento
    )
    caminhos[len(etapas) - 1] = fechamento

    return caminhos


# ---------------------------------------------------------------------------
# Sequência expandida: atuadores + comandos das memórias
# ---------------------------------------------------------------------------


def _literal(simbolo: Symbol, valor: int):
    return simbolo if valor else Not(simbolo)


def _conclusao_acoes(
    acoes: tuple[Acao, ...],
    simbolos: dict[str, Symbol],
):
    fatores = [_literal(simbolos[acao.atuador], acao.destino) for acao in acoes]
    return And(*fatores) if fatores else true


def _fatores_conclusao_acoes(
    acoes: tuple[Acao, ...],
    simbolos: dict[str, Symbol],
) -> list[object]:
    return [_literal(simbolos[acao.atuador], acao.destino) for acao in acoes]


def _construir_eventos(
    etapas: list[Etapa],
    memorias: tuple[str, ...],
    caminhos: dict[int, tuple[tuple[int, ...], ...]],
    simbolos: dict[str, Symbol],
) -> list[Evento]:
    eventos: list[Evento] = []

    for etapa in etapas:
        eventos.append(
            Evento(
                indice=len(eventos),
                tipo="atuador",
                saidas=tuple(acao.nome for acao in etapa.acoes),
                fisico=etapa.antes,
                codigo=etapa.codigo,
                etapa_indice=etapa.indice,
                acoes=etapa.acoes,
                intermediarios=etapa.intermediarios,
            )
        )

        caminho = caminhos[etapa.indice]

        for atual, novo in zip(caminho, caminho[1:]):
            diferentes = [
                i for i, (antigo, novo_valor) in enumerate(zip(atual, novo))
                if antigo != novo_valor
            ]

            if len(diferentes) != 1:
                raise RuntimeError(
                    "A colocação das memórias tentou alterar mais de uma "
                    "memória no mesmo evento."
                )

            bit = diferentes[0]
            sentido = "+" if novo[bit] else "-"

            eventos.append(
                Evento(
                    indice=len(eventos),
                    tipo="memoria",
                    saidas=(f"{memorias[bit]}{sentido}",),
                    fisico=etapa.depois,
                    codigo=atual,
                )
            )

    if not eventos:
        return eventos

    def fatores_produzidos(evento: Evento) -> list[object]:
        """Sinais produzidos quando um evento termina.

        O método usa o sinal produzido pelo passo anterior como condição
        mínima do passo seguinte. Para o primeiro passo, considera-se o
        fechamento lógico da sequência: S em série com o sinal produzido
        pelo último evento.
        """
        if evento.tipo == "atuador":
            return _fatores_conclusao_acoes(evento.acoes, simbolos)

        nome = evento.saidas[0]
        memoria, sentido = nome[:-1], nome[-1]
        return [
            _literal(
                simbolos[memoria],
                1 if sentido == "+" else 0,
            )
        ]

    for i, evento in enumerate(eventos):
        anterior = eventos[i - 1]
        fatores = fatores_produzidos(anterior)

        if i == 0:
            fatores = [simbolos["S"], *fatores]

        evento.base = And(*fatores) if fatores else true
        evento.fatores_ordenados = list(fatores)

    return eventos


# ---------------------------------------------------------------------------
# Qualificação progressiva como na apostila
# ---------------------------------------------------------------------------


def _todas_saidas(eventos: list[Evento]) -> tuple[str, ...]:
    saidas: list[str] = []

    for evento in eventos:
        for saida in evento.saidas:
            if saida not in saidas:
                saidas.append(saida)

    return tuple(saidas)


def _rotulos_eventos(
    eventos: list[Evento],
    ciclo: bool,
) -> dict[str, list[str]]:
    """1 = deve atuar; 0 = bloqueado; X = pode permanecer acionado."""
    saidas = _todas_saidas(eventos)
    resultado: dict[str, list[str]] = {}

    por_evento = [
        {saida[:-1]: saida[-1] for saida in evento.saidas}
        for evento in eventos
    ]

    for saida in saidas:
        dispositivo, sentido = saida[:-1], saida[-1]
        oposto = "-" if sentido == "+" else "+"
        ultimo: Optional[str] = None

        if ciclo:
            for evento in reversed(eventos):
                atual = next(
                    (s[-1] for s in evento.saidas if s[:-1] == dispositivo),
                    None,
                )
                if atual is not None:
                    ultimo = atual
                    break

        rotulos: list[str] = []

        for mapa in por_evento:
            atual = mapa.get(dispositivo)

            if atual == sentido:
                rotulos.append("1")
            elif atual == oposto:
                rotulos.append("0")
            elif ultimo is None or ultimo == oposto:
                rotulos.append("0")
            else:
                rotulos.append("X")

            if atual is not None:
                ultimo = atual

        resultado[saida] = rotulos

    return resultado


def _pontos_alcancaveis(eventos: list[Evento]) -> list[Ponto]:
    pontos: list[Ponto] = []

    for evento in eventos:
        estados = (evento.fisico,) + evento.intermediarios

        for fisico in estados:
            valores = tuple(fisico) + tuple(evento.codigo) + (1,)
            pontos.append(Ponto(evento.indice, valores))

    unicos: list[Ponto] = []
    vistos: set[tuple[int, tuple[int, ...]]] = set()

    for ponto in pontos:
        chave = (ponto.evento, ponto.valores)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(ponto)

    return unicos


def _avaliar(expressao, ordem_simbolos: list[Symbol], valores: tuple[int, ...]) -> bool:
    substituicoes = {
        simbolo: bool(valor)
        for simbolo, valor in zip(ordem_simbolos, valores)
    }
    return bool(expressao.subs(substituicoes))


def _base_literal_unica(expressao) -> Optional[tuple[str, int]]:
    if isinstance(expressao, Symbol):
        return str(expressao), 1

    if expressao.func is Not and isinstance(expressao.args[0], Symbol):
        return str(expressao.args[0]), 0

    return None


def _qualificar_progressivamente(
    eventos: list[Evento],
    rotulos: dict[str, list[str]],
    pontos: list[Ponto],
    ordem_nomes: list[str],
    ordem_simbolos: list[Symbol],
    quantidade_atuadores: int,
    arestas_conflito: set[tuple[int, int]],
) -> dict[str, object]:
    """Reproduz a qualificação progressiva ensinada na apostila.

    A rotina mantém separadas duas etapas do método:

    1. qualificadores usados para diferenciar comando e contracomando;
    2. qualificadores complementares usados para eliminar pontos perigosos.

    A verificação dos pontos perigosos é feita sobre os conjuntos máximos de
    sinais alcançáveis, conforme o artigo e os exemplos da apostila. Não se
    deve substituir essa verificação por uma análise exclusiva de bordas
    0 -> 1, pois isso altera a quantidade mínima de memórias e as equações.
    """
    alvo = {
        evento.indice: tuple(evento.fisico) + tuple(evento.codigo) + (1,)
        for evento in eventos
    }

    qualificadores_contracomando: dict[int, list[object]] = {
        evento.indice: [] for evento in eventos
    }
    qualificadores_complementares: dict[int, list[object]] = {
        evento.indice: [] for evento in eventos
    }

    # ------------------------------------------------------------------
    # 1) Qualificação entre comando e contracomando.
    #
    # Cada ocorrência é comparada com todas as ocorrências do comando de
    # sentido oposto. A comparação deve acontecer nos dois sentidos.
    # Exemplo da apostila para A+, B+, B-, A-:
    #   A+ recebe x0 e A- recebe x.
    # ------------------------------------------------------------------
    for evento in eventos:
        dispositivos_evento = {saida[:-1] for saida in evento.saidas}

        for saida in evento.saidas:
            dispositivo, sentido = saida[:-1], saida[-1]
            oposto = "-" if sentido == "+" else "+"

            eventos_opostos = [
                outro
                for outro in eventos
                if f"{dispositivo}{oposto}" in outro.saidas
            ]

            for outro in eventos_opostos:
                expressao_atual = And(
                    evento.base,
                    *qualificadores_contracomando[evento.indice],
                )
                valores_oposto = alvo[outro.indice]

                # Se a expressão atual já é falsa na ocorrência oposta,
                # comando e contracomando já estão diferenciados.
                if not _avaliar(
                    expressao_atual,
                    ordem_simbolos,
                    valores_oposto,
                ):
                    continue

                valores_alvo = alvo[evento.indice]
                simbolos_usados = expressao_atual.free_symbols
                base_oposta = _base_literal_unica(outro.base)
                candidatos: list[tuple[int, int, int, object]] = []

                for permitir_proprios in (False, True):
                    candidatos = []

                    for indice, nome in enumerate(ordem_nomes[:-1]):
                        simbolo = ordem_simbolos[indice]

                        if not permitir_proprios and nome in dispositivos_evento:
                            continue
                        if simbolo in simbolos_usados:
                            continue
                        if valores_alvo[indice] == valores_oposto[indice]:
                            continue

                        prioridade = 5

                        # A apostila prefere o complemento da memória que
                        # caracteriza o comando oposto.
                        if (
                            base_oposta
                            and base_oposta[0] == nome
                            and indice >= quantidade_atuadores
                        ):
                            prioridade = 0
                        elif base_oposta and base_oposta[0] == nome:
                            # Evita reutilizar diretamente o sinal físico que
                            # dispara o comando oposto; primeiro procura-se um
                            # diferenciador independente, como no artigo.
                            prioridade = 4
                        elif nome in dispositivos_evento:
                            # Sensor do próprio atuador somente como último
                            # recurso, por exemplo na sequência A+, A-.
                            prioridade = 6
                        elif indice < quantidade_atuadores:
                            prioridade = 1
                        else:
                            prioridade = 2

                        desempate = (
                            -indice if indice < quantidade_atuadores else indice
                        )
                        candidatos.append(
                            (
                                prioridade,
                                desempate,
                                indice,
                                _literal(simbolo, valores_alvo[indice]),
                            )
                        )

                    if candidatos:
                        break

                if not candidatos:
                    raise RuntimeError(
                        f"Não foi possível qualificar {evento.saidas} em "
                        f"relação a {outro.saidas}."
                    )

                _, _, _, escolhido = min(candidatos)
                qualificadores_contracomando[evento.indice].append(escolhido)

    # ------------------------------------------------------------------
    # 2) Verificação dos pontos perigosos e qualificação complementar.
    #
    # Um ponto é perigoso quando a equação já qualificada é verdadeira em
    # um conjunto máximo de sinais no qual aquela saída deve estar em 0.
    # ------------------------------------------------------------------
    for evento in eventos:
        valores_alvo = alvo[evento.indice]

        while True:
            expressao_atual = And(
                evento.base,
                *qualificadores_contracomando[evento.indice],
                *qualificadores_complementares[evento.indice],
            )

            perigosos = [
                ponto
                for ponto in pontos
                if any(
                    rotulos[saida][ponto.evento] == "0"
                    for saida in evento.saidas
                )
                and _avaliar(
                    expressao_atual,
                    ordem_simbolos,
                    ponto.valores,
                )
            ]

            if not perigosos:
                break

            simbolos_usados = expressao_atual.free_symbols
            dispositivos_evento = {saida[:-1] for saida in evento.saidas}
            melhor = None

            for permitir_proprios in (False, True):
                melhor = None

                for indice, nome in enumerate(ordem_nomes[:-1]):
                    simbolo = ordem_simbolos[indice]

                    if not permitir_proprios and nome in dispositivos_evento:
                        continue
                    if simbolo in simbolos_usados:
                        continue

                    literal = _literal(simbolo, valores_alvo[indice])
                    cobertura = sum(
                        not _avaliar(literal, ordem_simbolos, ponto.valores)
                        for ponto in perigosos
                    )

                    if cobertura == 0:
                        continue

                    # Nos pontos perigosos, o método gráfico prefere uma
                    # variável de memória quando ela está disponível.
                    prioridade = (
                        -cobertura,
                        2 if nome in dispositivos_evento else (
                            0 if indice >= quantidade_atuadores else 1
                        ),
                        indice,
                    )

                    if melhor is None or prioridade < melhor[0]:
                        melhor = (prioridade, literal)

                if melhor is not None:
                    break

            if melhor is None:
                raise RuntimeError(
                    f"Não foi possível eliminar os pontos perigosos de "
                    f"{evento.saidas}."
                )

            qualificadores_complementares[evento.indice].append(melhor[1])

    # ------------------------------------------------------------------
    # 3) Organização didática dos fatores.
    #
    # Em regiões canônicas usadas apenas uma vez, a apostila apresenta a
    # memória de menor ordem (X antes de Y, Y antes de Z...) como
    # qualificador da fase e deixa a memória posterior para a coluna de
    # pontos perigosos. A troca abaixo não altera a equação final; apenas
    # preserva a separação didática mostrada nas tabelas do método.
    # ------------------------------------------------------------------
    passos_conflito = set(_nos_de_conflito(arestas_conflito))
    frequencia_codigo: dict[tuple[int, ...], int] = {}

    for evento in eventos:
        if (
            evento.tipo == "atuador"
            and evento.etapa_indice in passos_conflito
        ):
            frequencia_codigo[evento.codigo] = (
                frequencia_codigo.get(evento.codigo, 0) + 1
            )

    nomes_memorias = ordem_nomes[quantidade_atuadores:-1]
    indice_memoria = {
        nome: indice for indice, nome in enumerate(nomes_memorias)
    }

    def posicao_memoria(literal) -> Optional[int]:
        if isinstance(literal, Symbol):
            nome = str(literal)
        elif literal.func is Not and isinstance(literal.args[0], Symbol):
            nome = str(literal.args[0])
        else:
            return None
        return indice_memoria.get(nome)

    for evento in eventos:
        if (
            evento.tipo != "atuador"
            or evento.etapa_indice not in passos_conflito
            or frequencia_codigo.get(evento.codigo, 0) != 1
        ):
            continue

        memoria_qualificacao = [
            (posicao_memoria(literal), posicao, literal)
            for posicao, literal in enumerate(
                qualificadores_contracomando[evento.indice]
            )
            if posicao_memoria(literal) is not None
        ]
        memoria_perigo = [
            (posicao_memoria(literal), posicao, literal)
            for posicao, literal in enumerate(
                qualificadores_complementares[evento.indice]
            )
            if posicao_memoria(literal) is not None
        ]

        if not memoria_qualificacao or not memoria_perigo:
            continue

        qualificador_tardio = min(memoria_qualificacao)
        qualificador_inicial = min(memoria_perigo)

        if qualificador_inicial[0] >= qualificador_tardio[0]:
            continue

        _, pos_q, literal_q = qualificador_tardio
        _, pos_p, literal_p = qualificador_inicial

        qualificadores_contracomando[evento.indice][pos_q] = literal_p
        qualificadores_complementares[evento.indice][pos_p] = literal_q

    # ------------------------------------------------------------------
    # 4) Recalcula os pontos perigosos para a apresentação didática.
    #
    # A etapa anterior pode trocar um literal entre as categorias
    # "qualificação" e "qualificação complementar" sem alterar a
    # equação final.
    #
    # Por isso, os estados exibidos precisam ser recalculados usando:
    #
    # condição mínima
    # + qualificadores de comando/contracomando
    #
    # mas ainda sem os qualificadores complementares.
    # ------------------------------------------------------------------
    for evento in eventos:
        evento.pontos_perigosos.clear()

        expressao_qualificada = And(
            evento.base,
            *qualificadores_contracomando[
                evento.indice
            ],
        )

        expressao_final_evento = And(
            expressao_qualificada,
            *qualificadores_complementares[
                evento.indice
            ],
        )

        for ponto in pontos:
            saida_deveria_estar_bloqueada = any(
                rotulos[saida][ponto.evento] == "0"
                for saida in evento.saidas
            )

            if not saida_deveria_estar_bloqueada:
                continue

            # Só é um ponto perigoso para apresentação
            # quando a equação qualificada é verdadeira.
            if not _avaliar(
                expressao_qualificada,
                ordem_simbolos,
                ponto.valores,
            ):
                continue

            if (
                ponto.valores
                not in evento.pontos_perigosos
            ):
                evento.pontos_perigosos.append(
                    ponto.valores
                )

        # Verificação de segurança:
        # a expressão final precisa bloquear todos os
        # pontos perigosos encontrados.
        pontos_nao_eliminados = [
            valores
            for valores in evento.pontos_perigosos
            if _avaliar(
                expressao_final_evento,
                ordem_simbolos,
                valores,
            )
        ]

        if pontos_nao_eliminados:
            raise RuntimeError(
                "A qualificação complementar não eliminou "
                "todos os pontos perigosos de "
                f"{evento.saidas}: "
                f"{pontos_nao_eliminados}."
            )

    termos_por_saida: dict[str, list[object]] = {
        saida: [] for saida in _todas_saidas(eventos)
    }

    for evento in eventos:
        evento.qualificadores_contracomando = list(
            qualificadores_contracomando[evento.indice]
        )
        evento.qualificadores_complementares = list(
            qualificadores_complementares[evento.indice]
        )

        # fatores_ordenados já contém apenas a condição mínima.
        evento.fatores_ordenados.extend(
            evento.qualificadores_contracomando
        )
        evento.fatores_ordenados.extend(
            evento.qualificadores_complementares
        )
        evento.termo = And(*evento.fatores_ordenados)

        for saida in evento.saidas:
            termos_por_saida[saida].append(evento.termo)

    expressoes: dict[str, object] = {}

    for saida, termos in termos_por_saida.items():
        expressoes[saida] = termos[0] if len(termos) == 1 else Or(*termos)

    return expressoes


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


def _validar(
    eventos: list[Evento],
    memorias: tuple[str, ...],
    caminhos: dict[int, tuple[tuple[int, ...], ...]],
    rotulos: dict[str, list[str]],
    pontos: list[Ponto],
    expressoes: dict[str, object],
    ordem_simbolos: list[Symbol],
) -> tuple[str, ...]:
    for evento in eventos:
        valores = tuple(evento.fisico) + tuple(evento.codigo) + (1,)

        if not _avaliar(evento.termo, ordem_simbolos, valores):
            raise RuntimeError(
                f"O evento {evento.saidas} não dispara no ponto correto."
            )

    for ponto in pontos:
        for saida, expressao in expressoes.items():
            esperado = rotulos[saida][ponto.evento]
            obtido = _avaliar(expressao, ordem_simbolos, ponto.valores)

            if esperado == "1" and not obtido:
                raise RuntimeError(
                    f"{saida} deveria estar ativo no ponto {ponto.valores}."
                )

            if esperado == "0" and obtido:
                raise RuntimeError(
                    f"Ponto perigoso: {saida} ficou ativo no ponto "
                    f"{ponto.valores}."
                )

    dispositivos = {saida[:-1] for saida in expressoes}

    for dispositivo in dispositivos:
        mais = expressoes.get(f"{dispositivo}+", false)
        menos = expressoes.get(f"{dispositivo}-", false)

        for ponto in pontos:
            if (
                _avaliar(mais, ordem_simbolos, ponto.valores)
                and _avaliar(menos, ordem_simbolos, ponto.valores)
            ):
                raise RuntimeError(
                    f"Conflito simultâneo entre {dispositivo}+ e "
                    f"{dispositivo}-."
                )

    for caminho in caminhos.values():
        for antigo, novo in zip(caminho, caminho[1:]):
            distancia = sum(a != b for a, b in zip(antigo, novo))
            if distancia != 1:
                raise RuntimeError(
                    "Mais de uma memória muda na mesma transição."
                )

    for memoria in memorias:
        set_expr = expressoes.get(f"{memoria}+", false)
        reset_expr = expressoes.get(f"{memoria}-", false)

        for ponto in pontos:
            if (
                _avaliar(set_expr, ordem_simbolos, ponto.valores)
                and _avaliar(reset_expr, ordem_simbolos, ponto.valores)
            ):
                raise RuntimeError(
                    f"SET e RESET simultâneos na memória {memoria}."
                )

    return (
        "a colocação das memórias segue a sequência de SET/RESET do método",
        "cada passo usa como base o sinal produzido pelo passo anterior",
        "comandos e contracomandos foram qualificados progressivamente",
        "nenhum ponto perigoso foi encontrado nos estados alcançáveis",
        "nenhum comando e contracomando ficam ativos simultaneamente",
        "somente uma memória muda em cada evento de memória",
        "equações de SET, RESET e retenção das memórias são coerentes",
    )


# ---------------------------------------------------------------------------
# Formatação das equações na mesma ordem da construção
# ---------------------------------------------------------------------------


def _formatar_literal(
    literal,
    atuadores: tuple[str, ...],
    memorias: tuple[str, ...],
) -> str:
    """Formata os literais na notação utilizada na apostila.

    Sensores avançados são escritos como a1, b1, ...; memórias acionadas são
    escritas simplesmente como x, y, ...; estados negados usam a0, x0, etc.
    """
    conjunto_atuadores = set(atuadores)
    conjunto_memorias = set(memorias)

    if isinstance(literal, Symbol):
        nome = str(literal)
        if nome == "S":
            return "S"
        if nome in conjunto_memorias:
            return nome.lower()
        if nome in conjunto_atuadores:
            return f"{nome.lower()}1"
        return nome

    if literal.func is Not and isinstance(literal.args[0], Symbol):
        nome = str(literal.args[0])
        if nome == "S":
            return "S0"
        if nome in conjunto_memorias or nome in conjunto_atuadores:
            return f"{nome.lower()}0"
        return f"{nome}0"

    return str(literal)


def _formatar_termo_evento(
    evento: Evento,
    atuadores: tuple[str, ...],
    memorias: tuple[str, ...],
) -> str:
    if not evento.fatores_ordenados:
        return "1"

    return ".".join(
        _formatar_literal(fator, atuadores, memorias)
        for fator in evento.fatores_ordenados
    )


def _equacoes_textuais(
    eventos: list[Evento],
    atuadores: tuple[str, ...],
    memorias: tuple[str, ...],
) -> dict[str, str]:
    termos: dict[str, list[str]] = {
        saida: [] for saida in _todas_saidas(eventos)
    }

    for evento in eventos:
        texto = _formatar_termo_evento(evento, atuadores, memorias)
        for saida in evento.saidas:
            if texto not in termos[saida]:
                termos[saida].append(texto)

    return {
        saida: " + ".join(parcelas)
        for saida, parcelas in termos.items()
    }


def _equacoes_completas_memorias(
    memorias: tuple[str, ...],
    equacoes: dict[str, str],
) -> dict[str, str]:
    completas: dict[str, str] = {}

    for memoria in memorias:
        set_texto = equacoes.get(f"{memoria}+", "0")
        reset_texto = equacoes.get(f"{memoria}-", "0")
        estado = memoria.lower()

        if reset_texto == "0":
            completas[memoria] = f"{set_texto} + {estado}"
        else:
            completas[memoria] = (
                f"({set_texto} + {estado}).¬({reset_texto})"
            )

    return completas


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------


def resolver(
    sequencia,
    estado_inicial: Optional[Mapping[str, int]] = None,
    *,
    ciclo_continuo: bool = False,
) -> Resultado:
    atuadores, inicial, etapas = construir_etapas(sequencia, estado_inicial)

    fecha_ciclo = etapas[-1].depois == etapas[0].antes

    if ciclo_continuo and not fecha_ciclo:
        raise ValueError(
            "Em ciclo contínuo, o estado final deve ser igual ao estado inicial."
        )

    # Mesmo em ciclo único, as memórias são restauradas ao final, preparando
    # o circuito para uma nova partida, como nos exemplos da apostila.
    ciclo_logico = True

    rotulos_base = _rotulos_originais(etapas, ciclo_logico)
    arestas = _arestas_conflito(etapas, rotulos_base)

    clique = _maior_clique_aproximada(len(etapas), arestas)
    minimo_bits = 0
    while (1 << minimo_bits) < clique:
        minimo_bits += 1

    solucao = None
    erros: list[str] = []
    total_candidatos_testados = 0

    maximo_memorias = min(_LIMITE_MEMORIAS, max(0, len(etapas) - 1))

    for quantidade_memorias in range(minimo_bits, maximo_memorias + 1):
        candidatos = _buscar_caminhos_memorias(
            etapas,
            arestas,
            quantidade_memorias,
            limite=_LIMITE_ALTERNATIVAS,
        )

        if not candidatos:
            continue

        candidatos = tuple(
            sorted(
                candidatos,
                key=lambda item: _chave_metodo_candidato(item, arestas),
            )
        )

        memorias = _nomes_memorias(quantidade_memorias, atuadores)

        for candidato in candidatos:
            total_candidatos_testados += 1

            # Cópia das etapas porque cada candidato recebe códigos próprios.
            etapas_teste = [
                Etapa(
                    indice=etapa.indice,
                    acoes=etapa.acoes,
                    antes=etapa.antes,
                    depois=etapa.depois,
                    intermediarios=etapa.intermediarios,
                )
                for etapa in etapas
            ]

            try:
                caminhos = _atribuir_candidato(
                    etapas_teste,
                    candidato,
                    quantidade_memorias,
                )

                ordem_nomes = list(atuadores) + list(memorias) + ["S"]
                ordem_simbolos = [
                    Symbol(nome, boolean=True)
                    for nome in ordem_nomes
                ]
                simbolos = dict(zip(ordem_nomes, ordem_simbolos))

                eventos = _construir_eventos(
                    etapas_teste,
                    memorias,
                    caminhos,
                    simbolos,
                )
                rotulos = _rotulos_eventos(eventos, ciclo_logico)
                pontos = _pontos_alcancaveis(eventos)

                expressoes = _qualificar_progressivamente(
                    eventos,
                    rotulos,
                    pontos,
                    ordem_nomes,
                    ordem_simbolos,
                    len(atuadores),
                    arestas,
                )

                validacoes = _validar(
                    eventos,
                    memorias,
                    caminhos,
                    rotulos,
                    pontos,
                    expressoes,
                    ordem_simbolos,
                )
            except RuntimeError as erro:
                erros.append(str(erro))
                continue

            equacoes = _equacoes_textuais(
                eventos,
                atuadores,
                memorias,
            )
            equacoes_memorias = _equacoes_completas_memorias(
                memorias,
                equacoes,
            )

            solucao = (
                etapas_teste,
                tuple(eventos),
                memorias,
                expressoes,
                equacoes,
                equacoes_memorias,
                validacoes,
                candidato,
            )
            break

        if solucao is not None:
            break

    if solucao is None:
        detalhe = f" Último erro: {erros[-1]}" if erros else ""
        raise RuntimeError(
            "Não foi encontrada uma colocação válida das memórias dentro "
            f"do limite de busca.{detalhe}"
        )

    (
        etapas_finais,
        eventos_finais,
        memorias,
        expressoes,
        equacoes,
        equacoes_memorias,
        validacoes,
        candidato,
    ) = solucao

    observacoes = [
        f"Quantidade encontrada: {len(memorias)} memória(s).",
        f"Foram testadas {total_candidatos_testados} colocações de memória.",
        "As expressões são mantidas na ordem de qualificação da apostila; "
        "não é feita uma minimização algébrica global que altere o método.",
    ]

    if ciclo_continuo:
        observacoes.append(
            "No ciclo contínuo, mantenha S acionado para repetição automática "
            "ou use uma memória externa de ciclo."
        )

    return Resultado(
        atuadores=atuadores,
        estado_inicial=inicial,
        etapas=etapas_finais,
        eventos=eventos_finais,
        memorias=memorias,
        expressoes=expressoes,
        equacoes=equacoes,
        equacoes_memorias=equacoes_memorias,
        validacoes=validacoes,
        observacoes=tuple(observacoes),
    )


# ---------------------------------------------------------------------------
# Regressões dos exemplos documentados
# ---------------------------------------------------------------------------


def validar_exemplos_referencia() -> tuple[str, ...]:
    """Executa regressões dos exemplos explícitos da apostila.

    A função não é chamada durante a importação do módulo. Ela pode ser
    executada manualmente após futuras alterações no algoritmo para garantir
    que colocação das memórias, qualificação, pontos perigosos e equações não
    se afastaram dos resultados documentados.
    """

    casos = (
        (
            "A+, B+, B-, A-",
            ("A+", "B+", "X+", "B-", "A-", "X-"),
            {
                "A+": "S.x0",
                "B+": "a1.x0",
                "X+": "b1",
                "B-": "x",
                "A-": "b0.x",
                "X-": "a0",
            },
        ),
        (
            "A+, A-, B+, B-, C+, C-",
            (
                "A+", "X+", "A-", "B+", "Y+",
                "B-", "X-", "C+", "Y-", "C-",
            ),
            {
                "A+": "S.c0.x0.y0",
                "X+": "a1",
                "A-": "x",
                "B+": "a0.x.y0",
                "Y+": "b1",
                "B-": "y",
                "X-": "b0.y",
                "C+": "x0.y",
                "Y-": "c1",
                "C-": "y0",
            },
        ),
        (
            "A+, B+, B-, C+, B+, B-, C-, A-",
            (
                "A+", "B+", "X+", "B-", "C+", "B+",
                "X-", "B-", "Y+", "C-", "A-", "Y-",
            ),
            {
                "A+": "S.y0",
                "B+": "a1.x0.c0.y0 + c1.x",
                "X+": "b1.c0",
                "B-": "x.c0 + x0.c1",
                "C+": "b0.y0.x",
                "X-": "b1.c1",
                "Y+": "b0.c1.x0",
                "C-": "y",
                "A-": "c0.y",
                "Y-": "a0",
            },
        ),
    )

    mensagens: list[str] = []

    for sequencia, eventos_esperados, equacoes_esperadas in casos:
        resultado = resolver(sequencia)
        eventos_obtidos = tuple(
            evento.saidas[0]
            if len(evento.saidas) == 1
            else " ∥ ".join(evento.saidas)
            for evento in resultado.eventos
        )

        if eventos_obtidos != eventos_esperados:
            raise AssertionError(
                "A sequência expandida divergiu da referência para "
                f"{sequencia!r}: {eventos_obtidos}."
            )

        if resultado.equacoes != equacoes_esperadas:
            raise AssertionError(
                "As equações divergiram da referência para "
                f"{sequencia!r}: {resultado.equacoes}."
            )

        # Confirma que cada ponto mostrado realmente satisfaz
        # a equação qualificada e é eliminado pela equação final.
        nomes_teste = [
            *resultado.atuadores,
            *resultado.memorias,
            "S",
        ]

        simbolos_teste = [
            Symbol(nome)
            for nome in nomes_teste
        ]

        for evento in resultado.eventos:
            expressao_qualificada = And(
                evento.base,
                *evento.qualificadores_contracomando,
            )

            expressao_final_evento = And(
                expressao_qualificada,
                *evento.qualificadores_complementares,
            )

            for valores in evento.pontos_perigosos:
                if not _avaliar(
                    expressao_qualificada,
                    simbolos_teste,
                    valores,
                ):
                    raise AssertionError(
                        "Foi exibido um ponto perigoso que "
                        "não satisfaz a equação qualificada "
                        f"de {evento.saidas}: {valores}."
                    )

                if _avaliar(
                    expressao_final_evento,
                    simbolos_teste,
                    valores,
                ):
                    raise AssertionError(
                        "O qualificador complementar não "
                        "eliminou o ponto perigoso de "
                        f"{evento.saidas}: {valores}."
                    )

        mensagens.append(
            f"Referência validada: {sequencia}"
        )

    # Verifica também o detalhamento didático do exemplo com dois grupos
    # de memória, no qual x é qualificador e y0 é ponto perigoso de B+.
    resultado = resolver("A+, A-, B+, B-, C+, C-")
    evento_b_mais = next(
        evento
        for evento in resultado.eventos
        if evento.saidas == ("B+",)
    )
    qualificadores = tuple(
        _formatar_literal(
            literal,
            resultado.atuadores,
            resultado.memorias,
        )
        for literal in evento_b_mais.qualificadores_contracomando
    )
    complementares = tuple(
        _formatar_literal(
            literal,
            resultado.atuadores,
            resultado.memorias,
        )
        for literal in evento_b_mais.qualificadores_complementares
    )

    if qualificadores != ("x",) or complementares != ("y0",):
        raise AssertionError(
            "A separação didática de B+ deveria ser x na qualificação "
            "e y0 nos pontos perigosos."
        )

    mensagens.append("Classificação didática dos qualificadores validada.")
    return tuple(mensagens)


# ---------------------------------------------------------------------------
# Utilidades de exibição
# ---------------------------------------------------------------------------


def _estado_texto(estado: tuple[int, ...], atuadores: tuple[str, ...]) -> str:
    return " ".join(
        f"{atuador.lower()}{valor}"
        for atuador, valor in zip(atuadores, estado)
    )


def _codigo_texto(codigo: tuple[int, ...], memorias: tuple[str, ...]) -> str:
    return " ".join(
        f"{memoria.lower()}{valor}"
        for memoria, valor in zip(memorias, codigo)
    )


if __name__ == "__main__":
    for mensagem in validar_exemplos_referencia():
        print(f"✓ {mensagem}")