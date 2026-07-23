-- Turmas e convites em lote com perfil e cota inicial.
-- O envio do email é feito pela API por meio do Supabase Auth; esta migração
-- mantém a autorização, a matrícula e a auditoria no banco de dados.

alter table public.convites
    add column acesso_destino public.tipo_acesso not null default 'limitado',
    add column analises_iniciais integer default 0;

update public.convites
set acesso_destino = 'ilimitado',
    analises_iniciais = null
where papel_destino = 'submaster';

alter table public.convites
    add constraint convites_cota_inicial_coerente_ck check (
        (
            acesso_destino = 'ilimitado'
            and analises_iniciais is null
        )
        or
        (
            acesso_destino = 'limitado'
            and analises_iniciais is not null
            and analises_iniciais >= 0
        )
    ),
    add constraint convites_admin_ilimitado_ck check (
        papel_destino = 'usuario'
        or (
            acesso_destino = 'ilimitado'
            and analises_iniciais is null
        )
    );


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
        v_acesso_inicial := v_convite.acesso_destino;
        v_analises_iniciais := v_convite.analises_iniciais;
    elsif v_convite.id is not null then
        v_estado_inicial := 'convidado';
        v_papel_inicial := 'usuario';
        v_acesso_inicial := 'limitado';
        v_analises_iniciais := 0;
    else
        v_estado_inicial := 'aguardando_aprovacao';
        v_papel_inicial := 'usuario';
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
    on conflict (id) do update
    set email = excluded.email;

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
            acesso = v_convite.acesso_destino,
            analises_restantes = v_convite.analises_iniciais
        where id = new.id;

        update public.convites
        set estado = 'aceito',
            aceito_por = new.id
        where id = v_convite.id;

        if v_convite.turma_id is not null then
            update public.matriculas
            set ativa = false,
                encerrada_em = now()
            where usuario_id = new.id
              and ativa
              and turma_id <> v_convite.turma_id;

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
                'acesso', v_convite.acesso_destino,
                'analises_iniciais', v_convite.analises_iniciais,
                'turma_id', v_convite.turma_id
            )
        );
    end if;

    return new;
end;
$$;


