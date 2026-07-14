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
    A+, B+ até b1, C+, B+ até b2, C-, B+ até b3, A-, B- até b0
    A+, B+, [C+, D+, C-, D-] enquanto e=0, A-, B-
    A+, B+, (C-, D+), (D-, A-)

Dependência:

    pip install sympy
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache
from itertools import combinations, permutations, product
import re
from typing import Any, Mapping, Optional

from sympy import And, Not, Or, Symbol, false, true

from src.modelos import AtuadorConfig, EtapaSequencial, Movimento, ProjetoSequencial
from src.parser_entrada import interpretar_entrada


VERSAO = "engine6-final-regressao-11.0"

# Quantidade de alternativas mantidas pela busca para cada estado dinâmico.
# O aumento deste valor torna a busca mais abrangente, porém mais lenta.
_LIMITE_ALTERNATIVAS = 1200
_LIMITE_MEMORIAS = 8


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextoFisico:
    """Descrição das variáveis físicas usadas pelo motor lógico.

    Atuadores com exatamente duas posições continuam representados por uma
    única variável binária, preservando as equações tradicionais a0/a1.
    Atuadores com três ou mais posições são representados pelos próprios
    sensores em codificação one-hot, por exemplo b0, b1, b2 e b3.
    """

    atuadores: tuple[str, ...]
    configuracoes: dict[str, AtuadorConfig]
    variaveis: tuple[str, ...]
    variaveis_por_atuador: dict[str, tuple[str, ...]]
    variavel_para_atuador: dict[str, str]
    rotulos_binarios: dict[str, tuple[str, str]]
    sensores_one_hot: frozenset[str]
    entradas_externas: tuple[str, ...] = ()
    loops: tuple[Any, ...] = ()

    @property
    def quantidade_variaveis(self) -> int:
        return len(self.variaveis)

    def sensor_ativo(self, estado: tuple[int, ...], atuador: str) -> str:
        config = self.configuracoes[atuador]
        variaveis = self.variaveis_por_atuador[atuador]
        indices = {nome: i for i, nome in enumerate(self.variaveis)}

        if len(variaveis) == 1:
            valor = estado[indices[variaveis[0]]]
            return config.sensores[int(valor)]

        for sensor in variaveis:
            if estado[indices[sensor]]:
                return sensor

        raise RuntimeError(
            f"O estado do atuador {atuador} não possui sensor ativo."
        )


@dataclass(frozen=True)
class ComandoLogico:
    chave: str
    fisica: str
    dispositivo: str
    sentido: str
    rotulo: str
    sensor_destino: str | None = None


@dataclass(frozen=True)
class Acao:
    atuador: str
    sentido: str
    sensor_origem: str = ""
    sensor_destino: str = ""
    alteracoes: tuple[tuple[int, int], ...] = ()
    conclusao: tuple[tuple[str, int], ...] = ()
    sensores_percorridos: tuple[str, ...] = ()
    comando: ComandoLogico | None = None
    requer_parada: bool = False

    @property
    def destino(self):
        # Mantido por compatibilidade com versões anteriores.
        if self.sensor_destino:
            return self.sensor_destino
        return 1 if self.sentido == "+" else 0

    @property
    def nome(self) -> str:
        if self.comando is not None:
            return self.comando.rotulo
        return f"{self.atuador}{self.sentido}"

    @property
    def saida_fisica(self) -> str:
        return f"{self.atuador}{self.sentido}"


@dataclass
class Etapa:
    indice: int
    acoes: tuple[Acao, ...]
    antes: tuple[int, ...]
    depois: tuple[int, ...]
    intermediarios: tuple[tuple[int, ...], ...]
    intermediarios_conflito: tuple[tuple[int, ...], ...] = ()
    condicoes_externas: tuple[tuple[str, int], ...] = ()
    restricoes_externas: tuple[tuple[str, int], ...] = ()
    fechamento_loop: tuple[tuple[str, int], ...] = ()
    fase: int = 0
    codigo: tuple[int, ...] = ()


@dataclass
class Evento:
    indice: int
    tipo: str  # "atuador" ou "memoria"
    comandos: tuple[ComandoLogico, ...]
    fisico: tuple[int, ...]
    codigo: tuple[int, ...]
    etapa_indice: Optional[int] = None
    acoes: tuple[Acao, ...] = ()
    intermediarios: tuple[tuple[int, ...], ...] = ()
    condicoes_externas: tuple[tuple[str, int], ...] = ()
    restricoes_externas: tuple[tuple[str, int], ...] = ()
    fechamento_loop: tuple[tuple[str, int], ...] = ()

    # Condição mínima produzida pelo passo anterior.
    base: object = true

    # Fatores de parada por comando lógico. Em uma etapa simultânea, cada
    # saída pode terminar em um instante diferente sem interromper as demais.
    qualificadores_parada: list[object] = field(default_factory=list)
    qualificadores_parada_por_comando: dict[str, list[object]] = field(
        default_factory=dict
    )

    # Equação final comum e equações finais individuais por comando.
    termo: object = true
    termos_por_comando: dict[str, object] = field(default_factory=dict)

    # Todos os fatores na ordem em que aparecem na equação final.
    fatores_ordenados: list[object] = field(default_factory=list)
    fatores_por_comando: dict[str, list[object]] = field(default_factory=dict)

    # Fatores acrescentados para diferenciar comando e contracomando.
    qualificadores_contracomando: list[object] = field(default_factory=list)

    # Fatores acrescentados para eliminar pontos perigosos.
    qualificadores_complementares: list[object] = field(default_factory=list)

    # Estados nos quais a equação qualificada poderia disparar indevidamente.
    pontos_perigosos: list[tuple[int, ...]] = field(default_factory=list)

    @property
    def saidas(self) -> tuple[str, ...]:
        return tuple(comando.rotulo for comando in self.comandos)

    @property
    def chaves_saidas(self) -> tuple[str, ...]:
        return tuple(comando.chave for comando in self.comandos)

    @property
    def saidas_fisicas(self) -> tuple[str, ...]:
        return tuple(comando.fisica for comando in self.comandos)


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
    estado_inicial: dict[str, str]
    etapas: list[Etapa]
    eventos: tuple[Evento, ...]
    memorias: tuple[str, ...]

    # Equações agregadas pelas saídas físicas A+, B+, ...
    expressoes: dict[str, object]
    equacoes: dict[str, str]

    # Equações por comando lógico. Em atuadores multiposição podem aparecer
    # B+(1), B+(2), B+(3), além da equação física agregada B+.
    expressoes_comandos: dict[str, object]
    equacoes_comandos: dict[str, str]

    equacoes_memorias: dict[str, str]
    validacoes: tuple[str, ...]
    contexto_fisico: ContextoFisico
    observacoes: tuple[str, ...] = ()

    @property
    def variaveis_fisicas(self) -> tuple[str, ...]:
        return self.contexto_fisico.variaveis

    @property
    def sensores_por_atuador(self) -> dict[str, tuple[str, ...]]:
        return {
            nome: config.sensores
            for nome, config in self.contexto_fisico.configuracoes.items()
        }

    @property
    def entradas_externas(self) -> tuple[str, ...]:
        return self.contexto_fisico.entradas_externas

    @property
    def loops(self) -> tuple[Any, ...]:
        return self.contexto_fisico.loops

    def resumo(self) -> str:
        linhas = ["ETAPAS E FASES"]

        for etapa in self.etapas:
            acoes = " e ".join(acao.nome for acao in etapa.acoes)
            antes = _estado_texto(etapa.antes, self.contexto_fisico)
            depois = _estado_texto(etapa.depois, self.contexto_fisico)
            codigo = _codigo_texto(etapa.codigo, self.memorias)
            sufixo = f" {codigo}" if codigo else ""
            linhas.append(
                f"{etapa.indice + 1:>2}: {acoes:<20} "
                f"{antes} -> {depois}  F{etapa.fase}{sufixo}"
            )

        linhas += [
            "\nMEMÓRIAS",
            ", ".join(self.memorias) if self.memorias else "Nenhuma",
            "\nEQUAÇÕES DOS COMANDOS",
        ]
        linhas += [
            f"{saida} = {equacao}"
            for saida, equacao in self.equacoes_comandos.items()
        ]

        if self.equacoes != self.equacoes_comandos:
            linhas.append("\nEQUAÇÕES FÍSICAS AGREGADAS")
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
    """Compatibilidade com a leitura antiga de A+, B-, (C+, D-)."""
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
        etapas.append(tuple(acoes))
    return etapas


