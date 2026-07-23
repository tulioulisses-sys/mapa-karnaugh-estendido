-- Histórico administrativo visível e encerramento seguro de turmas.
-- As operações continuam exclusivas do backend com service role.

create or replace function public.listar_auditoria_administracao(
    p_ator_id uuid,
    p_limite integer
)
returns table (
    id bigint,
    ator_id uuid,
    ator_email text,
    acao text,
    entidade text,
    entidade_id text,
    valor_anterior jsonb,
    valor_posterior jsonb,
    criada_em timestamptz
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
    perform public.papel_administrador_ativo(p_ator_id);

    if p_limite is null or p_limite < 1 or p_limite > 200 then
        raise exception 'O limite da auditoria deve estar entre 1 e 200.';
    end if;

    return query
    select
        registro.id,
        registro.ator_id,
        ator.email,
        registro.acao,
        registro.entidade,
        registro.entidade_id,
        registro.valor_anterior,
        registro.valor_posterior,
        registro.criada_em
    from public.auditoria as registro
    left join public.usuarios as ator
      on ator.id = registro.ator_id
    where registro.acao not in (
        'analise_reservada',
        'analise_consumida',
        'analise_estornada',
        'reserva_expirada'
    )
    order by registro.criada_em desc, registro.id desc
    limit p_limite;
end;
$$;


create or replace function public.encerrar_turma(
    p_ator_id uuid,
    p_turma_id uuid,
    p_estado_usuarios public.estado_conta
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_turma public.turmas%rowtype;
    v_alvo record;
    v_usuarios_alterados integer := 0;
    v_matriculas_encerradas integer := 0;
    v_convites_cancelados integer := 0;
begin
    perform public.papel_administrador_ativo(p_ator_id);

    if p_estado_usuarios not in ('suspenso', 'revogado') then
        raise exception 'Estado de encerramento da turma inválido.';
    end if;

    select turma.*
    into v_turma
    from public.turmas as turma
    where turma.id = p_turma_id
    for update;

    if not found then
        raise exception 'Turma não encontrada.';
    end if;
    if not v_turma.ativa then
        raise exception 'A turma já está encerrada.';
    end if;

    for v_alvo in
        select
            usuario.id,
            usuario.estado,
            usuario.email
        from public.matriculas as matricula
        join public.usuarios as usuario
          on usuario.id = matricula.usuario_id
        where matricula.turma_id = p_turma_id
          and matricula.ativa
          and usuario.papel = 'usuario'
          and usuario.estado <> 'revogado'
        order by usuario.id
        for update of usuario
    loop
        update public.usuarios
        set estado = p_estado_usuarios
        where id = v_alvo.id;

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
            'encerrar_turma_usuario',
            'usuario',
            v_alvo.id::text,
            jsonb_build_object(
                'estado', v_alvo.estado,
                'turma_id', p_turma_id,
                'email', v_alvo.email
            ),
            jsonb_build_object(
                'estado', p_estado_usuarios,
                'turma_id', p_turma_id,
                'email', v_alvo.email
            )
        );

        v_usuarios_alterados := v_usuarios_alterados + 1;
    end loop;

    update public.matriculas
    set ativa = false,
        encerrada_em = now()
    where turma_id = p_turma_id
      and ativa;
    get diagnostics v_matriculas_encerradas = row_count;

    update public.convites
    set estado = 'cancelado'
    where turma_id = p_turma_id
      and estado = 'pendente';
    get diagnostics v_convites_cancelados = row_count;

    update public.turmas
    set ativa = false
    where id = p_turma_id;

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
        'encerrar_turma',
        'turma',
        p_turma_id::text,
        jsonb_build_object(
            'codigo', v_turma.codigo,
            'nome', v_turma.nome,
            'ativa', true
        ),
        jsonb_build_object(
            'codigo', v_turma.codigo,
            'nome', v_turma.nome,
            'ativa', false,
            'estado_usuarios', p_estado_usuarios,
            'usuarios_alterados', v_usuarios_alterados,
            'matriculas_encerradas', v_matriculas_encerradas,
            'convites_cancelados', v_convites_cancelados
        )
    );

    return jsonb_build_object(
        'id', p_turma_id,
        'codigo', v_turma.codigo,
        'nome', v_turma.nome,
        'ativa', false,
        'estado_usuarios', p_estado_usuarios,
        'usuarios_alterados', v_usuarios_alterados,
        'matriculas_encerradas', v_matriculas_encerradas,
        'convites_cancelados', v_convites_cancelados
    );
