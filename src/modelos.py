from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias


EstadoFisico: TypeAlias = dict[str, str]


def _nome_normalizado(nome: str) -> str:
    """Normaliza nomes somente para comparações e detecção de conflitos."""
    return str(nome).strip().casefold()


def _validar_nome(nome: str, descricao: str) -> None:
    if not str(nome).strip():
        raise ValueError(f"{descricao} precisa possuir um nome.")


def _verificar_repetidos(
    nomes: list[str] | tuple[str, ...],
    descricao: str,
) -> None:
    normalizados = [_nome_normalizado(nome) for nome in nomes]

    repetidos = {
        nome
        for nome in normalizados
        if normalizados.count(nome) > 1
    }

    if repetidos:
        raise ValueError(
            f"{descricao} possui nomes repetidos: "
            + ", ".join(sorted(repetidos))
            + "."
        )


@dataclass(frozen=True)
class AtuadorConfig:
    """
    Configuração de um atuador e de suas posições monitoradas.

    A ordem dos sensores representa a ordem física das posições.

    Exemplo:

        AtuadorConfig(
            nome="B",
            sensores=("b0", "b1", "b2", "b3"),
            sensor_inicial="b0",
        )

    Nesse caso:

        B+ pode avançar de b0 para b1, b2 ou b3;
        B- pode retornar de b3 para b2, b1 ou b0.
    """

    nome: str
    sensores: tuple[str, ...]
    sensor_inicial: str

    def validar(self) -> None:
        _validar_nome(
            self.nome,
            "O atuador",
        )

        if len(self.sensores) < 2:
            raise ValueError(
                f"O atuador {self.nome} precisa possuir "
                "pelo menos dois sensores."
            )

        for sensor in self.sensores:
            _validar_nome(
                sensor,
                f"Um sensor do atuador {self.nome}",
            )

        _verificar_repetidos(
            self.sensores,
            f"O atuador {self.nome}",
        )

        sensores_normalizados = {
            _nome_normalizado(sensor): sensor
            for sensor in self.sensores
        }

        if (
            _nome_normalizado(self.sensor_inicial)
            not in sensores_normalizados
        ):
            raise ValueError(
                f"O sensor inicial {self.sensor_inicial} "
                f"não pertence ao atuador {self.nome}."
            )

    def indice_sensor(self, sensor: str) -> int:
        """
        Retorna a posição ordinal de um sensor.

        A comparação é feita sem diferenciar letras maiúsculas
        e minúsculas.
        """

        procurado = _nome_normalizado(sensor)

        for indice, nome_sensor in enumerate(self.sensores):
            if _nome_normalizado(nome_sensor) == procurado:
                return indice

        raise ValueError(
            f"O sensor {sensor} não pertence ao atuador {self.nome}."
        )

    def sensor_canonico(self, sensor: str) -> str:
        """
        Retorna o nome do sensor exatamente como foi cadastrado.
        """

        return self.sensores[self.indice_sensor(sensor)]

    @property
    def quantidade_posicoes(self) -> int:
        return len(self.sensores)

    @property
    def sensor_minimo(self) -> str:
        return self.sensores[0]

    @property
    def sensor_maximo(self) -> str:
        return self.sensores[-1]


@dataclass(frozen=True)
class Movimento:
    """
    Movimento normalizado de um atuador.

    O destino é sempre explícito no modelo interno, mesmo quando
    o usuário digitou apenas A+ ou A-.

    Exemplos:

        Movimento("A", "+", "a1")
        Movimento("B", "+", "b2")
        Movimento("B", "-", "b0")
    """

    atuador: str
    sentido: str
    sensor_destino: str

    def validar(self) -> None:
        _validar_nome(
            self.atuador,
            "O movimento",
        )

        if self.sentido not in {"+", "-"}:
            raise ValueError(
                f"Sentido inválido no movimento do atuador "
                f"{self.atuador}: {self.sentido!r}."
            )

        _validar_nome(
            self.sensor_destino,
            (
                f"O sensor de destino do movimento "
                f"{self.atuador}{self.sentido}"
            ),
        )

    @property
    def saida(self) -> str:
        """
        Nome da saída física do atuador.

        Vários movimentos podem usar a mesma saída, por exemplo:

            B+ até b1
            B+ até b2
            B+ até b3

        Todos possuem a saída física B+.
        """

        return f"{self.atuador}{self.sentido}"

    @property
    def descricao(self) -> str:
        return (
            f"{self.atuador}{self.sentido} "
            f"até {self.sensor_destino}"
        )