def _entrada_para_texto(entrada) -> str:
    if isinstance(entrada, str):
        return entrada
    partes: list[str] = []
    for item in entrada:
        if isinstance(item, str):
            partes.append(item)
        else:
            partes.append("(" + ", ".join(str(x) for x in item) + ")")
    return ", ".join(partes)


def _normalizar_projeto(
    sequencia,
    estado_inicial: Optional[Mapping[str, int | str]] = None,
) -> ProjetoSequencial:
    if isinstance(sequencia, ProjetoSequencial):
        projeto = sequencia
    else:
        projeto = interpretar_entrada(_entrada_para_texto(sequencia))

    if estado_inicial:
        configs: dict[str, AtuadorConfig] = {}
        for nome, config in projeto.atuadores.items():
            valor = next(
                (
                    v for chave, v in estado_inicial.items()
                    if str(chave).casefold() == nome.casefold()
                ),
                config.sensor_inicial,
            )

            if isinstance(valor, str):
                sensor = config.sensor_canonico(valor)
            else:
                indice = int(valor)
                if not 0 <= indice < len(config.sensores):
                    raise ValueError(
                        f"A posição inicial {valor} é inválida para {nome}."
                    )
                sensor = config.sensores[indice]

            configs[nome] = replace(config, sensor_inicial=sensor)

        projeto = ProjetoSequencial(
            atuadores=configs,
            etapas=list(projeto.etapas),
            loops=list(projeto.loops),
            sinal_partida=projeto.sinal_partida,
            entradas_externas=list(projeto.entradas_externas),
        )

    projeto.validar()
    return projeto


def _criar_contexto(projeto: ProjetoSequencial) -> ContextoFisico:
    atuadores = tuple(config.nome for config in projeto.atuadores.values())
    configuracoes = {config.nome: config for config in projeto.atuadores.values()}
    variaveis: list[str] = []
    variaveis_por_atuador: dict[str, tuple[str, ...]] = {}
    variavel_para_atuador: dict[str, str] = {}
    rotulos_binarios: dict[str, tuple[str, str]] = {}
    sensores_one_hot: set[str] = set()

    for config in projeto.atuadores.values():
        if len(config.sensores) == 2:
            variavel = config.nome
            variaveis.append(variavel)
            variaveis_por_atuador[config.nome] = (variavel,)
            variavel_para_atuador[variavel] = config.nome
            rotulos_binarios[variavel] = (
                config.sensores[0],
                config.sensores[1],
            )
        else:
            nomes = tuple(config.sensores)
            variaveis.extend(nomes)
            variaveis_por_atuador[config.nome] = nomes
            for sensor in nomes:
                variavel_para_atuador[sensor] = config.nome
                sensores_one_hot.add(sensor)

    return ContextoFisico(
        atuadores=atuadores,
        configuracoes=configuracoes,
        variaveis=tuple(variaveis),
        variaveis_por_atuador=variaveis_por_atuador,
        variavel_para_atuador=variavel_para_atuador,
        rotulos_binarios=rotulos_binarios,
        sensores_one_hot=frozenset(sensores_one_hot),
        entradas_externas=tuple(projeto.entradas_externas),
        loops=tuple(projeto.loops),
    )


def _registro_comandos(
    projeto: ProjetoSequencial,
) -> dict[tuple[str, str, str], ComandoLogico]:
    destinos_por_saida: dict[str, list[str]] = {}
    for etapa in projeto.etapas:
        for movimento in etapa.movimentos:
            saida = f"{movimento.atuador}{movimento.sentido}"
            destinos = destinos_por_saida.setdefault(saida, [])
            if movimento.sensor_destino not in destinos:
                destinos.append(movimento.sensor_destino)

    registro: dict[tuple[str, str, str], ComandoLogico] = {}
    for saida, destinos in destinos_por_saida.items():
        atuador, sentido = saida[:-1], saida[-1]
        multiplo = len(destinos) > 1
        for numero, sensor in enumerate(destinos, start=1):
            chave = saida if not multiplo else f"{saida}@{sensor}"
            rotulo = saida if not multiplo else f"{saida}({numero})"
            registro[(atuador, sentido, sensor)] = ComandoLogico(
                chave=chave,
                fisica=saida,
                dispositivo=atuador,
                sentido=sentido,
                rotulo=rotulo,
                sensor_destino=sensor,
            )
    return registro


def _ha_mesmo_sentido_antes_do_oposto(
    etapas: list[EtapaSequencial],
    indice_etapa: int,
    atuador: str,
    sentido: str,
) -> bool:
    for deslocamento, etapa in enumerate(
        etapas[indice_etapa + 1:],
        start=1,
    ):
        movimento = next(
            (m for m in etapa.movimentos if m.atuador == atuador),
            None,
        )
        if movimento is None:
            continue
        # Há uma região de parada quando o mesmo sentido volta a ocorrer ou
        # quando existe ao menos uma etapa intermediária antes do próximo
        # comando desse atuador.
        return movimento.sentido == sentido or deslocamento > 1
    return False


def _acao_completa(
    movimento: Movimento,
    sensor_origem: str,
    contexto: ContextoFisico,
    registro: dict[tuple[str, str, str], ComandoLogico],
    requer_parada: bool,
) -> Acao:
    config = contexto.configuracoes[movimento.atuador]
    indices = {nome: i for i, nome in enumerate(contexto.variaveis)}
    variaveis = contexto.variaveis_por_atuador[movimento.atuador]

    sensores_percorridos: tuple[str, ...] = ()

    if len(variaveis) == 1:
        variavel = variaveis[0]
        valor = config.indice_sensor(movimento.sensor_destino)
        alteracoes = ((indices[variavel], valor),)
        conclusao = ((variavel, valor),)
    else:
        alteracoes = tuple(
            (indices[sensor], int(sensor == movimento.sensor_destino))
            for sensor in variaveis
        )
        conclusao = ((movimento.sensor_destino, 1),)

        indice_origem = config.indice_sensor(sensor_origem)
        indice_destino = config.indice_sensor(movimento.sensor_destino)
        passo = 1 if indice_destino > indice_origem else -1
        sensores_percorridos = tuple(
            config.sensores[indice]
            for indice in range(
                indice_origem + passo,
                indice_destino,
                passo,
            )
        )

    return Acao(
        atuador=movimento.atuador,
        sentido=movimento.sentido,
        sensor_origem=sensor_origem,
        sensor_destino=movimento.sensor_destino,
        alteracoes=alteracoes,
        conclusao=conclusao,
        sensores_percorridos=sensores_percorridos,
        comando=registro[(
            movimento.atuador,
            movimento.sentido,
            movimento.sensor_destino,
        )],
        requer_parada=requer_parada and len(variaveis) > 1,
    )


def _aplicar_acao(estado: tuple[int, ...], acao: Acao) -> tuple[int, ...]:
    novo = list(estado)
    for indice, valor in acao.alteracoes:
        novo[indice] = valor
    return tuple(novo)


