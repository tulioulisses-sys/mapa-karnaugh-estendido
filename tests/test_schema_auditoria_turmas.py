from pathlib import Path

import pytest


MIGRACAO = (
    Path(__file__).parents[1]
    / "supabase"
    / "migrations"
    / "202607230004_auditoria_encerramento_turmas.sql"
)


@pytest.fixture(scope="module")
def sql() -> str:
    return MIGRACAO.read_text(encoding="utf-8").casefold()


def test_auditoria_administrativa_tem_limite_e_identifica_ator(
    sql: str,
) -> None:
    assert "function public.listar_auditoria_administracao" in sql
    assert "left join public.usuarios as ator" in sql
    assert "registro.valor_anterior" in sql
    assert "registro.valor_posterior" in sql
    assert "p_limite > 200" in sql
    assert "registro.acao not in" in sql


def test_encerramento_preserva_historico_e_bloqueia_alunos(
    sql: str,
) -> None:
    assert "function public.encerrar_turma" in sql
    assert "p_estado_usuarios not in ('suspenso', 'revogado')" in sql
    assert "set ativa = false" in sql
    assert "encerrada_em = now()" in sql
    assert "'encerrar_turma_usuario'" in sql
    assert "'encerrar_turma'" in sql
    assert "delete from public.turmas" not in sql
    assert "delete from public.usuarios" not in sql


def test_encerramento_cancela_convites_pendentes(sql: str) -> None:
    assert "update public.convites" in sql
    assert "and estado = 'pendente'" in sql
    assert "v_convites_cancelados" in sql


def test_cotas_em_lote_exigem_turma_ativa(sql: str) -> None:
    assert "p_turma_id uuid" in sql
    assert "matricula.turma_id = p_turma_id" in sql
    assert "matricula.ativa" in sql
    assert "turma ativa não encontrada" in sql


def test_funcoes_ficam_exclusivas_do_backend(sql: str) -> None:
    for funcao in (
        "listar_auditoria_administracao",
        "encerrar_turma",
        "ajustar_cotas_em_lote",
    ):
        assert f"function public.{funcao}" in sql
    assert sql.count("to service_role") == 3
    assert "from public, anon, authenticated" in sql
