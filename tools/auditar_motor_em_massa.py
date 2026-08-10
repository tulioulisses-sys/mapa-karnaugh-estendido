from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from itertools import combinations, product
from pathlib import Path
from typing import Iterable

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.engine import resolver


@dataclass
class Falha:
    categoria: str
    sequencia: str
    detalhe: str


def _rotulo_equacao(chave: str) -> str:
    if "#" not in chave:
        return chave
    base, indice = chave.rsplit("#", 1)
    return f"{base}({indice})"


def _avaliar_equacao_binaria(
    equacao: str,
    estado: dict[str, int],
    *,
    start: bool,
) -> bool:
    texto = equacao.replace(" ", "")
    if texto == "1":
        return True

    for parcela in texto.split("+"):
        produto = True
        for token in parcela.split("."):
            if not token:
                continue
            if token == "S":
                valor = start
            elif token[-1:] in {"0", "1"} and token[:-1].isalpha():
                nome = token[:-1].upper()
                if nome not in estado:
                    raise ValueError(f"literal fora do modelo binario: {token}")
                valor = estado[nome] == int(token[-1])
            else:
                raise ValueError(f"literal nao suportado na auditoria binaria: {token}")
            produto = produto and valor
        if produto:
            return True
    return False


def _fatores_textuais(expressao) -> set[str]:
    if getattr(expressao.func, "__name__", "") == "And":
        return {str(item) for item in expressao.args}
    return {str(expressao)}


def _literal_conclusao(nome: str, valor: int) -> str:
    return nome if valor else f"~{nome}"


def _sequencias_binarias_fechadas(
    nomes: str,
    max_etapas: int,
) -> Iterable[tuple[str, list[list[str]], list[dict[str, int]]]]:
    quantidade = len(nomes)
    subconjuntos = tuple(range(1, 1 << quantidade))

    for numero_etapas in range(2, max_etapas + 1):
        for mascaras in product(subconjuntos, repeat=numero_etapas):
            paridade = 0
            for mascara in mascaras:
                paridade ^= mascara
            if paridade:
                continue

            estado = {nome: 0 for nome in nomes}
            etapas: list[list[str]] = []
            estados_antes: list[dict[str, int]] = []

            for mascara in mascaras:
                estados_antes.append(estado.copy())
                acoes: list[str] = []
                for indice, nome in enumerate(nomes):
                    if not (mascara >> indice) & 1:
                        continue
                    sentido = "+" if estado[nome] == 0 else "-"
                    acoes.append(f"{nome}{sentido}")
                    estado[nome] ^= 1
                etapas.append(acoes)

            partes = [
                acoes[0]
                if len(acoes) == 1
                else f"({', '.join(acoes)})"
                for acoes in etapas
            ]
            yield ", ".join(partes), etapas, estados_antes


def _sequencias_sequenciais_fechadas_3_atuadores() -> Iterable[str]:
    nomes = ("A", "B", "C")
    for quantidade in (2, 4, 6):
        for alternancias in product(range(3), repeat=quantidade):
            estado = [0, 0, 0]
            acoes: list[str] = []
            for indice in alternancias:
                sentido = "+" if estado[indice] == 0 else "-"
                acoes.append(f"{nomes[indice]}{sentido}")
                estado[indice] ^= 1
            if estado == [0, 0, 0]:
                yield ", ".join(acoes)