def _condicoes_por_etapa(
    projeto: ProjetoSequencial,
) -> tuple[
    dict[int, tuple[tuple[str, int], ...]],
    dict[int, tuple[tuple[str, int], ...]],
]:
    """Retorna condições de habilitação e restrições de alcançabilidade.

    A condição externa entra explicitamente somente nas duas saídas do nó de
    decisão: início do loop (repetir) e primeira etapa após o loop (sair).
    Durante as etapas internas, o valor de repetição é usado apenas para
    descrever os estados alcançáveis, sem ser acrescentado às equações de D+,
    C-, D- etc. Isso reproduz o ciclo interno apresentado no método.
    """

    habilitacao: dict[int, dict[str, int]] = {}
    restricoes: dict[int, dict[str, int]] = {}

    def registrar(
        destino: dict[int, dict[str, int]],
        indice: int,
        sensor: str,
        valor: int,
    ) -> None:
        if not 0 <= indice < len(projeto.etapas):
            return
        por_sensor = destino.setdefault(indice, {})
        anterior = por_sensor.get(sensor)
        if anterior is not None and anterior != valor:
            raise ValueError(
                f"A etapa {indice + 1} recebeu condições incompatíveis "
                f"para a entrada externa {sensor}."
            )
        por_sensor[sensor] = int(valor)

    for loop in projeto.loops:
        registrar(
            habilitacao,
            loop.inicio,
            loop.sensor,
            loop.repetir_quando,
        )
        registrar(
            habilitacao,
            loop.fim + 1,
            loop.sensor,
            loop.sair_quando,
        )

        for indice in range(loop.inicio, loop.fim + 1):
            registrar(
                restricoes,
                indice,
                loop.sensor,
                loop.repetir_quando,
            )

        proximos_inicios = [
            outro.inicio
            for outro in projeto.loops
            if outro.sensor == loop.sensor
            and outro.inicio > loop.fim
        ]
        limite_saida = min(
            proximos_inicios,
            default=len(projeto.etapas),
        )
        for indice in range(loop.fim + 1, limite_saida):
            registrar(
                restricoes,
                indice,
                loop.sensor,
                loop.sair_quando,
            )

    ordem_entradas = {
        nome: indice
        for indice, nome in enumerate(projeto.entradas_externas)
    }

    def finalizar(
        origem: dict[int, dict[str, int]],
    ) -> dict[int, tuple[tuple[str, int], ...]]:
        return {
            indice: tuple(
                sorted(
                    condicoes.items(),
                    key=lambda item: ordem_entradas.get(item[0], 10**9),
                )
            )
            for indice, condicoes in origem.items()
        }

    return finalizar(habilitacao), finalizar(restricoes)


def _condicoes_mutuamente_exclusivas(
    primeira: tuple[tuple[str, int], ...],
    segunda: tuple[tuple[str, int], ...],
) -> bool:
    mapa_primeira = dict(primeira)
    mapa_segunda = dict(segunda)
    return any(
        sensor in mapa_segunda and mapa_segunda[sensor] != valor
        for sensor, valor in mapa_primeira.items()
    )


def _construir_etapas_contexto(
    sequencia,
    estado_inicial: Optional[Mapping[str, int | str]] = None,
) -> tuple[ContextoFisico, dict[str, str], list[Etapa]]:
    projeto = _normalizar_projeto(sequencia, estado_inicial)
    contexto = _criar_contexto(projeto)
    registro = _registro_comandos(projeto)
    indices = {nome: i for i, nome in enumerate(contexto.variaveis)}
    (
        condicoes_por_etapa,
        restricoes_por_etapa,
    ) = _condicoes_por_etapa(projeto)

    inicial_sensores = {
        config.nome: config.sensor_inicial
        for config in projeto.atuadores.values()
    }
    valores = [0] * len(contexto.variaveis)
    for config in projeto.atuadores.values():
        variaveis = contexto.variaveis_por_atuador[config.nome]
        if len(variaveis) == 1:
            valores[indices[variaveis[0]]] = config.indice_sensor(
                config.sensor_inicial
            )
        else:
            for sensor in variaveis:
                valores[indices[sensor]] = int(sensor == config.sensor_inicial)

    estado = tuple(valores)
    etapas: list[Etapa] = []

    for indice_etapa, etapa_modelo in enumerate(projeto.etapas):
        antes = estado
        acoes: list[Acao] = []

        for movimento in etapa_modelo.movimentos:
            sensor_origem = contexto.sensor_ativo(antes, movimento.atuador)
            acao = _acao_completa(
                movimento,
                sensor_origem,
                contexto,
                registro,
                _ha_mesmo_sentido_antes_do_oposto(
                    projeto.etapas,
                    indice_etapa,
                    movimento.atuador,
                    movimento.sentido,
                ),
            )
            acoes.append(acao)

        depois = antes
        for acao in acoes:
            depois = _aplicar_acao(depois, acao)

        # Estados fisicamente alcançáveis durante a etapa. Para atuadores
        # multiposição, também entram as posições atravessadas entre origem e
        # destino. Em movimentos simultâneos são consideradas todas as ordens
        # possíveis de avanço/conclusão, exceto o estado inicial e o estado em
        # que todas as ações já terminaram.
        progressos_por_acao: list[list[tuple[int, ...]]] = []
        for acao in acoes:
            progressos = [antes]
            if acao.sensores_percorridos:
                variaveis_atuador = contexto.variaveis_por_atuador[acao.atuador]
                for sensor in acao.sensores_percorridos:
                    parcial = list(antes)
                    for variavel in variaveis_atuador:
                        parcial[indices[variavel]] = int(variavel == sensor)
                    progressos.append(tuple(parcial))
            progressos.append(_aplicar_acao(antes, acao))
            progressos_por_acao.append(progressos)

        intermediarios: set[tuple[int, ...]] = set()
        for escolhas in product(*progressos_por_acao):
            parcial = list(antes)
            for acao, estado_acao in zip(acoes, escolhas):
                for indice_variavel, valor in acao.alteracoes:
                    parcial[indice_variavel] = estado_acao[indice_variavel]
            estado_parcial = tuple(parcial)
            if estado_parcial not in {antes, depois}:
                intermediarios.add(estado_parcial)

        intermediarios_conflito: set[tuple[int, ...]] = set()
        for quantidade in range(1, len(acoes)):
            for concluidas in combinations(range(len(acoes)), quantidade):
                parcial = antes
                for k in concluidas:
                    parcial = _aplicar_acao(parcial, acoes[k])
                intermediarios_conflito.add(parcial)

        etapas.append(
            Etapa(
                indice=indice_etapa,
                acoes=tuple(acoes),
                antes=antes,
                depois=depois,
                intermediarios=tuple(sorted(intermediarios)),
                intermediarios_conflito=tuple(
                    sorted(intermediarios_conflito)
                ),
                condicoes_externas=condicoes_por_etapa.get(
                    indice_etapa,
                    (),
                ),
                restricoes_externas=restricoes_por_etapa.get(
                    indice_etapa,
                    (),
                ),
            )
        )
        estado = depois

    # A saída de um loop deve confirmar a conclusão da última etapa física do
    # ciclo mesmo quando um evento de memória é inserido entre o retorno dos
    # atuadores e a decisão de saída.
    for loop in projeto.loops:
        indice_saida = loop.fim + 1
        if indice_saida >= len(etapas):
            continue
        fechamento: list[tuple[str, int]] = []
        for acao in etapas[loop.fim].acoes:
            for fator in acao.conclusao:
                if fator not in fechamento:
                    fechamento.append(fator)
        etapas[indice_saida].fechamento_loop = tuple(fechamento)

    return contexto, inicial_sensores, etapas


def construir_etapas(
    sequencia,
    estado_inicial: Optional[Mapping[str, int | str]] = None,
) -> tuple[tuple[str, ...], dict[str, str], list[Etapa]]:
    """API histórica; o contexto completo é usado internamente por resolver."""
    contexto, inicial, etapas = _construir_etapas_contexto(
        sequencia, estado_inicial
    )
    return contexto.atuadores, inicial, etapas


# ---------------------------------------------------------------------------
# Conflitos entre conjuntos máximos de sinais
# ---------------------------------------------------------------------------


def _comandos_por_etapa(etapas: list[Etapa]) -> list[tuple[ComandoLogico, ...]]:
    return [
        tuple(
            acao.comando
            for acao in etapa.acoes
            if acao.comando is not None
        )
        for etapa in etapas
    ]


def _comandos_unicos(
    comandos_por_passo: list[tuple[ComandoLogico, ...]],
) -> dict[str, ComandoLogico]:
    resultado: dict[str, ComandoLogico] = {}
    for comandos in comandos_por_passo:
        for comando in comandos:
            resultado.setdefault(comando.chave, comando)
    return resultado


def _comando_dispositivo_no_passo(
    comandos: tuple[ComandoLogico, ...],
    dispositivo: str,
) -> ComandoLogico | None:
    return next(
        (c for c in comandos if c.dispositivo == dispositivo),
        None,
    )


