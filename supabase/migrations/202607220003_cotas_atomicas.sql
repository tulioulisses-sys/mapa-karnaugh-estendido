-- Reserva, consumo, estorno e expiração atômicos das cotas de análise.
-- Todas as funções desta migração são exclusivas do backend.

create or replace function public.reservar_analise(
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
    v_usuario public.usuarios%rowtype;
    v_reserva public.reservas_analise%rowtype;
    v_saldo_anterior integer;
    v_saldo_posterior integer;
begin
    if p_usuario_id is null then
        raise exception 'O usuário da análise é obrigatório.';
    end if;

    p_chave_idempotencia := btrim(p_chave_idempotencia);
    if p_chave_idempotencia is null
       or p_chave_idempotencia = ''
       or length(p_chave_idempotencia) > 200 then
        raise exception 'A chave de idempotência é inválida.';
    end if;

    -- O bloqueio do usuário serializa reservas concorrentes e impede que duas
    -- solicitações consumam a mesma unidade da cota.
    select usuario.*
    into v_usuario
    from public.usuarios as usuario
    where usuario.id = p_usuario_id
    for update;

    if v_usuario.id is null then
        raise exception 'Usuário não encontrado.';
    end if;

    if v_usuario.estado <> 'ativo' then
        raise exception 'A conta não está ativa.';
    end if;

    select reserva.*
    into v_reserva
    from public.reservas_analise as reserva
    where reserva.usuario_id = p_usuario_id
      and reserva.chave_idempotencia = p_chave_idempotencia
    limit 1;

    if v_reserva.id is not null then
        return jsonb_build_object(
            'reserva_id', v_reserva.id,
            'estado', v_reserva.estado,
            'acesso', v_usuario.acesso,
            'analises_restantes', v_usuario.analises_restantes,
            'idempotente', true
        );
    end if;

    if v_usuario.papel = 'usuario' then
        if p_turma_id is null then
            raise exception 'O usuário precisa de uma turma ativa.';
        end if;

        if not exists (
            select 1
            from public.matriculas as matricula
            join public.turmas as turma
              on turma.id = matricula.turma_id
            where matricula.usuario_id = p_usuario_id
              and matricula.turma_id = p_turma_id
              and matricula.ativa
              and turma.ativa
        ) then
            raise exception 'O usuário não pertence à turma ativa informada.';
        end if;
    end if;

    v_saldo_anterior := v_usuario.analises_restantes;
    v_saldo_posterior := v_saldo_anterior;

    if v_usuario.acesso = 'limitado' then
        if v_saldo_anterior is null or v_saldo_anterior <= 0 then
            raise exception 'O usuário não possui análises disponíveis.';
        end if;

        v_saldo_posterior := v_saldo_anterior - 1;
        update public.usuarios
        set analises_restantes = v_saldo_posterior
        where id = p_usuario_id;
    end if;

    insert into public.reservas_analise (
        usuario_id,
        turma_id,
        chave_idempotencia,
        expira_em
    )
    values (
        p_usuario_id,
        p_turma_id,
        p_chave_idempotencia,
        now() + interval '15 minutes'
    )
    returning * into v_reserva;

    insert into public.movimentos_cota (
        usuario_id,
        turma_id,
        reserva_id,
        tipo,
        quantidade,
        saldo_anterior,
        saldo_posterior,
        realizado_por
    )
    values (
        p_usuario_id,
        p_turma_id,
        v_reserva.id,
        'reservar',
        1,
        v_saldo_anterior,
        v_saldo_posterior,
        p_usuario_id
    );

    insert into public.auditoria (
        ator_id,
        acao,
        entidade,
        entidade_id,
        valor_posterior,
        requisicao_id
    )
    values (
        p_usuario_id,
        'analise_reservada',
        'reserva_analise',
        v_reserva.id::text,
        jsonb_build_object(
            'turma_id', p_turma_id,
            'acesso', v_usuario.acesso,
            'analises_restantes', v_saldo_posterior,
            'expira_em', v_reserva.expira_em
        ),
        p_chave_idempotencia
    );

    return jsonb_build_object(
        'reserva_id', v_reserva.id,
        'estado', v_reserva.estado,
        'acesso', v_usuario.acesso,
        'analises_restantes', v_saldo_posterior,
        'idempotente', false
    );
end;
$$;

create or replace function public.consumir_reserva_analise(p_reserva_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_reserva public.reservas_analise%rowtype;
    v_usuario public.usuarios%rowtype;
begin
    select reserva.*
    into v_reserva
    from public.reservas_analise as reserva
    where reserva.id = p_reserva_id
    for update;

    if v_reserva.id is null then
        raise exception 'Reserva não encontrada.';
    end if;

    select usuario.*
    into v_usuario
    from public.usuarios as usuario
    where usuario.id = v_reserva.usuario_id
    for update;

    if v_reserva.estado = 'consumida' then
        return jsonb_build_object(
            'reserva_id', v_reserva.id,
            'estado', v_reserva.estado,
            'analises_restantes', v_usuario.analises_restantes,
            'idempotente', true
        );
    end if;

    if v_reserva.estado <> 'reservada' then
        raise exception 'A reserva não pode mais ser consumida.';
    end if;

    update public.reservas_analise
    set estado = 'consumida',
        finalizada_em = now()
    where id = v_reserva.id;

    insert into public.movimentos_cota (
        usuario_id,
        turma_id,
        reserva_id,
        tipo,
        quantidade,
        saldo_anterior,
        saldo_posterior,
        realizado_por
    )
    values (
        v_reserva.usuario_id,
        v_reserva.turma_id,
        v_reserva.id,
        'consumir',
        1,
        v_usuario.analises_restantes,
        v_usuario.analises_restantes,
        v_reserva.usuario_id
    );

    insert into public.auditoria (
        ator_id,
        acao,
        entidade,
        entidade_id,
        valor_posterior,
        requisicao_id
    )
    values (
        v_reserva.usuario_id,
        'analise_consumida',
        'reserva_analise',
        v_reserva.id::text,
        jsonb_build_object(
            'estado', 'consumida',
            'analises_restantes', v_usuario.analises_restantes
        ),
        v_reserva.chave_idempotencia
    );

    return jsonb_build_object(
        'reserva_id', v_reserva.id,
        'estado', 'consumida',
        'analises_restantes', v_usuario.analises_restantes,
        'idempotente', false
    );
end;
$$;

create or replace function public.estornar_reserva_analise(
    p_reserva_id uuid,
    p_motivo text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_reserva public.reservas_analise%rowtype;
    v_usuario public.usuarios%rowtype;
    v_saldo_anterior integer;
    v_saldo_posterior integer;
begin
    p_motivo := btrim(p_motivo);
    if p_motivo is null or p_motivo = '' or length(p_motivo) > 100 then
        raise exception 'O motivo do estorno é inválido.';
    end if;

    select reserva.*
    into v_reserva
    from public.reservas_analise as reserva
    where reserva.id = p_reserva_id
    for update;

    if v_reserva.id is null then
        raise exception 'Reserva não encontrada.';
    end if;

    select usuario.*
    into v_usuario
    from public.usuarios as usuario
    where usuario.id = v_reserva.usuario_id
    for update;

    if v_reserva.estado in ('estornada', 'expirada') then
        return jsonb_build_object(
            'reserva_id', v_reserva.id,
            'estado', v_reserva.estado,
            'analises_restantes', v_usuario.analises_restantes,
            'idempotente', true
        );
    end if;

    if v_reserva.estado = 'consumida' then
        raise exception 'Uma análise consumida não pode ser estornada automaticamente.';
    end if;

    v_saldo_anterior := v_usuario.analises_restantes;
    v_saldo_posterior := v_saldo_anterior;

    if v_usuario.acesso = 'limitado' then
        v_saldo_posterior := v_saldo_anterior + 1;
        update public.usuarios
        set analises_restantes = v_saldo_posterior
        where id = v_usuario.id;
    end if;

    update public.reservas_analise
    set estado = 'estornada',
        finalizada_em = now()
    where id = v_reserva.id;

    insert into public.movimentos_cota (
        usuario_id,
        turma_id,
        reserva_id,
        tipo,
        quantidade,
        saldo_anterior,
        saldo_posterior,
        realizado_por
    )
    values (
        v_reserva.usuario_id,
        v_reserva.turma_id,
        v_reserva.id,
        'estornar',
        1,
        v_saldo_anterior,
        v_saldo_posterior,
        v_reserva.usuario_id
    );

    insert into public.auditoria (
        ator_id,
        acao,
        entidade,
        entidade_id,
        valor_posterior,
        requisicao_id
    )
    values (
        v_reserva.usuario_id,
        'analise_estornada',
        'reserva_analise',
        v_reserva.id::text,
        jsonb_build_object(
            'estado', 'estornada',
            'motivo', p_motivo,
            'analises_restantes', v_saldo_posterior
        ),
        v_reserva.chave_idempotencia
    );

    return jsonb_build_object(
        'reserva_id', v_reserva.id,
        'estado', 'estornada',
        'analises_restantes', v_saldo_posterior,
        'idempotente', false
    );
end;
$$;

create or replace function public.expirar_reservas_analise(p_limite integer)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_reserva public.reservas_analise%rowtype;
    v_usuario public.usuarios%rowtype;
    v_saldo_anterior integer;
    v_saldo_posterior integer;
    v_total integer := 0;
begin
    if p_limite is null or p_limite < 1 or p_limite > 1000 then
        raise exception 'O limite de expiração deve estar entre 1 e 1000.';
    end if;

    for v_reserva in
        select reserva.*
        from public.reservas_analise as reserva
        where reserva.estado = 'reservada'
          and reserva.expira_em <= now()
        order by reserva.expira_em
        limit p_limite
        for update skip locked
    loop
        select usuario.*
        into v_usuario
        from public.usuarios as usuario
        where usuario.id = v_reserva.usuario_id
        for update;

        v_saldo_anterior := v_usuario.analises_restantes;
        v_saldo_posterior := v_saldo_anterior;

        if v_usuario.acesso = 'limitado' then
            v_saldo_posterior := v_saldo_anterior + 1;
            update public.usuarios
            set analises_restantes = v_saldo_posterior
            where id = v_usuario.id;
        end if;

        update public.reservas_analise
        set estado = 'expirada',
            finalizada_em = now()
        where id = v_reserva.id;

        insert into public.movimentos_cota (
            usuario_id,
            turma_id,
            reserva_id,
            tipo,
            quantidade,
            saldo_anterior,
            saldo_posterior,
            realizado_por
        )
        values (
            v_reserva.usuario_id,
            v_reserva.turma_id,
            v_reserva.id,
            'estornar',
            1,
            v_saldo_anterior,
            v_saldo_posterior,
            null
        );

        insert into public.auditoria (
            ator_id,
            acao,
            entidade,
            entidade_id,
            valor_posterior,
            requisicao_id
        )
        values (
            null,
            'reserva_expirada',
            'reserva_analise',
            v_reserva.id::text,
            jsonb_build_object(
                'estado', 'expirada',
                'analises_restantes', v_saldo_posterior
            ),
            v_reserva.chave_idempotencia
        );

        v_total := v_total + 1;
    end loop;

    return v_total;
end;
$$;

revoke all on function public.reservar_analise(uuid, text, uuid)
from public, anon, authenticated;
revoke all on function public.consumir_reserva_analise(uuid)
from public, anon, authenticated;
revoke all on function public.estornar_reserva_analise(uuid, text)
from public, anon, authenticated;
revoke all on function public.expirar_reservas_analise(integer)
from public, anon, authenticated;

grant execute on function public.reservar_analise(uuid, text, uuid)
to service_role;
grant execute on function public.consumir_reserva_analise(uuid)
to service_role;
grant execute on function public.estornar_reserva_analise(uuid, text)
to service_role;
grant execute on function public.expirar_reservas_analise(integer)
to service_role;
