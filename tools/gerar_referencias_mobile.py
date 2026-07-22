from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from src.engine import VERSAO  # noqa: E402
from src.solver import analisar_entrada, resolver_site  # noqa: E402


CAMINHO_PADRAO = (
    RAIZ_PROJETO
    / "mobile"
    / "test"
    / "fixtures"
    / "motor_referencias.json"
)

CASOS_REFERENCIA = (
    {
        "id": "simples",
        "descricao": "Sequência linear com dois atuadores",
        "sequencia": "A+, B+, B-, A-",
    },
    {
        "id": "simultaneo",
        "descricao": "Etapa com movimentos simultâneos",
        "sequencia": "A+, (B+, C+), C-, B-, A-",
    },
    {
        "id": "multiposicao",
        "descricao": "Atuador com quatro posições monitoradas",
        "sequencia": (
            "A+, B+ até b1, C+, B+ até b2, C-, "
            "B+ até b3, A-, B- até b0"
        ),
    },
    {
        "id": "loop",
        "descricao": "Trecho repetitivo controlado por entrada externa",
        "sequencia": (
            "A+, B+, [C+, D+, C-, D-] enquanto e=0, A-, B-"
        ),
    },
)


def _remover_objetos_internos(resultado: dict[str, Any]) -> dict[str, Any]:
    """Retira objetos Python que não fazem parte do contrato público."""

    serializavel = dict(resultado)
    serializavel.pop("projeto", None)
    return serializavel


def construir_referencias() -> dict[str, Any]:
    """Executa o motor Python e devolve os resultados canônicos."""

    casos: list[dict[str, Any]] = []

    for caso in CASOS_REFERENCIA:
        sequencia = str(caso["sequencia"])
        analise = _remover_objetos_internos(
            analisar_entrada(sequencia)
        )
        resolucao = _remover_objetos_internos(
            resolver_site(sequencia)
        )

        casos.append(
            {
                **caso,
                "analise": analise,
                "resolucao": resolucao,
            }
        )

    return {
        "schema_version": 1,
        "motor_python_version": VERSAO,
        "casos": casos,
    }


def gravar_referencias(caminho: Path = CAMINHO_PADRAO) -> Path:
    referencias = construir_referencias()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(
            referencias,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return caminho


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Gera resultados canônicos do motor Python para validar "
            "a implementação offline em Dart."
        )
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=CAMINHO_PADRAO,
        help="Arquivo JSON de destino.",
    )
    argumentos = parser.parse_args()

    caminho = gravar_referencias(argumentos.saida.resolve())
    print(f"Referências gravadas em: {caminho}")


if __name__ == "__main__":
    main()