def _vizinho_dispositivo(
    comandos_por_passo: list[tuple[ComandoLogico, ...]],
    indice: int,
    dispositivo: str,
    direcao: int,
    ciclo: bool,
) -> ComandoLogico | None:
    n = len(comandos_por_passo)
    if n == 0:
        return None

    limite = n if ciclo else (n - 1)
    for deslocamento in range(1, limite + 1):
        posicao = indice + direcao * deslocamento
        if ciclo:
            posicao %= n
        elif not 0 <= posicao < n:
            return None

        encontrado = _comando_dispositivo_no_passo(
            comandos_por_passo[posicao],
            dispositivo,
        )
        if encontrado is not None:
            return encontrado
    return None


def _rotulos_comandos(
    comandos_por_passo: list[tuple[ComandoLogico, ...]],
    ciclo: bool,
) -> dict[str, list[str]]:
    """Rótulos 1/0/X por comando lógico.

    Quando um atuador multiposição recebe vários comandos no mesmo sentido,
    os intervalos entre dois avanços (ou dois retornos) são tratados como
    regiões de parada. Após o último comando daquele sentido, o sinal volta a
    ser don't-care até surgir o contracomando, preservando a retenção usual.
    """

    comandos = _comandos_unicos(comandos_por_passo)
    resultado: dict[str, list[str]] = {}

    for chave, comando in comandos.items():
        rotulos: list[str] = []

        for indice, comandos_passo in enumerate(comandos_por_passo):
            chaves_passo = {c.chave for c in comandos_passo}
            fisicas_passo = {c.fisica for c in comandos_passo}

            if chave in chaves_passo:
                rotulos.append("1")
                continue

            if comando.fisica in fisicas_passo:
                # Outra variante do mesmo comando físico está atuando.
                rotulos.append("X")
                continue

            atual_dispositivo = _comando_dispositivo_no_passo(
                comandos_passo,
                comando.dispositivo,
            )
            if atual_dispositivo is not None:
                rotulos.append("0")
                continue

            anterior = _vizinho_dispositivo(
                comandos_por_passo,
                indice,
                comando.dispositivo,
                -1,
                ciclo,
            )
            proximo = _vizinho_dispositivo(
                comandos_por_passo,
                indice,
                comando.dispositivo,
                1,
                ciclo,
            )

            if anterior is None or anterior.sentido != comando.sentido:
                rotulos.append("0")
            elif proximo is not None and proximo.sentido == comando.sentido:
                # Pausa intermediária antes de nova atuação no mesmo sentido.
                rotulos.append("0")
            else:
                # Última atuação no sentido atual: pode permanecer retida.
                rotulos.append("X")

        resultado[chave] = rotulos

    return resultado


def _rotulos_originais(
    etapas: list[Etapa],
    ciclo: bool,
) -> dict[str, list[str]]:
    return _rotulos_comandos(_comandos_por_etapa(etapas), ciclo)


def _arestas_conflito(
    etapas: list[Etapa],
    rotulos: dict[str, list[str]],
) -> set[tuple[int, int]]:
    """Passos com mesmo conjunto máximo e decisões incompatíveis."""
    ativos = [
        set((etapa.antes,) + etapa.intermediarios_conflito)
        for etapa in etapas
    ]
    arestas: set[tuple[int, int]] = set()

    for i, j in combinations(range(len(etapas)), 2):
        if not (ativos[i] & ativos[j]):
            continue

        if _condicoes_mutuamente_exclusivas(
            etapas[i].restricoes_externas,
            etapas[j].restricoes_externas,
        ):
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

    ids_fontes: dict[tuple[tuple[str, str, str], ...], int] = {}
    fontes_etapas: list[int] = []

    for etapa in etapas:
        assinatura = tuple(
            (acao.atuador, acao.sentido, acao.sensor_destino)
            for acao in etapa.acoes
        )
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


def _fatores_conclusao_acoes(
    acoes: tuple[Acao, ...],
    simbolos: dict[str, Symbol],
) -> list[object]:
    fatores: list[object] = []
    for acao in acoes:
        fatores.extend(
            _literal(simbolos[nome], valor)
            for nome, valor in acao.conclusao
        )
    return fatores


def _comando_memoria(nome: str, sentido: str) -> ComandoLogico:
    saida = f"{nome}{sentido}"
    return ComandoLogico(
        chave=saida,
        fisica=saida,
        dispositivo=nome,
        sentido=sentido,
        rotulo=saida,
    )


def _construir_eventos(
    etapas: list[Etapa],
    memorias: tuple[str, ...],
    caminhos: dict[int, tuple[tuple[int, ...], ...]],
    simbolos: dict[str, Symbol],
) -> list[Evento]:
    eventos: list[Evento] = []

    for etapa in etapas:
        comandos = tuple(
            acao.comando
            for acao in etapa.acoes
            if acao.comando is not None
        )
        evento_atuador = Evento(
            indice=len(eventos),
            tipo="atuador",
            comandos=comandos,
            fisico=etapa.antes,
            codigo=etapa.codigo,
            etapa_indice=etapa.indice,
            acoes=etapa.acoes,
            intermediarios=etapa.intermediarios,
            condicoes_externas=etapa.condicoes_externas,
            restricoes_externas=etapa.restricoes_externas,
            fechamento_loop=etapa.fechamento_loop,
        )

        # Cada saída multiposição recebe seu próprio contato de parada. Isso
        # permite que, numa etapa simultânea, uma ação termine sem desligar as
        # demais. O contato pode ser removido mais adiante quando um sensor de
        # origem intermediário já fornece a autointerrupção necessária.
        for acao in etapa.acoes:
            if (
                acao.comando is not None
                and len(acao.alteracoes) > 1
                and acao.requer_parada
            ):
                evento_atuador.qualificadores_parada_por_comando[
                    acao.comando.chave
                ] = [Not(simbolos[acao.sensor_destino])]

        eventos.append(evento_atuador)

        caminho = caminhos[etapa.indice]
        for atual, novo in zip(caminho, caminho[1:]):
            diferentes = [
                i
                for i, (antigo, novo_valor) in enumerate(zip(atual, novo))
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
                    comandos=(_comando_memoria(memorias[bit], sentido),),
                    fisico=etapa.depois,
                    codigo=atual,
                    restricoes_externas=etapa.restricoes_externas,
                )
            )

    if not eventos:
        return eventos

    def fatores_produzidos(evento: Evento) -> list[object]:
        if evento.tipo == "atuador":
            return _fatores_conclusao_acoes(evento.acoes, simbolos)

        comando = evento.comandos[0]
        return [
            _literal(
                simbolos[comando.dispositivo],
                1 if comando.sentido == "+" else 0,
            )
        ]

    for i, evento in enumerate(eventos):
        anterior = eventos[i - 1]
        fatores = fatores_produzidos(anterior)
        if i == 0:
            fatores = [simbolos["S"], *fatores]

        fatores_externos = [
            _literal(simbolos[nome], valor)
            for nome, valor in evento.condicoes_externas
        ]
        fatores_fechamento = [
            _literal(simbolos[nome], valor)
            for nome, valor in evento.fechamento_loop
        ]

        fatores_unicos: list[object] = []
        for fator in [*fatores, *fatores_externos, *fatores_fechamento]:
            if fator not in fatores_unicos:
                fatores_unicos.append(fator)
        fatores = fatores_unicos

        evento.base = And(*fatores) if fatores else true
        evento.fatores_ordenados = list(fatores)

    return eventos


# ---------------------------------------------------------------------------
# Qualificação progressiva como na apostila
# ---------------------------------------------------------------------------


def _comandos_eventos(eventos: list[Evento]) -> dict[str, ComandoLogico]:
    resultado: dict[str, ComandoLogico] = {}
    for evento in eventos:
        for comando in evento.comandos:
            resultado.setdefault(comando.chave, comando)
    return resultado


def _rotulos_eventos(
    eventos: list[Evento],
    ciclo: bool,
) -> dict[str, list[str]]:
    return _rotulos_comandos(
        [evento.comandos for evento in eventos],
        ciclo,
    )


