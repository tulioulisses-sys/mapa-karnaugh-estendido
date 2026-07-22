-- Cadastro automático dos usuários autenticados e criação auditada do
-- primeiro master. Esta migração não contém emails nem credenciais reais.

-- A primeira migração usou um nome diferente somente nesta coluna. A
-- padronização permite que o trigger compartilhado de atualização funcione.
alter table public.convites
    rename column atualizado_em to atualizada_em;

create or replace function public.sincronizar_usuario_auth()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_email text;
    v_email_confirmado boolean;
    v_convite public.convites%rowtype;
    v_estado_inicial public.estado_conta;
    v_papel_inicial public.papel_usuario;
    v_acesso_inicial public.tipo_acesso;
    v_analises_iniciais integer;
begin
    v_email := lower(btrim(new.email));
    if v_email is null or v_email = '' then
        raise exception 'O aplicativo exige cadastro com email.';
    end if;

    v_email_confirmado := new.email_confirmed_at is not null;

    update public.convites
    set estado = 'expirado'
    where lower(btrim(email)) = v_email
      and estado = 'pendente'
      and expira_em <= now();

    select convite.*
    into v_convite
    from public.convites as convite
    where lower(btrim(convite.email)) = v_email
      and convite.estado = 'pendente'
      and convite.expira_em > now()
    order by convite.criado_em desc
    limit 1
    for update;

    if v_convite.id is not null and v_email_confirmado then
        v_estado_inicial := 'ativo';
        v_papel_inicial := v_convite.papel_destino;
    elsif v_convite.id is not null then
        v_estado_inicial := 'convidado';
        v_papel_inicial := 'usuario';
    else
        v_estado_inicial := 'aguardando_aprovacao';
        v_papel_inicial := 'usuario';
    end if;

    if v_papel_inicial in ('master', 'submaster') then
        v_acesso_inicial := 'ilimitado';
        v_analises_iniciais := null;
    else
        v_acesso_inicial := 'limitado';
        v_analises_iniciais := 0;
    end if;

    insert into public.usuarios (
        id,
        email,
        papel,
        estado,
        acesso,
        analises_restantes
    )
    values (
        new.id,
        v_email,
        v_papel_inicial,
        v_estado_inicial,
        v_acesso_inicial,
        v_analises_iniciais
    )
    on conflict (id) do nothing;

    if tg_op = 'INSERT' then
        insert into public.auditoria (
            ator_id,
            acao,
            entidade,
            entidade_id,
            valor_posterior
        )
        values (
            new.id,
            'cadastro_criado',
            'usuario',
            new.id::text,
            jsonb_build_object(
                'email', v_email,
                'estado', v_estado_inicial,
                'origem', case
                    when v_convite.id is null then 'espontaneo'
                    else 'convite'
                end
            )
        );
    end if;

    if v_convite.id is not null and v_email_confirmado then
        update public.usuarios
        set papel = v_convite.papel_destino,
            estado = 'ativo',
            acesso = case
                when v_convite.papel_destino = 'submaster'
                    then 'ilimitado'::public.tipo_acesso
                else 'limitado'::public.tipo_acesso
            end,
            analises_restantes = case
                when v_convite.papel_destino = 'submaster' then null
                else 0
            end
        where id = new.id;

        update public.convites
        set estado = 'aceito',
            aceito_por = new.id
        where id = v_convite.id;

        if v_convite.turma_id is not null then
            insert into public.matriculas (usuario_id, turma_id)
            values (new.id, v_convite.turma_id)
            on conflict (usuario_id, turma_id) do update
            set ativa = true,
                encerrada_em = null;
        end if;

        insert into public.auditoria (
            ator_id,
            acao,
            entidade,
            entidade_id,
            valor_posterior
        )
        values (
            new.id,
            'convite_aceito',
            'convite',
            v_convite.id::text,
            jsonb_build_object(
                'email', v_email,
                'papel', v_convite.papel_destino,
                'turma_id', v_convite.turma_id
            )
        );
    end if;

    return new;
end;
$$;

create trigger auth_usuario_criado
after insert on auth.users
for each row execute function public.sincronizar_usuario_auth();

create trigger auth_email_confirmado
after update of email_confirmed_at on auth.users
for each row
when (
    old.email_confirmed_at is null
    and new.email_confirmed_at is not null
)
execute function public.sincronizar_usuario_auth();

create or replace function public.bootstrap_primeiro_master(p_email text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_email text;
    v_auth_id uuid;
    v_email_confirmado_em timestamptz;
    v_valor_anterior jsonb;
begin
    v_email := lower(btrim(p_email));
    if v_email is null or v_email = '' then
        raise exception 'Informe o email verificado do primeiro master.';
    end if;

    -- Serializa tentativas concorrentes de bootstrap. O índice parcial da
    -- primeira migração permanece como uma segunda barreira de segurança.
    perform pg_advisory_xact_lock(
        hashtextextended('mapa-karnaugh-bootstrap-master', 0)
    );

    if exists (
        select 1
        from public.usuarios
        where papel = 'master'
    ) then
        raise exception 'O sistema já possui um master.';
    end if;

    select usuario_auth.id, usuario_auth.email_confirmed_at
    into v_auth_id, v_email_confirmado_em
    from auth.users as usuario_auth
    where lower(btrim(usuario_auth.email)) = v_email
    order by usuario_auth.created_at
    limit 1
    for update;

    if v_auth_id is null then
        raise exception 'Crie primeiro a conta de autenticação desse email.';
    end if;

    if v_email_confirmado_em is null then
        raise exception 'Confirme o email antes de criar o primeiro master.';
    end if;

    select jsonb_build_object(
        'papel', usuario.papel,
        'estado', usuario.estado,
        'acesso', usuario.acesso,
        'analises_restantes', usuario.analises_restantes
    )
    into v_valor_anterior
    from public.usuarios as usuario
    where usuario.id = v_auth_id;

    insert into public.usuarios (
        id,
        email,
        papel,
        estado,
        acesso,
        analises_restantes
    )
    values (
        v_auth_id,
        v_email,
        'master',
        'ativo',
        'ilimitado',
        null
    )
    on conflict (id) do update
    set email = excluded.email,
        papel = excluded.papel,
        estado = excluded.estado,
        acesso = excluded.acesso,
        analises_restantes = excluded.analises_restantes;

    insert into public.auditoria (
        ator_id,
        acao,
        entidade,
        entidade_id,
        valor_anterior,
        valor_posterior
    )
    values (
        v_auth_id,
        'bootstrap_master',
        'usuario',
        v_auth_id::text,
        v_valor_anterior,
        jsonb_build_object(
            'email', v_email,
            'papel', 'master',
            'estado', 'ativo',
            'acesso', 'ilimitado'
        )
    );

    return v_auth_id;
end;
$$;

revoke all on function public.sincronizar_usuario_auth()
from public, anon, authenticated;

revoke all on function public.bootstrap_primeiro_master(text)
from public, anon, authenticated;

grant execute on function public.bootstrap_primeiro_master(text)
to service_role;
