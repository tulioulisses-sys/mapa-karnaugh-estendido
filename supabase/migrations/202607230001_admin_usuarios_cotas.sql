-- Operações administrativas seguras usadas pela API.
-- Nenhuma função desta migração é executável pelo cliente autenticado:
-- somente o backend, com a service role, pode chamá-las.

create or replace function public.papel_administrador_ativo(
    p_ator_id uuid
)
returns public.papel_usuario
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    v_papel public.papel_usuario;
begin
    select usuario.papel
    into v_papel
    from public.usuarios as usuario
    where usuario.id = p_ator_id
      and usuario.estado = 'ativo';

    if v_papel is null or v_papel not in ('master', 'submaster') then
        raise exception 'Permissão administrativa negada.';
    end if;

    return v_papel;
end;
$$;


create or replace function public.listar_usuarios_administracao(
    p_ator_id uuid
)
returns table (
    id uuid,
    email text,
    papel public.papel_usuario,
    estado public.estado_conta,
    acesso public.tipo_acesso,
    analises_restantes integer,
    criado_em timestamptz,
    atualizada_em timestamptz
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
    perform public.papel_administrador_ativo(p_ator_id);

    return query
    select
        usuario.id,
        usuario.email,
        usuario.papel,
        usuario.estado,
        usuario.acesso,
        usuario.analises_restantes,
        usuario.criado_em,
        usuario.atualizada_em
    from public.usuarios as usuario
    order by
        case usuario.estado
            when 'aguardando_aprovacao' then 0
            when 'convidado' then 1
            when 'ativo' then 2
            when 'suspenso' then 3
            else 4
        end,
        lower(usuario.email);
end;
$$;


create or replace function public.alterar_estado_usuario(
    p_ator_id uuid,
    p_usuario_id uuid,
    p_estado public.estado_conta
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_ator_papel public.papel_usuario;
    v_alvo public.usuarios%rowtype;
    v_anterior jsonb;
begin
    v_ator_papel := public.papel_administrador_ativo(p_ator_id);

    if p_usuario_id = p_ator_id then
        raise exception 'O administrador não pode alterar a própria conta.';
    end if;

    if p_estado not in ('ativo', 'suspenso', 'revogado') then
        raise exception 'Estado de conta inválido para administração.';
    end if;

    select usuario.*
    into v_alvo
    from public.usuarios as usuario
    where usuario.id = p_usuario_id
    for update;

    if not found then
        raise exception 'Usuário não encontrado.';
    end if;

    if v_alvo.papel = 'master'
       or (
           v_ator_papel = 'submaster'
           and v_alvo.papel <> 'usuario'
       ) then
        raise exception 'O administrador não pode administrar esse usuário.';
    end if;

    v_anterior := jsonb_build_object(
        'estado', v_alvo.estado,
        'papel', v_alvo.papel
    );

    update public.usuarios
    set estado = p_estado
    where id = p_usuario_id;

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
        'alterar_estado_usuario',
        'usuario',
        p_usuario_id::text,
        v_anterior,
        jsonb_build_object(
            'estado', p_estado,
            'papel', v_alvo.papel
        )
    );

    return jsonb_build_object(
        'id', p_usuario_id,
        'estado', p_estado,
        'papel', v_alvo.papel
    );
end;
$$;


create or replace function public.definir_acesso_usuario(
    p_ator_id uuid,
    p_usuario_id uuid,
    p_acesso public.tipo_acesso,
    p_analises_restantes integer
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_ator_papel public.papel_usuario;
    v_alvo public.usuarios%rowtype;
    v_novo_saldo integer;
begin
    v_ator_papel := public.papel_administrador_ativo(p_ator_id);

    if p_usuario_id = p_ator_id then
        raise exception 'O administrador não pode alterar a própria conta.';
    end if;

    select usuario.*
    into v_alvo
    from public.usuarios as usuario
    where usuario.id = p_usuario_id
    for update;

    if not found then
        raise exception 'Usuário não encontrado.';
    end if;

    if v_alvo.papel <> 'usuario'
       or (
           v_ator_papel = 'submaster'
           and v_alvo.papel <> 'usuario'
       ) then
        raise exception 'O administrador não pode administrar esse usuário.';
    end if;

    if p_acesso = 'ilimitado' then
        if p_analises_restantes is not null then
            raise exception 'O acesso ilimitado não possui saldo.';
        end if;
        v_novo_saldo := null;
    else
        if p_analises_restantes is null or p_analises_restantes < 0 then
            raise exception 'O saldo limitado deve ser maior ou igual a zero.';
        end if;
        v_novo_saldo := p_analises_restantes;
    end if;

    update public.usuarios
    set
        acesso = p_acesso,
        analises_restantes = v_novo_saldo
    where id = p_usuario_id;

    insert into public.movimentos_cota (
        usuario_id,
        tipo,
        quantidade,
        saldo_anterior,
        saldo_posterior,
        realizado_por
    )
    values (
        p_usuario_id,
        'definir',
        coalesce(v_novo_saldo, 0),
        case
            when p_acesso = 'ilimitado' then null
            else coalesce(v_alvo.analises_restantes, 0)
        end,
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
        'definir_acesso_usuario',
        'usuario',
        p_usuario_id::text,
        jsonb_build_object(
            'acesso', v_alvo.acesso,
            'analises_restantes', v_alvo.analises_restantes
        ),
        jsonb_build_object(
            'acesso', p_acesso,
            'analises_restantes', v_novo_saldo
        )
    );

    return jsonb_build_object(
        'id', p_usuario_id,
        'acesso', p_acesso,
        'analises_restantes', v_novo_saldo
    );
end;
$$;


create or replace function public.ajustar_cotas_em_lote(
    p_ator_id uuid,
    p_operacao text,
    p_quantidade integer,
    p_usuario_ids uuid[]
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

    for v_alvo in
        select usuario.*
        from public.usuarios as usuario
        where usuario.papel = 'usuario'
          and usuario.estado <> 'revogado'
          and (
              p_usuario_ids is null
              or usuario.id = any(p_usuario_ids)
          )
        order by usuario.id
        for update
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
        set
            acesso = 'limitado',
            analises_restantes = v_novo_saldo
        where id = v_alvo.id;

        insert into public.movimentos_cota (
            usuario_id,
            tipo,
            quantidade,
            saldo_anterior,
            saldo_posterior,
            realizado_por
        )
        values (
            v_alvo.id,
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
                'analises_restantes', v_alvo.analises_restantes
            ),
            jsonb_build_object(
                'acesso', 'limitado',
                'analises_restantes', v_novo_saldo,
                'operacao', p_operacao,
                'quantidade', p_quantidade
            )
        );

        v_alterados := v_alterados + 1;
    end loop;

    return jsonb_build_object(
        'operacao', p_operacao,
        'quantidade', p_quantidade,
        'usuarios_alterados', v_alterados,
        'usuarios_ignorados', v_ignorados
    );
end;
$$;


create or replace function public.alterar_papel_usuario(
    p_ator_id uuid,
    p_usuario_id uuid,
    p_papel public.papel_usuario
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_ator_papel public.papel_usuario;
    v_alvo public.usuarios%rowtype;
    v_acesso public.tipo_acesso;
    v_saldo integer;
begin
    v_ator_papel := public.papel_administrador_ativo(p_ator_id);

    if v_ator_papel <> 'master' then
        raise exception 'Somente o master pode gerenciar submasters.';
    end if;

    if p_usuario_id = p_ator_id then
        raise exception 'O administrador não pode alterar a própria conta.';
    end if;

    if p_papel not in ('usuario', 'submaster') then
        raise exception 'Papel de destino inválido.';
    end if;

    select usuario.*
    into v_alvo
    from public.usuarios as usuario
    where usuario.id = p_usuario_id
    for update;

    if not found then
        raise exception 'Usuário não encontrado.';
    end if;

    if v_alvo.papel = 'master' then
        raise exception 'O master não pode ser alterado por esta operação.';
    end if;

    if p_papel = 'submaster' then
        v_acesso := 'ilimitado';
        v_saldo := null;
    elsif v_alvo.papel = 'submaster' then
        v_acesso := 'limitado';
        v_saldo := 0;
    else
        v_acesso := v_alvo.acesso;
        v_saldo := v_alvo.analises_restantes;
    end if;

    update public.usuarios
    set
        papel = p_papel,
        estado = case
            when p_papel = 'submaster' then 'ativo'
            else estado
        end,
        acesso = v_acesso,
        analises_restantes = v_saldo
    where id = p_usuario_id;

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
        'alterar_papel_usuario',
        'usuario',
        p_usuario_id::text,
        jsonb_build_object(
            'papel', v_alvo.papel,
            'estado', v_alvo.estado,
            'acesso', v_alvo.acesso,
            'analises_restantes', v_alvo.analises_restantes
        ),
        jsonb_build_object(
            'papel', p_papel,
            'estado', case
                when p_papel = 'submaster' then 'ativo'
                else v_alvo.estado
            end,
            'acesso', v_acesso,
            'analises_restantes', v_saldo
        )
    );

    return jsonb_build_object(
        'id', p_usuario_id,
        'papel', p_papel,
        'estado', case
            when p_papel = 'submaster' then 'ativo'
            else v_alvo.estado
        end,
        'acesso', v_acesso,
        'analises_restantes', v_saldo
    );
end;
$$;


revoke all on function public.papel_administrador_ativo(uuid) from public;
revoke all on function public.listar_usuarios_administracao(uuid) from public;
revoke all on function public.alterar_estado_usuario(
    uuid,
    uuid,
    public.estado_conta
) from public;
revoke all on function public.definir_acesso_usuario(
    uuid,
    uuid,
    public.tipo_acesso,
    integer
) from public;
revoke all on function public.ajustar_cotas_em_lote(
    uuid,
    text,
    integer,
    uuid[]
) from public;
revoke all on function public.alterar_papel_usuario(
    uuid,
    uuid,
    public.papel_usuario
) from public;

grant execute on function public.papel_administrador_ativo(uuid)
to service_role;
grant execute on function public.listar_usuarios_administracao(uuid)
to service_role;
grant execute on function public.alterar_estado_usuario(
    uuid,
    uuid,
    public.estado_conta
) to service_role;
grant execute on function public.definir_acesso_usuario(
    uuid,
    uuid,
    public.tipo_acesso,
    integer
) to service_role;
grant execute on function public.ajustar_cotas_em_lote(
    uuid,
    text,
    integer,
    uuid[]
) to service_role;
grant execute on function public.alterar_papel_usuario(
    uuid,
    uuid,
    public.papel_usuario
) to service_role;
