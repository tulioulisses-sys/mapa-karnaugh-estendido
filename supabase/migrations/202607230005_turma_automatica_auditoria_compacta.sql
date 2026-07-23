-- Seleção automática da turma ativa do aluno e auditoria compacta.
--
-- O aplicativo não precisa conhecer nem enviar o id da matrícula. O backend
-- continua podendo informar uma turma explicitamente, mas, quando não o faz,
-- esta função resolve a única matrícula ativa diretamente no banco.

create or replace function public.reservar_analise_com_turma_ativa(
    p_usuario_id uuid,
    p_chave_idempotencia text,
    p_turma_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_turma_id uuid := p_turma_id;
begin
    if v_turma_id is null then
        select matricula.turma_id
        into v_turma_id
        from public.matriculas as matricula
        join public.turmas as turma
          on turma.id = matricula.turma_id
        where matricula.usuario_id = p_usuario_id
          and matricula.ativa
          and turma.ativa
        order by matricula.matriculada_em desc
        limit 1;
    end if;

    return public.reservar_analise(
        p_usuario_id,
        p_chave_idempotencia,
        v_turma_id
    );
end;
$$;

revoke all on function public.reservar_analise_com_turma_ativa(
    uuid,
    text,
    uuid
) from public, anon, authenticated;

grant execute on function public.reservar_analise_com_turma_ativa(
    uuid,
    text,
    uuid
) to service_role;


-- Alguns fluxos do Supabase Auth criam o usuário antes de confirmar o e-mail.
-- Uma nova autenticação confirmada volta a executar a sincronização e conclui
-- o convite, inclusive a matrícula.

drop trigger if exists auth_login_sincronizar_convite on auth.users;
create trigger auth_login_sincronizar_convite
after update of last_sign_in_at on auth.users
for each row
when (
    new.email_confirmed_at is not null
    and old.last_sign_in_at is distinct from new.last_sign_in_at
)
execute function public.sincronizar_usuario_auth();


-- Corrige convites confirmados antes desta migração.

do $$
declare
    v_registro record;
begin
    for v_registro in
        select distinct on (usuario_auth.id)
            usuario_auth.id as usuario_id,
            convite.id as convite_id,
            convite.papel_destino,
            convite.acesso_destino,
            convite.analises_iniciais,
            convite.turma_id
        from auth.users as usuario_auth
        join public.usuarios as usuario
          on usuario.id = usuario_auth.id
        join public.convites as convite
          on lower(btrim(convite.email)) =
             lower(btrim(usuario_auth.email))
        where usuario_auth.email_confirmed_at is not null
          and convite.estado = 'pendente'
          and convite.expira_em > now()
        order by usuario_auth.id, convite.criado_em desc
    loop
        update public.usuarios
        set papel = v_registro.papel_destino,
            estado = 'ativo',
            acesso = v_registro.acesso_destino,
            analises_restantes = v_registro.analises_iniciais
        where id = v_registro.usuario_id;

        update public.convites
        set estado = 'aceito',
            aceito_por = v_registro.usuario_id
        where id = v_registro.convite_id;

        if v_registro.turma_id is not null then
            update public.matriculas
            set ativa = false,
                encerrada_em = now()
            where usuario_id = v_registro.usuario_id
              and ativa
              and turma_id <> v_registro.turma_id;

            insert into public.matriculas (usuario_id, turma_id)
            values (v_registro.usuario_id, v_registro.turma_id)
            on conflict (usuario_id, turma_id) do update
            set ativa = true,
                encerrada_em = null;
        end if;
    end loop;

    -- Recria matrículas eventualmente ausentes em convites já aceitos.
    for v_registro in
        select distinct on (convite.aceito_por)
            convite.aceito_por as usuario_id,
            convite.turma_id
        from public.convites as convite
        join public.turmas as turma
          on turma.id = convite.turma_id
        where convite.estado = 'aceito'
          and convite.aceito_por is not null
          and convite.turma_id is not null
          and turma.ativa
        order by convite.aceito_por, convite.criado_em desc
    loop
        update public.matriculas
        set ativa = false,
            encerrada_em = now()
        where usuario_id = v_registro.usuario_id
          and ativa
          and turma_id <> v_registro.turma_id;

        insert into public.matriculas (usuario_id, turma_id)
        values (v_registro.usuario_id, v_registro.turma_id)
        on conflict (usuario_id, turma_id) do update
        set ativa = true,
            encerrada_em = null;
    end loop;
end;
$$;


-- Reservas já possuem tabelas próprias para cotas e idempotência. Duplicá-las
-- na auditoria gerava quatro registros adicionais por ciclo de análise. O
-- filtro mantém apenas os eventos administrativos e de segurança.

create or replace function public.descartar_auditoria_operacional()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    if new.entidade = 'reserva_analise' then
        return null;
    end if;
    return new;
end;
$$;

drop trigger if exists auditoria_descartar_operacional
on public.auditoria;
create trigger auditoria_descartar_operacional
before insert on public.auditoria
for each row execute function public.descartar_auditoria_operacional();

-- Libera o espaço usado pela duplicação operacional anterior sem remover os
-- registros administrativos importantes.
drop trigger if exists auditoria_impedir_mutacao on public.auditoria;
delete from public.auditoria
where entidade = 'reserva_analise';
create trigger auditoria_impedir_mutacao
before update or delete on public.auditoria
for each row execute function public.impedir_mutacao_auditoria();

revoke all on function public.descartar_auditoria_operacional()
from public, anon, authenticated;
