from src.solver import analisar_entrada, resolver_site


def test_atuador_multiposicao(sequencia_multiposicao: str) -> None:
    entrada = analisar_entrada(sequencia_multiposicao)
    resultado = resolver_site(sequencia_multiposicao)

    assert entrada["sensores_por_atuador"]["B"] == ["b0", "b1", "b2", "b3"]
    assert entrada["etapas"] == [
        ["A+"],
        ["B+(1)"],
        ["C+"],
        ["B+(2)"],
        ["C-"],
        ["B+(3)"],
        ["A-"],
        ["B-"],
    ]
    assert resultado["equacoes_comandos"]["B+(1)"] == "a1.c0.b1'"
    assert resultado["equacoes_comandos"]["B+(2)"] == "c1.b2'"
    assert resultado["equacoes_comandos"]["B+(3)"] == "c0.b2"


def test_loop_condicional(sequencia_loop: str) -> None:
    entrada = analisar_entrada(sequencia_loop)
    resultado = resolver_site(sequencia_loop)

    assert entrada["entradas_externas"] == ["e"]
    assert entrada["possui_loop"] is True
    assert entrada["loops"][0]["condicao_repeticao"] == {"e": 0}
    assert entrada["loops"][0]["condicao_saida"] == {"e": 1}
    assert resultado["equacoes_comandos"]["C+"] == "b1.e'.d0"
    assert resultado["equacoes_comandos"]["A-"] == "d0.e.b1"

