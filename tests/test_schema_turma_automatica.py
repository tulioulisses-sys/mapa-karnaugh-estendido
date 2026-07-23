from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
MIGRACAO = (
    RAIZ
    / "supabase"
    / "migrations"
    / "202607230005_turma_automatica_auditoria_compacta.sql"
)


def _sql() -> str:
    return MIGRACAO.read_text(encoding="utf-8").lower()


def test_reserva_descobre_matricula_ativa_sem_expor_id_ao_app() -> None:
    sql = _sql()

    assert "function public.reservar_analise_com_turma_ativa" in sql
    assert "from public.matriculas as matricula" in sql
    assert "and matricula.ativa" in sql
    assert "and turma.ativa" in sql
    assert "return public.reservar_analise(" in sql
    assert (
        "grant execute on function "
        "public.reservar_analise_com_turma_ativa" in sql
    )


def test_login_confirmado_reprocessa_convite_e_matricula() -> None:
    sql = _sql()

    assert "create trigger auth_login_sincronizar_convite" in sql
    assert "after update of last_sign_in_at on auth.users" in sql
    assert "execute function public.sincronizar_usuario_auth()" in sql
    assert "convite.estado = 'pendente'" in sql
    assert "usuario_auth.email_confirmed_at is not null" in sql
    assert "insert into public.matriculas" in sql
    assert "on conflict (usuario_id, turma_id) do update" in sql


def test_auditoria_descarta_apenas_eventos_operacionais_de_analise() -> None:
    sql = _sql()

    assert "function public.descartar_auditoria_operacional" in sql
    assert "if new.entidade = 'reserva_analise'" in sql
    assert "return null;" in sql
    assert "before insert on public.auditoria" in sql
    assert "delete from public.auditoria" in sql
    assert "where entidade = 'reserva_analise'" in sql
    assert "create trigger auditoria_impedir_mutacao" in sql