def _pontos_alcancaveis(
    eventos: list[Evento],
    entradas_externas: tuple[str, ...] = (),
) -> list[Ponto]:
    """Gera os conjuntos máximos alcançáveis.

    Entradas externas não associadas a uma decisão são avaliadas nas duas
    possibilidades. Quando um evento pertence a uma ramificação, somente o
    valor que habilita essa rota é usado naquele evento.
    """

    if not entradas_externas:
        ordem_detectada: list[str] = []
        for evento in eventos:
            for nome, _ in evento.restricoes_externas:
                if nome not in ordem_detectada:
                    ordem_detectada.append(nome)
        entradas_externas = tuple(ordem_detectada)

    pontos: list[Ponto] = []

    for evento in eventos:
        estados = (evento.fisico,) + evento.intermediarios
        fixadas = dict(evento.restricoes_externas)
        livres = [
            nome
            for nome in entradas_externas
            if nome not in fixadas
        ]

        combinacoes = product((0, 1), repeat=len(livres))

        for combinacao in combinacoes:
            valores_externos = dict(fixadas)
            valores_externos.update(zip(livres, combinacao))
            externos = tuple(
                int(valores_externos.get(nome, 0))
                for nome in entradas_externas
            )

            for fisico in estados:
                valores = (
                    tuple(fisico)
                    + tuple(evento.codigo)
                    + externos
                    + (1,)
                )
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


def _valores_alvo_evento(
    evento: Evento,
    entradas_externas: tuple[str, ...],
) -> tuple[int, ...]:
    fixadas = dict(evento.restricoes_externas)
    externos = tuple(
        int(fixadas.get(nome, 0))
        for nome in entradas_externas
    )
    return (
        tuple(evento.fisico)
        + tuple(evento.codigo)
        + externos
        + (1,)
    )