@dataclass(frozen=True)
class EtapaSequencial:
    """
    Uma etapa da sequência.

    Uma etapa pode possuir um único movimento ou vários movimentos
    simultâneos.
    """

    movimentos: tuple[Movimento, ...]

    def validar(self) -> None:
        if not self.movimentos:
            raise ValueError(
                "Uma etapa não pode estar vazia."
            )

        for movimento in self.movimentos:
            movimento.validar()

        atuadores = [
            _nome_normalizado(movimento.atuador)
            for movimento in self.movimentos
        ]

        if len(set(atuadores)) != len(atuadores):
            raise ValueError(
                "Um mesmo atuador não pode aparecer duas vezes "
                "na mesma etapa."
            )

    @property
    def simultanea(self) -> bool:
        return len(self.movimentos) > 1

    @property
    def descricao(self) -> str:
        textos = [
            movimento.descricao
            for movimento in self.movimentos
        ]

        if self.simultanea:
            return "(" + ", ".join(textos) + ")"

        return textos[0]


@dataclass(frozen=True)
class LoopConfig:
    """
    Configuração de um trecho repetitivo da sequência.

    Os índices de início e fim são inclusivos e começam em zero.

    Exemplo:

        LoopConfig(
            inicio=2,
            fim=5,
            sensor="e",
            repetir_quando=0,
        )

    Significa que as etapas 2, 3, 4 e 5 são repetidas enquanto
    e = 0. Quando e = 1, a sequência continua após a etapa 5.
    """

    inicio: int
    fim: int
    sensor: str
    repetir_quando: int = 0

    @property
    def sair_quando(self) -> int:
        return 1 - self.repetir_quando

    def validar(self, quantidade_etapas: int) -> None:
        if quantidade_etapas <= 0:
            raise ValueError(
                "Não é possível criar um loop sem etapas."
            )

        if self.inicio < 0 or self.inicio >= quantidade_etapas:
            raise ValueError(
                "O início do loop é inválido."
            )

        if self.fim < self.inicio or self.fim >= quantidade_etapas:
            raise ValueError(
                "O final do loop é inválido."
            )

        if self.repetir_quando not in {0, 1}:
            raise ValueError(
                "A condição de repetição precisa ser 0 ou 1."
            )

        _validar_nome(
            self.sensor,
            "O sensor de decisão do loop",
        )

    @property
    def quantidade_etapas(self) -> int:
        return self.fim - self.inicio + 1

    @property
    def descricao(self) -> str:
        return (
            f"etapas {self.inicio + 1} a {self.fim + 1}, "
            f"repetir enquanto {self.sensor} = "
            f"{self.repetir_quando}"
        )