def _auditar_ciclo_binario(
    sequencia: str,
    etapas: list[list[str]],
    estados_antes: list[dict[str, int]],
    falhas: list[Falha],
) -> tuple[int, int]:
    try:
        resultado = resolver(sequencia)
    except Exception as exc:  # pragma: no cover - utilitario de auditoria
        falhas.append(Falha("excecao", sequencia, repr(exc)))
        return 0, 0

    eventos_atuador = [
        evento for evento in resultado.eventos if evento.tipo == "atuador"
    ]
    obtido = [list(evento.saidas) for evento in eventos_atuador]
    if obtido != etapas:
        falhas.append(
            Falha(
                "estrutura_eventos",
                sequencia,
                f"esperado={etapas!r}; obtido={obtido!r}",
            )
        )
        return 0, 0

    barreiras = 0
    for indice in range(1, len(resultado.eventos)):
        anterior = resultado.eventos[indice - 1]
        atual = resultado.eventos[indice]
        if (
            anterior.tipo != "atuador"
            or atual.tipo != "atuador"
            or len(anterior.acoes) <= 1
        ):
            continue

        esperados = {
            _literal_conclusao(nome, valor)
            for acao in anterior.acoes
            for nome, valor in acao.conclusao
        }
        presentes = _fatores_textuais(atual.base)
        barreiras += 1
        faltantes = sorted(esperados - presentes)
        if faltantes:
            falhas.append(
                Falha(
                    "barreira_causal",
                    sequencia,
                    (
                        f"{anterior.saidas} -> {atual.saidas}; "
                        f"base={atual.base}; faltantes={faltantes}"
                    ),
                )
            )
            return barreiras, 0

    microestados = 0
    if resultado.memorias:
        return barreiras, microestados

    for indice, (evento, estado_antes) in enumerate(
        zip(eventos_atuador, estados_antes)
    ):
        for chave_interna in evento.chaves_saidas:
            chave = _rotulo_equacao(chave_interna)
            equacao = resultado.equacoes_comandos[chave]
            try:
                habilitada = _avaliar_equacao_binaria(
                    equacao,
                    estado_antes,
                    start=(indice == 0),
                )
            except ValueError as exc:
                falhas.append(
                    Falha("equacao_nao_avaliavel", sequencia, f"{chave}: {exc}")
                )
                return barreiras, microestados
            if not habilitada:
                falhas.append(
                    Falha(
                        "etapa_nao_habilitada",
                        sequencia,
                        f"etapa={indice}; comando={chave}; equacao={equacao}",
                    )
                )
                return barreiras, microestados

        if indice + 1 >= len(eventos_atuador) or len(etapas[indice]) <= 1:
            continue

        proximo = eventos_atuador[indice + 1]
        acoes = etapas[indice]
        for quantidade_concluida in range(1, len(acoes)):
            for concluidas in combinations(
                range(len(acoes)), quantidade_concluida
            ):
                parcial = estado_antes.copy()
                for posicao in concluidas:
                    comando = acoes[posicao]
                    parcial[comando[0]] = 1 if comando[1] == "+" else 0

                for chave_interna in proximo.chaves_saidas:
                    chave = _rotulo_equacao(chave_interna)
                    equacao = resultado.equacoes_comandos[chave]
                    microestados += 1
                    if _avaliar_equacao_binaria(
                        equacao,
                        parcial,
                        start=False,
                    ):
                        falhas.append(
                            Falha(
                                "habilitacao_prematura",
                                sequencia,
                                (
                                    f"etapa={indice}; concluidas={concluidas}; "
                                    f"proximo={chave}; equacao={equacao}; "
                                    f"estado={parcial}"
                                ),
                            )
                        )
                        return barreiras, microestados

    return barreiras, microestados


def executar() -> dict[str, object]:
    inicio = time.perf_counter()
    falhas: list[Falha] = []
    ciclos_binarios = 0
    barreiras = 0
    microestados = 0

    configuracoes = (
        ("ABC", 4),
        ("ABCD", 3),
    )
    for nomes, max_etapas in configuracoes:
        for sequencia, etapas, estados_antes in _sequencias_binarias_fechadas(
            nomes, max_etapas
        ):
            ciclos_binarios += 1
            b, m = _auditar_ciclo_binario(
                sequencia,
                etapas,
                estados_antes,
                falhas,
            )
            barreiras += b
            microestados += m

    ciclos_sequenciais = 0
    for sequencia in _sequencias_sequenciais_fechadas_3_atuadores():
        ciclos_sequenciais += 1
        try:
            resultado = resolver(sequencia)
        except Exception as exc:  # pragma: no cover
            falhas.append(Falha("excecao_sequencial", sequencia, repr(exc)))
            continue
        eventos = [
            evento.saidas
            for evento in resultado.eventos
            if evento.tipo == "atuador"
        ]
        esperado = tuple((parte.strip(),) for parte in sequencia.split(","))
        if tuple(eventos) != esperado:
            falhas.append(
                Falha(
                    "estrutura_sequencial",
                    sequencia,
                    f"esperado={esperado!r}; obtido={tuple(eventos)!r}",
                )
            )
        if "nenhum ponto perigoso permaneceu nos estados alcançáveis" not in (
            resultado.validacoes
        ):
            falhas.append(
                Falha(
                    "validacao_ponto_perigoso",
                    sequencia,
                    repr(resultado.validacoes),
                )
            )

    duracao = time.perf_counter() - inicio
    return {
        "status": "OK" if not falhas else "FALHA",
        "ciclos_binarios": ciclos_binarios,
        "ciclos_sequenciais": ciclos_sequenciais,
        "barreiras_causais_verificadas": barreiras,
        "microestados_parciais_verificados": microestados,
        "falhas": [asdict(falha) for falha in falhas],
        "duracao_segundos": round(duracao, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auditoria operacional em massa do motor de Karnaugh."
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="salva tambem o relatorio em JSON",
    )
    args = parser.parse_args()

    relatorio = executar()
    print("\n=== AUDITORIA OPERACIONAL DO MOTOR ===")
    print(f"Status: {relatorio['status']}")
    print(f"Ciclos binarios: {relatorio['ciclos_binarios']}")
    print(f"Ciclos sequenciais: {relatorio['ciclos_sequenciais']}")
    print(
        "Barreiras causais verificadas: "
        f"{relatorio['barreiras_causais_verificadas']}"
    )
    print(
        "Microestados parciais verificados: "
        f"{relatorio['microestados_parciais_verificados']}"
    )
    print(f"Falhas: {len(relatorio['falhas'])}")
    print(f"Duracao: {relatorio['duracao_segundos']} s")

    if relatorio["falhas"]:
        print("\n=== PRIMEIRAS FALHAS ===")
        for falha in relatorio["falhas"][:20]:
            print(
                f"[{falha['categoria']}] {falha['sequencia']}\n"
                f"  {falha['detalhe']}"
            )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Relatorio JSON: {args.json}")

    return 0 if relatorio["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