def _qualificar_progressivamente(
    eventos: list[Evento],
    rotulos: dict[str, list[str]],
    pontos: list[Ponto],
    ordem_nomes: list[str],
    ordem_simbolos: list[Symbol],
    quantidade_variaveis_fisicas: int,
    quantidade_memorias: int,
    arestas_conflito: set[tuple[int, int]],
    contexto: ContextoFisico,
) -> dict[str, object]:
    """Executa a qualificação progressiva com termos por saída lógica.

    Uma etapa simultânea continua sendo um único passo do método, mas cada
    comando recebe seu próprio contato de parada. Assim, B pode alcançar b1 e
    desligar B+ enquanto C+ permanece ativo até C concluir o mesmo passo.
    """

    alvo = {
        evento.indice: _valores_alvo_evento(
            evento,
            contexto.entradas_externas,
        )
        for evento in eventos
    }
    fatores_base = {
        evento.indice: list(evento.fatores_ordenados)
        for evento in eventos
    }
    inicio_memorias = quantidade_variaveis_fisicas
    fim_memorias = inicio_memorias + quantidade_memorias
    entradas_externas = set(contexto.entradas_externas)
    qualificadores_contracomando = {
        evento.indice: [] for evento in eventos
    }
    qualificadores_complementares = {
        evento.indice: [] for evento in eventos
    }

    def atuador_da_variavel(nome: str) -> str | None:
        if nome in contexto.variavel_para_atuador:
            return contexto.variavel_para_atuador[nome]
        return nome if nome not in contexto.variaveis else None

    def variavel_do_proprio_dispositivo(
        nome: str,
        dispositivos: set[str],
    ) -> bool:
        return atuador_da_variavel(nome) in dispositivos

    def paradas(evento: Evento, chave: str) -> list[object]:
        return list(
            evento.qualificadores_parada_por_comando.get(chave, ())
        )

    def expressao_comando(
        evento: Evento,
        chave: str,
        contra: list[object] | None = None,
        complementar: list[object] | None = None,
    ):
        return And(
            evento.base,
            *paradas(evento, chave),
            *(
                qualificadores_contracomando[evento.indice]
                if contra is None
                else contra
            ),
            *(
                qualificadores_complementares[evento.indice]
                if complementar is None
                else complementar
            ),
        )

    def origens_intermediarias(evento: Evento) -> set[str]:
        preferidas: set[str] = set()
        for acao in evento.acoes:
            variaveis_atuador = contexto.variaveis_por_atuador[acao.atuador]
            if len(variaveis_atuador) <= 1:
                continue
            config = contexto.configuracoes[acao.atuador]
            indice_origem = config.indice_sensor(acao.sensor_origem)
            if 0 < indice_origem < len(config.sensores) - 1:
                preferidas.add(acao.sensor_origem)
        return preferidas

    def transitorio_do_contracomando(
        ponto: Ponto,
        comando: ComandoLogico,
    ) -> bool:
        evento_ponto = eventos[ponto.evento]
        fisico = ponto.valores[:contexto.quantidade_variaveis]
        if fisico not in evento_ponto.intermediarios:
            return False
        return any(
            outro.dispositivo == comando.dispositivo
            and outro.sentido != comando.sentido
            for outro in evento_ponto.comandos
        )

    # 1) Diferencia comando e contracomando.
    for evento in eventos:
        dispositivos_evento = {
            comando.dispositivo for comando in evento.comandos
        }
        origens_preferidas = origens_intermediarias(evento)

        for comando in evento.comandos:
            eventos_opostos = [
                outro
                for outro in eventos
                if any(
                    c.dispositivo == comando.dispositivo
                    and c.sentido != comando.sentido
                    for c in outro.comandos
                )
            ]

            for outro in eventos_opostos:
                expressao_atual = expressao_comando(
                    evento,
                    comando.chave,
                    complementar=[],
                )
                valores_oposto = alvo[outro.indice]

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
                        if nome in entradas_externas:
                            continue

                        proprio = variavel_do_proprio_dispositivo(
                            nome,
                            dispositivos_evento,
                        )
                        if (
                            not permitir_proprios
                            and proprio
                            and nome not in origens_preferidas
                        ):
                            continue
                        if simbolo in simbolos_usados:
                            continue
                        if valores_alvo[indice] == valores_oposto[indice]:
                            continue

                        if (
                            base_oposta
                            and base_oposta[0] == nome
                            and inicio_memorias <= indice < fim_memorias
                        ):
                            prioridade = 0
                        elif nome in origens_preferidas:
                            prioridade = 0
                        elif indice < quantidade_variaveis_fisicas and not proprio:
                            prioridade = 1
                        elif inicio_memorias <= indice < fim_memorias:
                            prioridade = 2
                        elif base_oposta and base_oposta[0] == nome:
                            prioridade = 4
                        elif proprio:
                            prioridade = 6
                        else:
                            prioridade = 5

                        desempate = (
                            -indice
                            if indice < quantidade_variaveis_fisicas
                            else indice
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

                escolhido = min(candidatos)[3]
                if escolhido not in qualificadores_contracomando[evento.indice]:
                    qualificadores_contracomando[evento.indice].append(escolhido)

    # 2) Elimina pontos perigosos. Os qualificadores contextuais continuam
    # comuns à etapa; os contatos de destino são individuais por saída.
    for evento in eventos:
        valores_alvo = alvo[evento.indice]
        dispositivos_evento = {
            comando.dispositivo for comando in evento.comandos
        }

        while True:
            perigosos: list[tuple[Ponto, str]] = []
            for ponto in pontos:
                for comando in evento.comandos:
                    if rotulos[comando.chave][ponto.evento] != "0":
                        continue
                    # O mapa do método não usa a passagem transitória do
                    # próprio atuador sob o contracomando para requalificar o
                    # comando oposto. Outros atuadores continuam sendo
                    # verificados nesses pontos (ex.: C+ ao cruzar b1).
                    if transitorio_do_contracomando(ponto, comando):
                        continue
                    if _avaliar(
                        expressao_comando(evento, comando.chave),
                        ordem_simbolos,
                        ponto.valores,
                    ):
                        perigosos.append((ponto, comando.chave))

            if not perigosos:
                break

            simbolos_usados = set().union(
                *(
                    expressao_comando(evento, comando.chave).free_symbols
                    for comando in evento.comandos
                )
            )
            melhor = None

            for permitir_proprios in (False, True):
                melhor = None
                for indice, nome in enumerate(ordem_nomes[:-1]):
                    simbolo = ordem_simbolos[indice]
                    if nome in entradas_externas:
                        continue
                    proprio = variavel_do_proprio_dispositivo(
                        nome,
                        dispositivos_evento,
                    )
                    if (
                        not permitir_proprios
                        and proprio
                        and nome not in origens_intermediarias(evento)
                    ):
                        continue
                    if simbolo in simbolos_usados:
                        continue

                    literal = _literal(simbolo, valores_alvo[indice])
                    cobertura = sum(
                        not _avaliar(
                            literal,
                            ordem_simbolos,
                            ponto.valores,
                        )
                        for ponto, _ in perigosos
                    )
                    if cobertura == 0:
                        continue

                    prioridade_tipo = (
                        0
                        if nome in origens_intermediarias(evento)
                        else 2 if proprio else (
                            0
                            if inicio_memorias <= indice < fim_memorias
                            else 1
                        )
                    )
                    prioridade = (
                        -cobertura,
                        prioridade_tipo,
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

    # 3) Em ramos condicionais, remove somente qualificadores acrescentados
    # que sejam realmente redundantes para todas as saídas da etapa.
    for evento in eventos:
        if not evento.condicoes_externas:
            continue

        def pode_remover(lista: list[object], posicao: int) -> bool:
            contra = list(qualificadores_contracomando[evento.indice])
            complementar = list(
                qualificadores_complementares[evento.indice]
            )
            if lista is qualificadores_contracomando[evento.indice]:
                contra.pop(posicao)
            else:
                complementar.pop(posicao)

            for comando in evento.comandos:
                expressao = expressao_comando(
                    evento,
                    comando.chave,
                    contra,
                    complementar,
                )
                if not _avaliar(
                    expressao,
                    ordem_simbolos,
                    alvo[evento.indice],
                ):
                    return False
                if any(
                    rotulos[comando.chave][ponto.evento] == "0"
                    and _avaliar(
                        expressao,
                        ordem_simbolos,
                        ponto.valores,
                    )
                    for ponto in pontos
                ):
                    return False
            return True

        for lista in (
            qualificadores_complementares[evento.indice],
            qualificadores_contracomando[evento.indice],
        ):
            for posicao in range(len(lista) - 1, -1, -1):
                if pode_remover(lista, posicao):
                    lista.pop(posicao)

    # 4) Organização didática das memórias, preservada da versão anterior.
    passos_conflito = set(_nos_de_conflito(arestas_conflito))
    frequencia_codigo: dict[tuple[int, ...], int] = {}
    for evento in eventos:
        if evento.tipo == "atuador" and evento.etapa_indice in passos_conflito:
            frequencia_codigo[evento.codigo] = (
                frequencia_codigo.get(evento.codigo, 0) + 1
            )

    nomes_memorias = ordem_nomes[inicio_memorias:fim_memorias]
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

    # 5) Se um sensor de origem intermediário já integra a condição do
    # comando, ele próprio cai quando o atuador deixa essa posição. Nesse caso
    # o contato de destino seria redundante e é retirado (ex.: B+(3)=c0.b2).
    for evento in eventos:
        fatores_contextuais = [
            *fatores_base[evento.indice],
            *qualificadores_contracomando[evento.indice],
            *qualificadores_complementares[evento.indice],
        ]
        simbolos_positivos = {
            str(fator)
            for fator in fatores_contextuais
            if isinstance(fator, Symbol)
        }
        for acao in evento.acoes:
            if acao.comando is None:
                continue
            if acao.sensor_origem in simbolos_positivos:
                evento.qualificadores_parada_por_comando[
                    acao.comando.chave
                ] = []

    # 6) Registra pontos perigosos e monta uma expressão por comando lógico.
    termos_por_saida: dict[str, list[object]] = {
        chave: [] for chave in _comandos_eventos(eventos)
    }

    for evento in eventos:
        evento.pontos_perigosos.clear()
        evento.qualificadores_contracomando = list(
            qualificadores_contracomando[evento.indice]
        )
        evento.qualificadores_complementares = list(
            qualificadores_complementares[evento.indice]
        )
        evento.qualificadores_parada = []
        evento.termos_por_comando = {}
        evento.fatores_por_comando = {}

        for comando in evento.comandos:
            paradas_comando = paradas(evento, comando.chave)
            for fator in paradas_comando:
                if fator not in evento.qualificadores_parada:
                    evento.qualificadores_parada.append(fator)

            expressao_qualificada = And(
                evento.base,
                *paradas_comando,
                *evento.qualificadores_contracomando,
            )
            expressao_final = And(
                expressao_qualificada,
                *evento.qualificadores_complementares,
            )

            for ponto in pontos:
                if rotulos[comando.chave][ponto.evento] != "0":
                    continue
                if transitorio_do_contracomando(ponto, comando):
                    continue
                if not _avaliar(
                    expressao_qualificada,
                    ordem_simbolos,
                    ponto.valores,
                ):
                    continue
                if ponto.valores not in evento.pontos_perigosos:
                    evento.pontos_perigosos.append(ponto.valores)
                if _avaliar(
                    expressao_final,
                    ordem_simbolos,
                    ponto.valores,
                ):
                    raise RuntimeError(
                        "A qualificação complementar não eliminou todos os "
                        f"pontos perigosos de {comando.rotulo}."
                    )

            fatores = [
                *fatores_base[evento.indice],
                *evento.qualificadores_contracomando,
                *evento.qualificadores_complementares,
                *paradas_comando,
            ]
            fatores_unicos: list[object] = []
            for fator in fatores:
                if fator not in fatores_unicos:
                    fatores_unicos.append(fator)

            termo = And(*fatores_unicos)
            evento.fatores_por_comando[comando.chave] = fatores_unicos
            evento.termos_por_comando[comando.chave] = termo
            termos_por_saida[comando.chave].append(termo)

        fatores_comuns = [
            *fatores_base[evento.indice],
            *evento.qualificadores_contracomando,
            *evento.qualificadores_complementares,
        ]
        if len(evento.comandos) == 1:
            fatores_comuns.extend(
                paradas(evento, evento.comandos[0].chave)
            )
        evento.fatores_ordenados = []
        for fator in fatores_comuns:
            if fator not in evento.fatores_ordenados:
                evento.fatores_ordenados.append(fator)
        evento.termo = (
            evento.termos_por_comando[evento.comandos[0].chave]
            if evento.comandos
            else And(*evento.fatores_ordenados)
        )

    return {
        chave: termos[0] if len(termos) == 1 else Or(*termos)
        for chave, termos in termos_por_saida.items()
    }


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


def _agrupar_expressoes_fisicas(
    expressoes_comandos: dict[str, object],
    comandos: dict[str, ComandoLogico],
) -> dict[str, object]:
    termos: dict[str, list[object]] = {}
    for chave, expressao in expressoes_comandos.items():
        fisica = comandos[chave].fisica
        termos.setdefault(fisica, []).append(expressao)
    return {
        saida: parcelas[0] if len(parcelas) == 1 else Or(*parcelas)
        for saida, parcelas in termos.items()
    }


def _validar(
    eventos: list[Evento],
    memorias: tuple[str, ...],
    caminhos: dict[int, tuple[tuple[int, ...], ...]],
    rotulos: dict[str, list[str]],
    pontos: list[Ponto],
    expressoes_comandos: dict[str, object],
    expressoes_fisicas: dict[str, object],
    ordem_simbolos: list[Symbol],
    contexto: ContextoFisico,
) -> tuple[str, ...]:
    for evento in eventos:
        valores = _valores_alvo_evento(
            evento,
            contexto.entradas_externas,
        )
        for comando in evento.comandos:
            termo = evento.termos_por_comando.get(
                comando.chave,
                evento.termo,
            )
            if not _avaliar(termo, ordem_simbolos, valores):
                raise RuntimeError(
                    f"O comando {comando.rotulo} não dispara no ponto correto."
                )

    indice_variavel = {
        nome: indice
        for indice, nome in enumerate(contexto.variaveis)
    }

    def comando_ja_concluido(chave: str, ponto: Ponto) -> bool:
        evento_ponto = eventos[ponto.evento]
        acao = next(
            (
                acao
                for acao in evento_ponto.acoes
                if acao.comando is not None
                and acao.comando.chave == chave
            ),
            None,
        )
        if acao is None:
            return False
        fisico = ponto.valores[:contexto.quantidade_variaveis]
        return all(
            fisico[indice_variavel[nome]] == valor
            for nome, valor in acao.conclusao
        )

    comandos_por_chave = _comandos_eventos(eventos)

    def transitorio_do_contracomando(chave: str, ponto: Ponto) -> bool:
        comando = comandos_por_chave[chave]
        evento_ponto = eventos[ponto.evento]
        fisico = ponto.valores[:contexto.quantidade_variaveis]
        if fisico not in evento_ponto.intermediarios:
            return False
        return any(
            outro.dispositivo == comando.dispositivo
            and outro.sentido != comando.sentido
            for outro in evento_ponto.comandos
        )

    for ponto in pontos:
        for chave, expressao in expressoes_comandos.items():
            esperado = rotulos[chave][ponto.evento]
            obtido = _avaliar(expressao, ordem_simbolos, ponto.valores)
            if esperado == "1" and not obtido:
                # Em simultaneidade, uma saída pode desligar assim que sua
                # própria ação termina, enquanto as outras continuam ativas.
                if comando_ja_concluido(chave, ponto):
                    continue
                raise RuntimeError(
                    f"{chave} deveria estar ativo no ponto {ponto.valores}."
                )
            if esperado == "0" and obtido:
                if transitorio_do_contracomando(chave, ponto):
                    continue
                raise RuntimeError(
                    f"Ponto perigoso: {chave} ficou ativo no ponto "
                    f"{ponto.valores}."
                )

    dispositivos = {saida[:-1] for saida in expressoes_fisicas}
    for dispositivo in dispositivos:
        mais = expressoes_fisicas.get(f"{dispositivo}+", false)
        menos = expressoes_fisicas.get(f"{dispositivo}-", false)
        for ponto in pontos:
            if (
                _avaliar(mais, ordem_simbolos, ponto.valores)
                and _avaliar(menos, ordem_simbolos, ponto.valores)
            ):
                evento_ponto = eventos[ponto.evento]
                fisico = ponto.valores[:contexto.quantidade_variaveis]
                transitorio_proprio = (
                    fisico in evento_ponto.intermediarios
                    and any(
                        comando.dispositivo == dispositivo
                        for comando in evento_ponto.comandos
                    )
                )
                if transitorio_proprio:
                    continue
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
        set_expr = expressoes_fisicas.get(f"{memoria}+", false)
        reset_expr = expressoes_fisicas.get(f"{memoria}-", false)
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
        "atuadores multiposição usam sensores exclusivos e destinos explícitos",
        "paradas intermediárias são bloqueadas pelo sensor de destino",
        "ramificações de loop são habilitadas por condições externas exclusivas",
        "comandos e contracomandos foram qualificados progressivamente",
        "nenhum ponto perigoso permaneceu nos estados alcançáveis",
        "nenhum comando e contracomando ficam ativos simultaneamente",
        "somente uma memória muda em cada evento de memória",
        "equações de SET, RESET e retenção das memórias são coerentes",
    )


# ---------------------------------------------------------------------------
# Formatação das equações na mesma ordem da construção
# ---------------------------------------------------------------------------


def _formatar_literal(
    literal,
    contexto: ContextoFisico,
    memorias: tuple[str, ...],
) -> str:
    conjunto_memorias = set(memorias)

    if isinstance(literal, Symbol):
        nome = str(literal)
        if nome == "S":
            return "S"
        if nome in conjunto_memorias:
            return nome.lower()
        if nome in contexto.entradas_externas:
            return nome.lower()
        if nome in contexto.rotulos_binarios:
            return contexto.rotulos_binarios[nome][1]
        if nome in contexto.sensores_one_hot:
            return nome.lower()
        return nome

    if literal.func is Not and isinstance(literal.args[0], Symbol):
        nome = str(literal.args[0])
        if nome == "S":
            return "S0"
        if nome in conjunto_memorias:
            return f"{nome.lower()}0"
        if nome in contexto.entradas_externas:
            return f"{nome.lower()}'"
        if nome in contexto.rotulos_binarios:
            return contexto.rotulos_binarios[nome][0]
        if nome in contexto.sensores_one_hot:
            return f"{nome.lower()}'"
        return f"{nome}0"

    return str(literal)


def _formatar_termo_evento(
    evento: Evento,
    contexto: ContextoFisico,
    memorias: tuple[str, ...],
    chave: str | None = None,
) -> str:
    fatores = (
        evento.fatores_por_comando.get(chave, evento.fatores_ordenados)
        if chave is not None
        else evento.fatores_ordenados
    )
    if not fatores:
        return "1"
    return ".".join(
        _formatar_literal(fator, contexto, memorias)
        for fator in fatores
    )


def _equacoes_textuais_comandos(
    eventos: list[Evento],
    contexto: ContextoFisico,
    memorias: tuple[str, ...],
) -> dict[str, str]:
    termos: dict[str, list[str]] = {}
    ordem_rotulos: list[str] = []

    for evento in eventos:
        for comando in evento.comandos:
            texto = _formatar_termo_evento(
                evento,
                contexto,
                memorias,
                comando.chave,
            )
            rotulo = comando.rotulo
            if rotulo not in termos:
                termos[rotulo] = []
                ordem_rotulos.append(rotulo)
            if texto not in termos[rotulo]:
                termos[rotulo].append(texto)

    return {
        rotulo: " + ".join(termos[rotulo])
        for rotulo in ordem_rotulos
    }


def _simplificar_soma_textual(
    termos: list[str],
    contexto: ContextoFisico,
    memorias: tuple[str, ...],
) -> str:
    """Aplica absorção e a identidade p.q + p.q' = p.

    A simplificação é deliberadamente conservadora para preservar a ordem e
    a forma didática do método. Ela resolve, por exemplo,
    x.b1' + b1.x = x, sem reescrever globalmente todas as equações.
    """

    complementos: dict[str, str] = {"S": "S0", "S0": "S"}
    for memoria in memorias:
        ativo = memoria.lower()
        inativo = f"{ativo}0"
        complementos[ativo] = inativo
        complementos[inativo] = ativo
    for entrada in contexto.entradas_externas:
        ativo = entrada.lower()
        inativo = f"{ativo}'"
        complementos[ativo] = inativo
        complementos[inativo] = ativo
    for sensor0, sensor1 in contexto.rotulos_binarios.values():
        complementos[sensor0] = sensor1
        complementos[sensor1] = sensor0
    for sensor in contexto.sensores_one_hot:
        ativo = sensor.lower()
        inativo = f"{ativo}'"
        complementos[ativo] = inativo
        complementos[inativo] = ativo

    parcelas: list[list[str]] = []
    for termo in termos:
        fatores: list[str] = []
        for fator in termo.split(".") if termo != "1" else []:
            if fator not in fatores:
                fatores.append(fator)
        if fatores not in parcelas:
            parcelas.append(fatores)

    mudou = True
    while mudou:
        mudou = False

        # Absorção: p + p.q = p.
        remover: set[int] = set()
        conjuntos = [set(parcela) for parcela in parcelas]
        for i, a in enumerate(conjuntos):
            for j, b in enumerate(conjuntos):
                if i != j and a <= b and a != b:
                    remover.add(j)
        if remover:
            parcelas = [
                parcela
                for indice, parcela in enumerate(parcelas)
                if indice not in remover
            ]
            mudou = True
            continue

        # Combina duas parcelas que diferem apenas por um literal e seu
        # complemento.
        combinado = False
        for i in range(len(parcelas)):
            if combinado:
                break
            for j in range(i + 1, len(parcelas)):
                a = set(parcelas[i])
                b = set(parcelas[j])
                somente_a = a - b
                somente_b = b - a
                if len(somente_a) != 1 or len(somente_b) != 1:
                    continue
                literal_a = next(iter(somente_a))
                literal_b = next(iter(somente_b))
                if complementos.get(literal_a) != literal_b:
                    continue
                comum = [
                    fator
                    for fator in parcelas[i]
                    if fator in a & b
                ]
                novas = [
                    parcela
                    for indice, parcela in enumerate(parcelas)
                    if indice not in {i, j}
                ]
                novas.append(comum)
                parcelas = novas
                mudou = True
                combinado = True
                break

    if not parcelas:
        return "0"
    if any(not parcela for parcela in parcelas):
        return "1"
    return " + ".join(".".join(parcela) for parcela in parcelas)


def _equacoes_textuais_fisicas(
    eventos: list[Evento],
    contexto: ContextoFisico,
    memorias: tuple[str, ...],
) -> dict[str, str]:
    termos: dict[str, list[str]] = {}
    ordem: list[str] = []

    for evento in eventos:
        for comando in evento.comandos:
            texto = _formatar_termo_evento(
                evento,
                contexto,
                memorias,
                comando.chave,
            )
            saida = comando.fisica
            if saida not in termos:
                termos[saida] = []
                ordem.append(saida)
            if texto not in termos[saida]:
                termos[saida].append(texto)

    return {
        saida: _simplificar_soma_textual(
            termos[saida],
            contexto,
            memorias,
        )
        for saida in ordem
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


def _candidato_compativel_com_loops(
    candidato: CaminhoCandidato,
    loops: tuple[Any, ...],
    quantidade_etapas: int,
) -> bool:
    """Garante um único código de memória no nó de decisão do loop.

    O estado antes da primeira etapa do loop e o estado após sua última etapa
    são fisicamente iguais. Portanto, a rota de repetição e a rota de saída
    precisam compartilhar o mesmo código de memória; a entrada externa é que
    escolhe qual comando será habilitado.
    """

    for loop in loops:
        codigo_inicio = candidato.codigos[loop.inicio]
        indice_saida = loop.fim + 1

        if indice_saida < quantidade_etapas:
            if codigo_inicio != candidato.codigos[indice_saida]:
                return False
        elif codigo_inicio != 0:
            # No fim da sequência, o fechamento das memórias restaura 0.
            return False

    return True


def resolver(
    sequencia,
    estado_inicial: Optional[Mapping[str, int | str]] = None,
    *,
    ciclo_continuo: bool = False,
) -> Resultado:
    contexto, inicial, etapas = _construir_etapas_contexto(
        sequencia,
        estado_inicial,
    )
    atuadores = contexto.atuadores

    fecha_ciclo = etapas[-1].depois == etapas[0].antes
    if ciclo_continuo and not fecha_ciclo:
        raise ValueError(
            "Em ciclo contínuo, o estado final deve ser igual ao estado inicial."
        )

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
        if contexto.loops:
            candidatos = tuple(
                candidato
                for candidato in candidatos
                if _candidato_compativel_com_loops(
                    candidato,
                    contexto.loops,
                    len(etapas),
                )
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
            etapas_teste = [
                Etapa(
                    indice=etapa.indice,
                    acoes=etapa.acoes,
                    antes=etapa.antes,
                    depois=etapa.depois,
                    intermediarios=etapa.intermediarios,
                    intermediarios_conflito=etapa.intermediarios_conflito,
                    condicoes_externas=etapa.condicoes_externas,
                    restricoes_externas=etapa.restricoes_externas,
                    fechamento_loop=etapa.fechamento_loop,
                )
                for etapa in etapas
            ]

            try:
                caminhos = _atribuir_candidato(
                    etapas_teste,
                    candidato,
                    quantidade_memorias,
                )

                ordem_nomes = [
                    *contexto.variaveis,
                    *memorias,
                    *contexto.entradas_externas,
                    "S",
                ]
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
                pontos = _pontos_alcancaveis(
                    eventos,
                    contexto.entradas_externas,
                )

                expressoes_comandos = _qualificar_progressivamente(
                    eventos,
                    rotulos,
                    pontos,
                    ordem_nomes,
                    ordem_simbolos,
                    contexto.quantidade_variaveis,
                    len(memorias),
                    arestas,
                    contexto,
                )
                comandos = _comandos_eventos(eventos)
                expressoes_fisicas = _agrupar_expressoes_fisicas(
                    expressoes_comandos,
                    comandos,
                )

                validacoes = _validar(
                    eventos,
                    memorias,
                    caminhos,
                    rotulos,
                    pontos,
                    expressoes_comandos,
                    expressoes_fisicas,
                    ordem_simbolos,
                    contexto,
                )
            except RuntimeError as erro:
                erros.append(str(erro))
                continue

            equacoes_comandos = _equacoes_textuais_comandos(
                eventos,
                contexto,
                memorias,
            )
            equacoes = _equacoes_textuais_fisicas(
                eventos,
                contexto,
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
                expressoes_fisicas,
                equacoes,
                expressoes_comandos,
                equacoes_comandos,
                equacoes_memorias,
                validacoes,
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
        expressoes_comandos,
        equacoes_comandos,
        equacoes_memorias,
        validacoes,
    ) = solucao

    multiposicao = [
        nome
        for nome, config in contexto.configuracoes.items()
        if len(config.sensores) > 2
    ]
    observacoes = [
        f"Quantidade encontrada: {len(memorias)} memória(s).",
        f"Foram testadas {total_candidatos_testados} colocações de memória.",
        "As expressões são mantidas na ordem de qualificação da apostila; "
        "não é feita uma minimização algébrica global que altere o método.",
    ]
    if multiposicao:
        observacoes.append(
            "Atuadores multiposição processados: "
            + ", ".join(multiposicao)
            + "."
        )
    if contexto.loops:
        observacoes.append(
            "Loops condicionais processados: "
            + ", ".join(
                f"etapas {loop.inicio + 1}–{loop.fim + 1} "
                f"por {loop.sensor}={loop.repetir_quando}"
                for loop in contexto.loops
            )
            + "."
        )
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
        expressoes_comandos=expressoes_comandos,
        equacoes_comandos=equacoes_comandos,
        equacoes_memorias=equacoes_memorias,
        validacoes=validacoes,
        contexto_fisico=contexto,
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
                "X-": "b0.a0.y",
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
            *resultado.variaveis_fisicas,
            *resultado.memorias,
            "S",
        ]

        simbolos_teste = [
            Symbol(nome, boolean=True)
            for nome in nomes_teste
        ]

        for evento in resultado.eventos:
            expressao_qualificada = And(
                evento.base,
                *evento.qualificadores_parada,
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
            resultado.contexto_fisico,
            resultado.memorias,
        )
        for literal in evento_b_mais.qualificadores_contracomando
    )
    complementares = tuple(
        _formatar_literal(
            literal,
            resultado.contexto_fisico,
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

    resultado_multiposicao = resolver(
        "A+, B+ até b1, C+, B+ até b2, C-, "
        "B+ até b3, A-, B- até b0"
    )
    esperado_multiposicao = {
        "A+": "S.b0",
        "B+": "a1.c0.b1' + c1.b2' + c0.b2",
        "C+": "b1.a1",
        "C-": "b2",
        "A-": "b3",
        "B-": "a0",
    }
    if resultado_multiposicao.equacoes != esperado_multiposicao:
        raise AssertionError(
            "As equações do exemplo multiposição divergiram: "
            f"{resultado_multiposicao.equacoes}."
        )
    mensagens.append("Exemplo multiposição validado.")

    resultado_loop = resolver(
        "A+, B+, [C+, D+, C-, D-] enquanto e=0, A-, B-"
    )
    esperado_loop = {
        "A+": "S.b0",
        "B+": "a1",
        "C+": "b1.e'.d0",
        "D+": "c1",
        "C-": "d1",
        "D-": "c0",
        "A-": "d0.e.b1",
        "B-": "a0",
    }
    if resultado_loop.equacoes != esperado_loop:
        raise AssertionError(
            "As equações do exemplo com loop divergiram: "
            f"{resultado_loop.equacoes}."
        )
    mensagens.append("Exemplo com loop condicional validado.")

    return tuple(mensagens)


# ---------------------------------------------------------------------------
# Utilidades de exibição
# ---------------------------------------------------------------------------


def _estado_texto(
    estado: tuple[int, ...],
    contexto: ContextoFisico,
) -> str:
    return " ".join(
        contexto.sensor_ativo(estado, atuador)
        for atuador in contexto.atuadores
    )


def _codigo_texto(codigo: tuple[int, ...], memorias: tuple[str, ...]) -> str:
    return " ".join(
        f"{memoria.lower()}{valor}"
        for memoria, valor in zip(memorias, codigo)
    )


if __name__ == "__main__":
    for mensagem in validar_exemplos_referencia():
        print(f"✓ {mensagem}")