@dataclass
class ProjetoSequencial:
    """
    Modelo completo de entrada do solucionador.

    Ele será utilizado tanto pela entrada textual quanto pelo futuro
    editor visual. O motor deverá receber este modelo já validado.
    """

    atuadores: dict[str, AtuadorConfig]
    etapas: list[EtapaSequencial]
    loops: list[LoopConfig] = field(default_factory=list)
    sinal_partida: str = "S"
    entradas_externas: list[str] = field(default_factory=list)

    def validar(self) -> None:
        self._validar_estrutura_basica()
        self._validar_atuadores()
        self._validar_entradas_externas()
        self._validar_conflitos_de_nomes()

        estados = self._validar_e_simular_etapas()

        self._validar_loops(
            estados=estados,
        )

    def _validar_estrutura_basica(self) -> None:
        if not self.atuadores:
            raise ValueError(
                "É necessário cadastrar pelo menos um atuador."
            )

        if not self.etapas:
            raise ValueError(
                "É necessário cadastrar pelo menos uma etapa."
            )

        _validar_nome(
            self.sinal_partida,
            "O sinal de partida",
        )

    def _validar_atuadores(self) -> None:
        nomes_atuadores: list[str] = []

        for chave, atuador in self.atuadores.items():
            atuador.validar()

            if _nome_normalizado(chave) != _nome_normalizado(
                atuador.nome
            ):
                raise ValueError(
                    f"A chave {chave!r} não corresponde "
                    f"ao atuador {atuador.nome!r}."
                )

            nomes_atuadores.append(atuador.nome)

        _verificar_repetidos(
            nomes_atuadores,
            "O cadastro de atuadores",
        )

    def _validar_entradas_externas(self) -> None:
        for entrada in self.entradas_externas:
            _validar_nome(
                entrada,
                "Uma entrada externa",
            )

        _verificar_repetidos(
            self.entradas_externas,
            "O cadastro de entradas externas",
        )

    def _validar_conflitos_de_nomes(self) -> None:
        """
        Impede que dois elementos diferentes utilizem o mesmo nome.

        A comparação ignora diferenças entre maiúsculas e minúsculas.
        """

        ocupados: dict[str, str] = {}

        def registrar(
            nome: str,
            descricao: str,
        ) -> None:
            chave = _nome_normalizado(nome)

            anterior = ocupados.get(chave)

            if anterior is not None:
                raise ValueError(
                    f"O nome {nome!r} está sendo utilizado por "
                    f"{descricao} e também por {anterior}."
                )

            ocupados[chave] = descricao

        for atuador in self.atuadores.values():
            registrar(
                atuador.nome,
                f"o atuador {atuador.nome}",
            )

            for sensor in atuador.sensores:
                registrar(
                    sensor,
                    (
                        f"o sensor {sensor} do atuador "
                        f"{atuador.nome}"
                    ),
                )

        for entrada in self.entradas_externas:
            registrar(
                entrada,
                f"a entrada externa {entrada}",
            )

        registrar(
            self.sinal_partida,
            f"o sinal de partida {self.sinal_partida}",
        )

    def _obter_atuador(
        self,
        nome: str,
    ) -> AtuadorConfig:
        procurado = _nome_normalizado(nome)

        for chave, configuracao in self.atuadores.items():
            if (
                _nome_normalizado(chave) == procurado
                or _nome_normalizado(configuracao.nome) == procurado
            ):
                return configuracao

        raise ValueError(
            f"O atuador {nome} não foi cadastrado."
        )

    def _validar_e_simular_etapas(
        self,
    ) -> list[EstadoFisico]:
        """
        Valida os movimentos e produz os estados lineares.

        A lista retornada possui:

            estados[0] = estado inicial
            estados[1] = estado após a etapa 1
            estados[2] = estado após a etapa 2
            ...

        Portanto, o estado anterior à etapa de índice i é estados[i],
        e o estado posterior é estados[i + 1].
        """

        estado_atual: EstadoFisico = {
            atuador.nome: atuador.sensor_canonico(
                atuador.sensor_inicial
            )
            for atuador in self.atuadores.values()
        }

        estados: list[EstadoFisico] = [
            dict(estado_atual)
        ]

        for indice_etapa, etapa in enumerate(
            self.etapas,
            start=1,
        ):
            etapa.validar()

            proximo_estado = dict(estado_atual)

            for movimento in etapa.movimentos:
                configuracao = self._obter_atuador(
                    movimento.atuador
                )

                sensor_atual = estado_atual[
                    configuracao.nome
                ]

                indice_atual = configuracao.indice_sensor(
                    sensor_atual
                )

                indice_destino = configuracao.indice_sensor(
                    movimento.sensor_destino
                )

                if indice_destino == indice_atual:
                    raise ValueError(
                        f"Etapa {indice_etapa}: o atuador "
                        f"{configuracao.nome} já está no sensor "
                        f"{movimento.sensor_destino}."
                    )

                if (
                    movimento.sentido == "+"
                    and indice_destino < indice_atual
                ):
                    raise ValueError(
                        f"Etapa {indice_etapa}: o movimento "
                        f"{movimento.saida} não pode ir de "
                        f"{sensor_atual} para "
                        f"{movimento.sensor_destino}. "
                        "O sentido positivo deve avançar na ordem "
                        "dos sensores."
                    )

                if (
                    movimento.sentido == "-"
                    and indice_destino > indice_atual
                ):
                    raise ValueError(
                        f"Etapa {indice_etapa}: o movimento "
                        f"{movimento.saida} não pode ir de "
                        f"{sensor_atual} para "
                        f"{movimento.sensor_destino}. "
                        "O sentido negativo deve retornar na ordem "
                        "dos sensores."
                    )

                proximo_estado[
                    configuracao.nome
                ] = configuracao.sensor_canonico(
                    movimento.sensor_destino
                )

            estado_atual = proximo_estado
            estados.append(
                dict(estado_atual)
            )

        return estados

    def _validar_loops(
        self,
        estados: list[EstadoFisico],
    ) -> None:
        entradas_normalizadas = {
            _nome_normalizado(entrada)
            for entrada in self.entradas_externas
        }

        for loop in self.loops:
            loop.validar(
                len(self.etapas)
            )

            if (
                _nome_normalizado(loop.sensor)
                not in entradas_normalizadas
            ):
                raise ValueError(
                    f"O sensor externo {loop.sensor} utilizado "
                    "no loop não foi cadastrado."
                )

        self._validar_sobreposicao_loops()

        for loop in self.loops:
            estado_entrada = estados[
                loop.inicio
            ]

            estado_saida = estados[
                loop.fim + 1
            ]

            if estado_entrada != estado_saida:
                diferencas: list[str] = []

                for atuador in self.atuadores.values():
                    antes = estado_entrada[
                        atuador.nome
                    ]

                    depois = estado_saida[
                        atuador.nome
                    ]

                    if antes != depois:
                        diferencas.append(
                            f"{atuador.nome}: "
                            f"{antes} → {depois}"
                        )

                raise ValueError(
                    "O trecho configurado como loop não retorna "
                    "ao estado físico necessário para uma nova "
                    "repetição. Diferenças encontradas: "
                    + ", ".join(diferencas)
                    + "."
                )

    def _validar_sobreposicao_loops(self) -> None:
        """
        Nesta primeira versão, loops podem existir em quantidade
        maior que um, mas não podem ser aninhados nem sobrepostos.
        """

        ordenados = sorted(
            self.loops,
            key=lambda loop: (
                loop.inicio,
                loop.fim,
            ),
        )

        for anterior, atual in zip(
            ordenados,
            ordenados[1:],
        ):
            if atual.inicio <= anterior.fim:
                raise ValueError(
                    "Os loops configurados entre as etapas "
                    f"{anterior.inicio + 1}–{anterior.fim + 1} "
                    f"e {atual.inicio + 1}–{atual.fim + 1} "
                    "estão sobrepostos. Loops sobrepostos ou "
                    "aninhados ainda não são permitidos."
                )

    def estado_inicial(self) -> EstadoFisico:
        """
        Retorna o estado inicial usando os sensores cadastrados.
        """

        return {
            atuador.nome: atuador.sensor_canonico(
                atuador.sensor_inicial
            )
            for atuador in self.atuadores.values()
        }

    def simular_estados(self) -> list[EstadoFisico]:
        """
        Valida o projeto e retorna todos os estados lineares.
        """

        self.validar()

        return self._validar_e_simular_etapas()

    def sensores_fisicos(self) -> tuple[str, ...]:
        """
        Retorna todos os sensores físicos na ordem de cadastro.
        """

        return tuple(
            sensor
            for atuador in self.atuadores.values()
            for sensor in atuador.sensores
        )

    def obter_loop_da_etapa(
        self,
        indice_etapa: int,
    ) -> LoopConfig | None:
        """
        Retorna o loop que contém uma etapa, quando existir.
        """

        for loop in self.loops:
            if loop.inicio <= indice_etapa <= loop.fim:
                return loop

        return None