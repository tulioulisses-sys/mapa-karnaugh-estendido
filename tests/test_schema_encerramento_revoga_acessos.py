from pathlib import Path


MIGRACAO = (
    Path(__file__).parents[1]
    / "supabase"
    / "migrations"
    / "202607230006_encerramento_revoga_acessos.sql"
)


def test_encerramento_sempre_revoga_os_alunos() -> None:
    sql = MIGRACAO.read_text(encoding="utf-8").casefold()

    assert "function public.encerrar_turma" in sql
    assert "v_estado_usuarios constant public.estado_conta := 'revogado'" in sql
    assert "set estado = v_estado_usuarios" in sql
    assert "usuario.papel <> 'master'" in sql
    assert "'estado_usuarios', v_estado_usuarios" in sql
    assert "p_estado_usuarios not in" not in sql
    assert "set estado = p_estado_usuarios" not in sql


def test_encerramento_preserva_historico_e_cancela_convites() -> None:
    sql = MIGRACAO.read_text(encoding="utf-8").casefold()

    assert "set ativa = false" in sql
    assert "encerrada_em = now()" in sql
    assert "update public.convites" in sql
    assert "and estado = 'pendente'" in sql
    assert "'encerrar_turma_usuario'" in sql
    assert "'encerrar_turma'" in sql
    assert "delete from public.usuarios" not in sql
