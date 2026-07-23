-- Transferência segura e atômica do controle master.
-- O master atual inicia a operação, mas continua no cargo até o destinatário
-- autenticado aceitar. A troca dos papéis ocorre em uma única transação.

create or replace function public.iniciar_transferencia_master(
    p_ator_id uuid,
    p_email_destino text,
    p_dias_validade integer default 7
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_master public.usuarios%rowtype;
    v_email text;
    v_auth_id uuid;
    v_email_confirmado_em timestamptz;
    v_usuario_destino_id uuid;
    v_transferencia_id uuid;
    v_expira_em timestamptz;
    v_envio_tipo text;
begin
    v_email := lower(btrim(p_email_destino));
    if v_email is null
       or v_email = ''
       or v_email !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' then
        raise exception 'Informe um email de destino válido.';
    end if;
    if p_dias_validade < 1 or p_dias_validade > 30 then
        raise exception 'A validade da transferência deve estar entre 1 e 30 dias.';
    end if;

    perform pg_advisory_xact_lock(
        hashtextextended('mapa-karnaugh-transferencia-master', 0)
    );

    select usuario.*
    into v_master
    from public.usuarios as usuario
    where usuario.id = p_ator_id
      and usuario.papel = 'master'
      and usuario.estado = 'ativo'
    for update;

    if v_master.id is null then
        raise exception 'Somente o master ativo pode iniciar a transferência.';
    end if;
    if lower(btrim(v_master.email)) = v_email then
        raise exception 'O master atual não pode transferir para o próprio email.';
    end if;

    update public.transferencias_master
    set estado = 'expirada'
    where estado = 'pendente'
      and expira_em <= now();

    if exists (
        select 1
        from public.transferencias_master
        where estado = 'pendente'
          and expira_em > now()
    ) then
        raise exception 'Já existe uma transferência master pendente.';
    end if;

    select usuario_auth.id, usuario_auth.email_confirmed_at
    into v_auth_id, v_email_confirmado_em
    from auth.users as usuario_auth
    where lower(btrim(usuario_auth.email)) = v_email
    order by usuario_auth.created_at
    limit 1;

    select usuario.id
    into v_usuario_destino_id
    from public.usuarios as usuario
    where lower(btrim(usuario.email)) = v_email
    limit 1;

    v_expira_em := now() + make_interval(days => p_dias_validade);

    insert into public.transferencias_master (
        master_atual_id,
        email_destino,
        usuario_destino_id,
        expira_em,
        confirmada_origem_em
    )
    values (
        p_ator_id,
        v_email,
        v_usuario_destino_id,
        v_expira_em,
        now()
    )
    returning id into v_transferencia_id;

    v_envio_tipo := case
        when v_auth_id is null then 'convite'
        when v_email_confirmado_em is null then 'confirmacao'
        else 'magic_link'
    end;

    insert into public.auditoria (
        ator_id,
        acao,
        entidade,
        entidade_id,
        valor_posterior
    )
    values (
        p_ator_id,
        'iniciar_transferencia_master',
        'transferencia_master',
        v_transferencia_id::text,
        jsonb_build_object(
            'master_atual_id', p_ator_id,
            'email_destino', v_email,
            'expira_em', v_expira_em
        )
    );

    return jsonb_build_object(
        'id', v_transferencia_id,
        'master_atual_id', p_ator_id,
        'master_atual_email', v_master.email,
        'email_destino', v_email,
        'usuario_destino_id', v_usuario_destino_id,
        'estado', 'pendente',
        'expira_em', v_expira_em,
        'sou_origem', true,
        'sou_destino', false,
        'envio_tipo', v_envio_tipo
    );
end;
$$;


create or replace function public.obter_transferencia_master(
    p_usuario_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_email_usuario text;
    v_resultado jsonb;
begin
    select lower(btrim(usuario.email))
    into v_email_usuario
    from public.usuarios as usuario
    where usuario.id = p_usuario_id;

    if v_email_usuario is null then
        return null;
    end if;

    update public.transferencias_master
    set estado = 'expirada'
    where estado = 'pendente'
      and expira_em <= now();

    select jsonb_build_object(
        'id', transferencia.id,
        'master_atual_id', transferencia.master_atual_id,
        'master_atual_email', master_atual.email,
        'email_destino', transferencia.email_destino,
        'usuario_destino_id', transferencia.usuario_destino_id,
        'estado', transferencia.estado,
        'expira_em', transferencia.expira_em,
        'sou_origem', transferencia.master_atual_id = p_usuario_id,
        'sou_destino',
            lower(btrim(transferencia.email_destino)) = v_email_usuario
    )
    into v_resultado
    from public.transferencias_master as transferencia
    join public.usuarios as master_atual
      on master_atual.id = transferencia.master_atual_id
    where transferencia.estado = 'pendente'
      and transferencia.expira_em > now()
      and (
          transferencia.master_atual_id = p_usuario_id
          or lower(btrim(transferencia.email_destino)) = v_email_usuario
      )
    order by transferencia.criada_em desc
    limit 1;

    return v_resultado;
end;
$$;


create or replace function public.cancelar_transferencia_master(
    p_ator_id uuid,
    p_transferencia_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_transferencia public.transferencias_master%rowtype;
begin
    perform pg_advisory_xact_lock(
        hashtextextended('mapa-karnaugh-transferencia-master', 0)
    );

    if not exists (
        select 1
        from public.usuarios
        where id = p_ator_id
          and papel = 'master'
          and estado = 'ativo'
    ) then
        raise exception 'Somente o master ativo pode cancelar a transferência.';
    end if;

    select transferencia.*
    into v_transferencia
    from public.transferencias_master as transferencia
    where transferencia.id = p_transferencia_id
    for update;

    if v_transferencia.id is null then
        raise exception 'Transferência master não encontrada.';
    end if;
    if v_transferencia.master_atual_id <> p_ator_id then
        raise exception 'Somente o master de origem pode cancelar a transferência.';
    end if;
    if v_transferencia.estado <> 'pendente' then
        raise exception 'A transferência master não está pendente.';
    end if;

    update public.transferencias_master
    set estado = case
            when expira_em <= now()
                then 'expirada'::public.estado_transferencia_master
            else 'cancelada'::public.estado_transferencia_master
        end
    where id = p_transferencia_id
    returning * into v_transferencia;

    insert into public.auditoria (
        ator_id,
        acao,
        entidade,
        entidade_id,
        valor_anterior,
        valor_posterior
    )
    values (
        p_ator_id,
        'cancelar_transferencia_master',
        'transferencia_master',
        p_transferencia_id::text,
        jsonb_build_object('estado', 'pendente'),
        jsonb_build_object('estado', v_transferencia.estado)
    );

    return jsonb_build_object(
        'id', v_transferencia.id,
        'estado', v_transferencia.estado
    );
end;
$$;


create or replace function public.aceitar_transferencia_master(
    p_usuario_id uuid,
    p_transferencia_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_transferencia public.transferencias_master%rowtype;
    v_master_atual public.usuarios%rowtype;
    v_destino public.usuarios%rowtype;
    v_email_confirmado_em timestamptz;
begin
    perform pg_advisory_xact_lock(
        hashtextextended('mapa-karnaugh-transferencia-master', 0)
    );

    select transferencia.*
    into v_transferencia
    from public.transferencias_master as transferencia
    where transferencia.id = p_transferencia_id
    for update;

    if v_transferencia.id is null then
        raise exception 'Transferência master não encontrada.';
    end if;
    if v_transferencia.estado <> 'pendente' then
        raise exception 'A transferência master não está pendente.';
    end if;
    if v_transferencia.expira_em <= now() then
        raise exception 'A transferência master expirou.';
    end if;

    select usuario.*
    into v_destino
    from public.usuarios as usuario
    where usuario.id = p_usuario_id
    for update;

    if v_destino.id is null
       or lower(btrim(v_destino.email))
          <> lower(btrim(v_transferencia.email_destino)) then
        raise exception 'Somente o destinatário pode aceitar a transferência.';
    end if;

    select usuario_auth.email_confirmed_at
    into v_email_confirmado_em
    from auth.users as usuario_auth
    where usuario_auth.id = p_usuario_id;

    if v_email_confirmado_em is null then
        raise exception 'O destinatário precisa confirmar o email.';
    end if;

    select usuario.*
    into v_master_atual
    from public.usuarios as usuario
    where usuario.id = v_transferencia.master_atual_id
    for update;

    if v_master_atual.id is null
       or v_master_atual.papel <> 'master'
       or v_master_atual.estado <> 'ativo' then
        raise exception 'O master de origem não está mais disponível.';
    end if;

    -- A restrição de master único exige esta ordem. Se a promoção falhar,
    -- toda a transação é revertida e o master anterior permanece no cargo.
    update public.usuarios
    set papel = 'submaster',
        estado = 'ativo',
        acesso = 'ilimitado',
        analises_restantes = null
    where id = v_master_atual.id;

    update public.usuarios
    set papel = 'master',
        estado = 'ativo',
        acesso = 'ilimitado',
        analises_restantes = null
    where id = v_destino.id;

    update public.matriculas
    set ativa = false,
        encerrada_em = now()
    where usuario_id = v_destino.id
      and ativa;

    update public.transferencias_master
    set estado = 'aceita',
        usuario_destino_id = v_destino.id,
        confirmada_destino_em = now()
    where id = v_transferencia.id;

    insert into public.auditoria (
        ator_id,
        acao,
        entidade,
        entidade_id,
        valor_anterior,
        valor_posterior
    )
    values (
        v_destino.id,
        'aceitar_transferencia_master',
        'transferencia_master',
        v_transferencia.id::text,
        jsonb_build_object(
            'master_id', v_master_atual.id,
            'master_email', v_master_atual.email
        ),
        jsonb_build_object(
            'master_id', v_destino.id,
            'master_email', v_destino.email,
            'master_anterior_papel', 'submaster'
        )
    );

    return jsonb_build_object(
        'id', v_transferencia.id,
        'estado', 'aceita',
        'novo_master_id', v_destino.id,
        'master_anterior_id', v_master_atual.id
    );
end;
$$;


revoke all on function public.iniciar_transferencia_master(
    uuid, text, integer
) from public, anon, authenticated;
revoke all on function public.obter_transferencia_master(uuid)
from public, anon, authenticated;
revoke all on function public.cancelar_transferencia_master(uuid, uuid)
from public, anon, authenticated;
revoke all on function public.aceitar_transferencia_master(uuid, uuid)
from public, anon, authenticated;

grant execute on function public.iniciar_transferencia_master(
    uuid, text, integer
) to service_role;
grant execute on function public.obter_transferencia_master(uuid)
to service_role;
grant execute on function public.cancelar_transferencia_master(uuid, uuid)
to service_role;
grant execute on function public.aceitar_transferencia_master(uuid, uuid)
to service_role;