end;
$$;


-- Substitui a operação global pela versão que exige uma turma explícita.
drop function if exists public.ajustar_cotas_em_lote(
    uuid,
    text,
    integer,
    uuid[]
);

create or replace function public.ajustar_cotas_em_lote(
    p_ator_id uuid,
    p_operacao text,
    p_quantidade integer,
    p_usuario_ids uuid[],
    p_turma_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_alvo public.usuarios%rowtype;
    v_novo_saldo integer;
    v_alterados integer := 0;
    v_ignorados integer := 0;
begin
    perform public.papel_administrador_ativo(p_ator_id);

    if p_operacao not in ('definir', 'adicionar') then
        raise exception 'Operação de cota inválida.';
    end if;
    if p_quantidade is null
       or p_quantidade < 0
       or (p_operacao = 'adicionar' and p_quantidade = 0) then
        raise exception 'Quantidade de cota inválida.';
    end if;
    if p_turma_id is null or not exists (
        select 1
        from public.turmas as turma
        where turma.id = p_turma_id
          and turma.ativa
    ) then
        raise exception 'Turma ativa não encontrada.';
    end if;

    for v_alvo in
        select usuario.*
        from public.usuarios as usuario
        join public.matriculas as matricula
          on matricula.usuario_id = usuario.id
        where usuario.papel = 'usuario'
          and usuario.estado <> 'revogado'
          and matricula.turma_id = p_turma_id
          and matricula.ativa
          and (
              p_usuario_ids is null
              or usuario.id = any(p_usuario_ids)
          )
        order by usuario.id
        for update of usuario
    loop
        if p_operacao = 'adicionar'
           and v_alvo.acesso = 'ilimitado' then
            v_ignorados := v_ignorados + 1;
            continue;
        end if;

        if p_operacao = 'definir' then
            v_novo_saldo := p_quantidade;
        else
            v_novo_saldo :=
                coalesce(v_alvo.analises_restantes, 0) + p_quantidade;
        end if;

        update public.usuarios
        set acesso = 'limitado',
            analises_restantes = v_novo_saldo
        where id = v_alvo.id;

        insert into public.movimentos_cota (
            usuario_id,
            turma_id,
            tipo,
            quantidade,
            saldo_anterior,
            saldo_posterior,
            realizado_por
        )
        values (
            v_alvo.id,
            p_turma_id,
            p_operacao::public.tipo_movimento_cota,
            p_quantidade,
            coalesce(v_alvo.analises_restantes, 0),
            v_novo_saldo,
            p_ator_id
        );

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
            'ajustar_cota_em_lote',
            'usuario',
            v_alvo.id::text,
            jsonb_build_object(
                'acesso', v_alvo.acesso,
                'analises_restantes', v_alvo.analises_restantes,
                'turma_id', p_turma_id
            ),
            jsonb_build_object(
                'acesso', 'limitado',
                'analises_restantes', v_novo_saldo,
                'operacao', p_operacao,
                'quantidade', p_quantidade,
                'turma_id', p_turma_id
            )
        );

        v_alterados := v_alterados + 1;
    end loop;

    return jsonb_build_object(
        'operacao', p_operacao,
        'quantidade', p_quantidade,
        'turma_id', p_turma_id,
        'usuarios_alterados', v_alterados,
        'usuarios_ignorados', v_ignorados
    );
end;
$$;


revoke all on function public.listar_auditoria_administracao(uuid, integer)
from public, anon, authenticated;
revoke all on function public.encerrar_turma(
    uuid,
    uuid,
    public.estado_conta
) from public, anon, authenticated;
revoke all on function public.ajustar_cotas_em_lote(
    uuid,
    text,
    integer,
    uuid[],
    uuid
) from public, anon, authenticated;

grant execute on function public.listar_auditoria_administracao(uuid, integer)
to service_role;
grant execute on function public.encerrar_turma(
    uuid,
    uuid,
    public.estado_conta
) to service_role;
grant execute on function public.ajustar_cotas_em_lote(
    uuid,
    text,
    integer,
    uuid[],
    uuid
) to service_role;
