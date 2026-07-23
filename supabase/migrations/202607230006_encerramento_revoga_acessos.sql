-- Encerrar uma turma sempre revoga o acesso de todos os alunos matriculados.
-- A assinatura anterior é preservada para manter compatibilidade com clientes
-- já instalados, mas o estado recebido deixa de controlar o resultado.

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
    v_estado_usuarios constant public.estado_conta := 'revogado';
    v_usuarios_alterados integer := 0;
    v_matriculas_encerradas integer := 0;
    v_convites_cancelados integer := 0;
begin
    perform public.papel_administrador_ativo(p_ator_id);

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
          and usuario.papel <> 'master'
          and usuario.estado <> 'revogado'
        order by usuario.id
        for update of usuario
    loop
        update public.usuarios
        set estado = v_estado_usuarios
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
                'estado', v_estado_usuarios,
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
            'estado_usuarios', v_estado_usuarios,
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
        'estado_usuarios', v_estado_usuarios,
        'usuarios_alterados', v_usuarios_alterados,
        'matriculas_encerradas', v_matriculas_encerradas,
        'convites_cancelados', v_convites_cancelados
    );
end;
$$;
