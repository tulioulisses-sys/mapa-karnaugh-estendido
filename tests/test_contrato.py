import json
from pathlib import Path

from src.solver import resolver_site


RAIZ = Path(__file__).resolve().parents[1]
SCHEMAS = RAIZ / "docs" / "schemas"


def carregar_schema(nome: str) -> dict:
    with (SCHEMAS / nome).open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def test_schemas_sao_json_valido() -> None:
    nomes = {
        "solicitacao-resolucao.schema.json",
        "resposta-resolucao.schema.json",
        "erro.schema.json",
    }

    for nome in nomes:
        schema = carregar_schema(nome)
        assert schema["$schema"].endswith("2020-12/schema")
        assert schema["type"] == "object"


def test_resultado_atual_contem_campos_obrigatorios_do_contrato() -> None:
    schema = carregar_schema("resposta-resolucao.schema.json")
    resultado = resolver_site("A+, B+, B-, A-")

    assert set(schema["required"]).issubset(resultado)


def test_resultado_do_motor_e_serializavel_em_json() -> None:
    resultado = resolver_site("A+, B+, B-, A-")

    serializado = json.dumps(resultado, ensure_ascii=False)
    assert "quantidade_memorias" in serializado
    assert "versao_motor" in serializado

