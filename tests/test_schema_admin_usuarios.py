from pathlib import Path

import pytest


MIGRACAO = (
    Path(__file__).parents[1]
    / "supabase"
    / "migrations"
    / "202607230001_admin_usuarios_cotas.sql"
)


@pytest.fixture(scope="module")
def sql() -> str:
    return MIGRACAO.read_text(encoding="utf-8").casefold()


@pytest.mark.parametrize(
    "funcao",
    (
        "papel_administrador_ativo",
        "listar_usuarios_administracao",
        "alterar_estado_usuario",
        "definir_acesso_usuario",
        "ajustar_cotas_em_lote",
        "alterar_papel_usuario",
    ),
)
def test_cria_funcoes_administrativas(sql: str, funcao: str) -> None:
    assert f"create or replace function public.{funcao}" in sql


def test_funcoes_mutaveis_sao_security_definer(sql: str) -> None:
    for funcao in (
        "alterar_estado_usuario",
        "definir_acesso_usuario",
        "ajustar_cotas_em_lote",
        "alterar_papel_usuario",
    ):
        inicio = sql.index(f"create or replace function public.{funcao}")
        fim = sql.index("$$;", inicio)
        assert "security definer" in sql[inicio:fim]
        assert "set search_path = ''" in sql[inicio:fim]


def test_cliente_autenticado_nao_executa_funcoes_admin(sql: str) -> None:
    assert "to authenticated" not in sql
    assert sql.count("to service_role") == 6


def test_submaster_so_administra_alunos(sql: str) -> None:
    assert "v_ator_papel = 'submaster'" in sql
    assert "v_alvo.papel <> 'usuario'" in sql
    assert "somente o master pode gerenciar submasters" in sql


def test_master_nao_pode_ser_modificado_por_operacao_comum(
    sql: str,
) -> None:
    assert "v_alvo.papel = 'master'" in sql
    assert "o master não pode ser alterado por esta operação" in sql


def test_cotas_em_lote_distinguem_definir_e_adicionar(sql: str) -> None:
    assert "p_operacao not in ('definir', 'adicionar')" in sql
    assert "coalesce(v_alvo.analises_restantes, 0) + p_quantidade" in sql
    assert "'usuarios_alterados', v_alterados" in sql
    assert "'usuarios_ignorados', v_ignorados" in sql


def test_operacoes_administrativas_geram_auditoria(sql: str) -> None:
    assert sql.count("insert into public.auditoria") >= 4
    assert "insert into public.movimentos_cota" in sql