create or replace function public.listar_turmas_administracao(
    p_ator_id uuid
)
returns table (
    id uuid,
    codigo text,
    nome text,
    ativa boolean,
    quantidade_alunos bigint,
    criada_em timestamptz,
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
        turma.id,
        turma.codigo,
        turma.nome,
        turma.ativa,
        count(matricula.usuario_id) filter (where matricula.ativa),
        turma.criada_em,
        turma.atualizada_em
    from public.turmas as turma
    left join public.matriculas as matricula
      on matricula.turma_id = turma.id
    group by turma.id
    order by turma.ativa desc, lower(turma.codigo);
end;
$$;


create or replace function public.criar_turma(
    p_ator_id uuid,
    p_codigo text,
    p_nome text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_turma public.turmas%rowtype;
begin
    perform public.papel_administrador_ativo(p_ator_id);

    if btrim(coalesce(p_codigo, '')) = ''
       or char_length(btrim(p_codigo)) > 40 then
        raise exception 'Código de turma inválido.';
    end if;
    if btrim(coalesce(p_nome, '')) = ''
       or char_length(btrim(p_nome)) > 120 then
        raise exception 'Nome de turma inválido.';
    end if;

    insert into public.turmas (codigo, nome, criada_por)
    values (btrim(p_codigo), btrim(p_nome), p_ator_id)
    returning * into v_turma;

    insert into public.auditoria (
        ator_id,
        acao,
        entidade,
        entidade_id,
        valor_posterior
    )
    values (
        p_ator_id,
        'criar_turma',
        'turma',
        v_turma.id::text,
        jsonb_build_object(
            'codigo', v_turma.codigo,
            'nome', v_turma.nome
        )
    );

    return jsonb_build_object(
        'id', v_turma.id,
        'codigo', v_turma.codigo,
        'nome', v_turma.nome,
        'ativa', v_turma.ativa,
        'quantidade_alunos', 0
    );
end;
$$;


create or replace function public.criar_convites_em_lote(
    p_ator_id uuid,
    p_emails text[],
    p_papel_destino public.papel_usuario,
    p_acesso_destino public.tipo_acesso,
    p_analises_iniciais integer,
    p_turma_id uuid,
    p_dias_validade integer
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_ator_papel public.papel_usuario;
    v_email text;
    v_usuario public.usuarios%rowtype;
    v_auth_id uuid;
    v_email_confirmado_em timestamptz;
    v_convite_id uuid;
    v_envio_tipo text;
    v_resultados jsonb := '[]'::jsonb;
    v_total integer := 0;
begin
    v_ator_papel := public.papel_administrador_ativo(p_ator_id);

    if coalesce(cardinality(p_emails), 0) = 0
       or cardinality(p_emails) > 300 then
        raise exception 'A lista deve possuir entre 1 e 300 emails.';
    end if;
    if p_papel_destino not in ('usuario', 'submaster') then
        raise exception 'Papel de destino inválido.';
    end if;
    if v_ator_papel = 'submaster' and p_papel_destino <> 'usuario' then
        raise exception 'Somente o master pode convidar submasters.';
    end if;
    if p_dias_validade is null or p_dias_validade < 1
       or p_dias_validade > 30 then
        raise exception 'A validade do convite deve estar entre 1 e 30 dias.';
    end if;
    if p_papel_destino = 'submaster' then
        if p_acesso_destino <> 'ilimitado'
           or p_analises_iniciais is not null then
            raise exception 'Submaster deve possuir acesso ilimitado.';
        end if;
    elsif p_acesso_destino = 'ilimitado' then
        if p_analises_iniciais is not null then
            raise exception 'O acesso ilimitado não possui saldo.';
        end if;
    elsif p_analises_iniciais is null or p_analises_iniciais < 0 then
        raise exception 'Informe uma cota inicial válida.';
    end if;

    if p_turma_id is not null and not exists (
        select 1
        from public.turmas as turma
        where turma.id = p_turma_id
          and turma.ativa
    ) then
        raise exception 'Turma ativa não encontrada.';
    end if;

    for v_email in
        select distinct lower(btrim(item.email))
        from unnest(p_emails) as item(email)
        where btrim(coalesce(item.email, '')) <> ''
        order by lower(btrim(item.email))
    loop
        if v_email !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
           or char_length(v_email) > 254 then
            raise exception 'Email inválido: %.', v_email;
        end if;

        select usuario.*
        into v_usuario
        from public.usuarios as usuario
        where lower(btrim(usuario.email)) = v_email
        for update;

        select usuario_auth.id, usuario_auth.email_confirmed_at
        into v_auth_id, v_email_confirmado_em
        from auth.users as usuario_auth
        where lower(btrim(usuario_auth.email)) = v_email
        order by usuario_auth.created_at
        limit 1;

        if v_usuario.id is not null and v_usuario.papel = 'master' then
            raise exception 'O master não pode receber esse convite.';
        end if;
        if v_ator_papel = 'submaster'
           and v_usuario.id is not null
           and v_usuario.papel <> 'usuario' then
            raise exception 'O submaster não pode administrar esse usuário.';
        end if;

        update public.convites
        set estado = 'cancelado'
        where lower(btrim(email)) = v_email
          and estado = 'pendente';

        if v_usuario.id is not null
           and v_email_confirmado_em is not null then
            update public.usuarios
            set papel = p_papel_destino,
                estado = 'ativo',
                acesso = p_acesso_destino,
                analises_restantes = p_analises_iniciais
            where id = v_usuario.id;

            if p_turma_id is not null then
                update public.matriculas
                set ativa = false,
                    encerrada_em = now()
                where usuario_id = v_usuario.id
                  and ativa
                  and turma_id <> p_turma_id;

                insert into public.matriculas (usuario_id, turma_id)
                values (v_usuario.id, p_turma_id)
                on conflict (usuario_id, turma_id) do update
                set ativa = true,
                    encerrada_em = null;
            end if;

            insert into public.convites (
                email,
                papel_destino,
                acesso_destino,
                analises_iniciais,
                turma_id,
                estado,
                convidado_por,
                aceito_por,
                expira_em
            )
            values (
                v_email,
                p_papel_destino,
                p_acesso_destino,
                p_analises_iniciais,
                p_turma_id,
                'aceito',
                p_ator_id,
                v_usuario.id,
                now() + make_interval(days => p_dias_validade)
            )
            returning id into v_convite_id;

            v_envio_tipo := 'magic_link';
        else
            insert into public.convites (
                email,
                papel_destino,
                acesso_destino,
                analises_iniciais,
                turma_id,
                estado,
                convidado_por,
                expira_em
            )
            values (
                v_email,
                p_papel_destino,
                p_acesso_destino,
                p_analises_iniciais,
                p_turma_id,
                'pendente',
                p_ator_id,
                now() + make_interval(days => p_dias_validade)
            )
            returning id into v_convite_id;

            if v_usuario.id is not null then
                update public.usuarios
                set estado = 'convidado'
                where id = v_usuario.id;
            end if;

            v_envio_tipo := case
                when v_auth_id is null then 'convite'
                else 'confirmacao'
            end;
        end if;

        insert into public.auditoria (
            ator_id,
            acao,
            entidade,
            entidade_id,
            valor_posterior
        )
        values (
            p_ator_id,
            'criar_convite',
            'convite',
            v_convite_id::text,
            jsonb_build_object(
                'email', v_email,
                'papel', p_papel_destino,
                'acesso', p_acesso_destino,
                'analises_iniciais', p_analises_iniciais,
                'turma_id', p_turma_id,
                'envio_tipo', v_envio_tipo
            )
        );

        v_resultados := v_resultados || jsonb_build_array(
            jsonb_build_object(
                'id', v_convite_id,
                'email', v_email,
                'estado', case
                    when v_envio_tipo = 'magic_link' then 'aceito'
                    else 'pendente'
                end,
                'envio_tipo', v_envio_tipo
            )
        );
        v_total := v_total + 1;
    end loop;

    if v_total = 0 then
        raise exception 'Nenhum email válido foi informado.';
    end if;

    return jsonb_build_object(
        'total', v_total,
        'convites', v_resultados
    );
end;
$$;


create or replace function public.listar_convites_administracao(
    p_ator_id uuid
)
returns table (
    id uuid,
    email text,
    papel_destino public.papel_usuario,
    acesso_destino public.tipo_acesso,
    analises_iniciais integer,
    turma_id uuid,
    turma_codigo text,
    estado public.estado_convite,
    expira_em timestamptz,
    criado_em timestamptz
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
        convite.id,
        convite.email,
        convite.papel_destino,
        convite.acesso_destino,
        convite.analises_iniciais,
        convite.turma_id,
        turma.codigo,
        convite.estado,
        convite.expira_em,
        convite.criado_em
    from public.convites as convite
    left join public.turmas as turma
      on turma.id = convite.turma_id
    order by convite.criado_em desc;
end;
$$;


create or replace function public.cancelar_convite(
    p_ator_id uuid,
    p_convite_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_ator_papel public.papel_usuario;
    v_convite public.convites%rowtype;
begin
    v_ator_papel := public.papel_administrador_ativo(p_ator_id);

    select convite.*
    into v_convite
    from public.convites as convite
    where convite.id = p_convite_id
    for update;

    if not found then
        raise exception 'Convite não encontrado.';
    end if;
    if v_convite.estado <> 'pendente' then
        raise exception 'Somente convites pendentes podem ser cancelados.';
    end if;
    if v_ator_papel = 'submaster'
       and v_convite.papel_destino <> 'usuario' then
        raise exception 'O submaster não pode administrar esse convite.';
    end if;

    update public.convites
    set estado = 'cancelado'
    where id = p_convite_id;

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
        'cancelar_convite',
        'convite',
        p_convite_id::text,
        jsonb_build_object('estado', v_convite.estado),
        jsonb_build_object('estado', 'cancelado')
    );

    return jsonb_build_object(
        'id', p_convite_id,
        'estado', 'cancelado'
    );
end;
$$;


revoke all on function public.sincronizar_usuario_auth()
from public, anon, authenticated;
revoke all on function public.listar_turmas_administracao(uuid)
from public, anon, authenticated;
revoke all on function public.criar_turma(uuid, text, text)
from public, anon, authenticated;
revoke all on function public.criar_convites_em_lote(
    uuid,
    text[],
    public.papel_usuario,
    public.tipo_acesso,
    integer,
    uuid,
    integer
) from public, anon, authenticated;
revoke all on function public.listar_convites_administracao(uuid)
from public, anon, authenticated;
revoke all on function public.cancelar_convite(uuid, uuid)
from public, anon, authenticated;

grant execute on function public.listar_turmas_administracao(uuid)
to service_role;
grant execute on function public.criar_turma(uuid, text, text)
to service_role;
grant execute on function public.criar_convites_em_lote(
    uuid,
    text[],
    public.papel_usuario,
    public.tipo_acesso,
    integer,
    uuid,
    integer
) to service_role;
grant execute on function public.listar_convites_administracao(uuid)
to service_role;
grant execute on function public.cancelar_convite(uuid, uuid)
to service_role;
