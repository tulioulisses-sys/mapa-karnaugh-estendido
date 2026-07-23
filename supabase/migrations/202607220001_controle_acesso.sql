-- Fundação do controle de acesso do Mapa de Karnaugh Estendido.
-- As operações administrativas serão expostas por funções/backend em uma
-- migração posterior. Nesta etapa, o cliente possui somente leitura protegida
-- por RLS e não recebe privilégios de escrita direta.

create extension if not exists pgcrypto;

create type public.papel_usuario as enum (
    'master',
    'submaster',
    'usuario'
);

create type public.estado_conta as enum (
    'convidado',
    'aguardando_aprovacao',
    'ativo',
    'suspenso',
    'revogado'
);

create type public.estado_convite as enum (
    'pendente',
    'aceito',
    'expirado',
    'cancelado'
);

create type public.tipo_acesso as enum (
    'ilimitado',
    'limitado'
);

create type public.tipo_movimento_cota as enum (
    'definir',
    'adicionar',
    'reservar',
    'consumir',
    'estornar'
);

create type public.estado_reserva_analise as enum (
    'reservada',
    'consumida',
    'estornada',
    'expirada'
);

create type public.estado_transferencia_master as enum (
    'pendente',
    'aceita',
    'cancelada',
    'expirada'
);

create table public.turmas (
    id uuid primary key default gen_random_uuid(),
    codigo text not null,
    nome text not null,
    ativa boolean not null default true,
    criada_por uuid references auth.users(id) on delete restrict,
    criada_em timestamptz not null default now(),
    atualizada_em timestamptz not null default now(),
    constraint turmas_codigo_nao_vazio_ck check (btrim(codigo) <> ''),
    constraint turmas_nome_nao_vazio_ck check (btrim(nome) <> '')
);

create unique index turmas_codigo_normalizado_uk
    on public.turmas (lower(btrim(codigo)));

create table public.usuarios (
    id uuid primary key references auth.users(id) on delete restrict,
    email text not null,
    papel public.papel_usuario not null default 'usuario',
    estado public.estado_conta not null default 'aguardando_aprovacao',
    acesso public.tipo_acesso not null default 'limitado',
    analises_restantes integer default 0,
    criado_em timestamptz not null default now(),
    atualizada_em timestamptz not null default now(),
    constraint usuarios_email_nao_vazio_ck check (btrim(email) <> ''),
    constraint usuarios_cota_coerente_ck check (
        (
            acesso = 'ilimitado'
            and analises_restantes is null
        )
        or
        (
            acesso = 'limitado'
            and analises_restantes is not null
            and analises_restantes >= 0
        )
    ),
    constraint usuarios_admin_ilimitado_ck check (
        papel = 'usuario'
        or (
            acesso = 'ilimitado'
            and analises_restantes is null
        )
    )
);

create unique index usuarios_email_normalizado_uk
    on public.usuarios (lower(btrim(email)));

-- O índice garante no máximo um master. O bootstrap e a transferência
-- garantem que o sistema nunca fique sem um master ativo.
create unique index usuarios_master_unico_uk
    on public.usuarios (papel)
    where papel = 'master';

create index usuarios_estado_idx on public.usuarios (estado);

create table public.matriculas (
    usuario_id uuid not null references public.usuarios(id) on delete restrict,
    turma_id uuid not null references public.turmas(id) on delete restrict,
    ativa boolean not null default true,
    matriculada_em timestamptz not null default now(),
    encerrada_em timestamptz,
    atualizada_em timestamptz not null default now(),
    primary key (usuario_id, turma_id),
    constraint matriculas_encerramento_coerente_ck check (
        (ativa and encerrada_em is null)
        or (not ativa and encerrada_em is not null)
    )
);

create unique index matriculas_uma_turma_ativa_por_usuario_uk
    on public.matriculas (usuario_id)
    where ativa;

create index matriculas_turma_ativa_idx
    on public.matriculas (turma_id)
    where ativa;

create table public.convites (
    id uuid primary key default gen_random_uuid(),
    email text not null,
    papel_destino public.papel_usuario not null default 'usuario',
    turma_id uuid references public.turmas(id) on delete restrict,
    estado public.estado_convite not null default 'pendente',
    convidado_por uuid not null references public.usuarios(id) on delete restrict,
    aceito_por uuid references public.usuarios(id) on delete restrict,
    expira_em timestamptz not null,
    criado_em timestamptz not null default now(),
    atualizado_em timestamptz not null default now(),
    constraint convites_email_nao_vazio_ck check (btrim(email) <> ''),
    constraint convites_nao_criam_master_ck check (papel_destino <> 'master'),
    constraint convites_aceite_coerente_ck check (
        (estado = 'aceito' and aceito_por is not null)
        or (estado <> 'aceito' and aceito_por is null)
    )
);

create unique index convites_email_pendente_uk
    on public.convites (lower(btrim(email)))
    where estado = 'pendente';

create index convites_turma_idx on public.convites (turma_id);

create table public.reservas_analise (
    id uuid primary key default gen_random_uuid(),
    usuario_id uuid not null references public.usuarios(id) on delete restrict,
    turma_id uuid references public.turmas(id) on delete restrict,
    chave_idempotencia text not null,
    estado public.estado_reserva_analise not null default 'reservada',
    expira_em timestamptz not null,
    criada_em timestamptz not null default now(),
    finalizada_em timestamptz,
    atualizada_em timestamptz not null default now(),
    constraint reservas_chave_nao_vazia_ck check (
        btrim(chave_idempotencia) <> ''
    ),
    constraint reservas_finalizacao_coerente_ck check (
        (estado = 'reservada' and finalizada_em is null)
        or (estado <> 'reservada' and finalizada_em is not null)
    )
);

create unique index reservas_idempotencia_usuario_uk
    on public.reservas_analise (usuario_id, chave_idempotencia);

create index reservas_pendentes_expiracao_idx
    on public.reservas_analise (expira_em)
    where estado = 'reservada';

create table public.movimentos_cota (
    id bigint generated always as identity primary key,
    usuario_id uuid not null references public.usuarios(id) on delete restrict,
    turma_id uuid references public.turmas(id) on delete restrict,
    reserva_id uuid references public.reservas_analise(id) on delete restrict,
    tipo public.tipo_movimento_cota not null,
    quantidade integer not null,
    saldo_anterior integer,
    saldo_posterior integer,
    realizado_por uuid references public.usuarios(id) on delete restrict,
    criado_em timestamptz not null default now(),
    constraint movimentos_quantidade_coerente_ck check (
        (tipo = 'definir' and quantidade >= 0)
        or (tipo <> 'definir' and quantidade > 0)
    ),
    constraint movimentos_saldos_coerentes_ck check (
        (
            saldo_anterior is null
            and saldo_posterior is null
        )
        or
        (
            saldo_anterior is not null
            and saldo_anterior >= 0
            and saldo_posterior is not null
            and saldo_posterior >= 0
        )
    )
);

create index movimentos_cota_usuario_data_idx
    on public.movimentos_cota (usuario_id, criado_em desc);

create table public.transferencias_master (
    id uuid primary key default gen_random_uuid(),
    master_atual_id uuid not null references public.usuarios(id) on delete restrict,
    email_destino text not null,
    usuario_destino_id uuid references public.usuarios(id) on delete restrict,
    estado public.estado_transferencia_master not null default 'pendente',
    expira_em timestamptz not null,
    confirmada_origem_em timestamptz,
    confirmada_destino_em timestamptz,
    criada_em timestamptz not null default now(),
    atualizada_em timestamptz not null default now(),
    constraint transferencias_email_nao_vazio_ck check (
        btrim(email_destino) <> ''
    ),
    constraint transferencias_usuarios_diferentes_ck check (
        usuario_destino_id is null
        or usuario_destino_id <> master_atual_id
    )
);

create unique index transferencias_uma_pendente_uk
    on public.transferencias_master ((estado))
    where estado = 'pendente';

create table public.auditoria (
    id bigint generated always as identity primary key,
    ator_id uuid references public.usuarios(id) on delete restrict,
    acao text not null,
    entidade text not null,
    entidade_id text,
    valor_anterior jsonb,
    valor_posterior jsonb,
    requisicao_id text,
    criada_em timestamptz not null default now(),
    constraint auditoria_acao_nao_vazia_ck check (btrim(acao) <> ''),
    constraint auditoria_entidade_nao_vazia_ck check (btrim(entidade) <> '')
);

create index auditoria_data_idx on public.auditoria (criada_em desc);
create index auditoria_ator_data_idx
    on public.auditoria (ator_id, criada_em desc);

create or replace function public.definir_atualizada_em()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.atualizada_em = now();
    return new;
end;
$$;

create trigger turmas_definir_atualizada_em
before update on public.turmas
for each row execute function public.definir_atualizada_em();

create trigger usuarios_definir_atualizada_em
before update on public.usuarios
for each row execute function public.definir_atualizada_em();

create trigger matriculas_definir_atualizada_em
before update on public.matriculas
for each row execute function public.definir_atualizada_em();

create trigger convites_definir_atualizada_em
before update on public.convites
for each row execute function public.definir_atualizada_em();

create trigger reservas_definir_atualizada_em
before update on public.reservas_analise
for each row execute function public.definir_atualizada_em();

create trigger transferencias_definir_atualizada_em
before update on public.transferencias_master
for each row execute function public.definir_atualizada_em();

create or replace function public.impedir_mutacao_auditoria()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    raise exception 'Os registros de auditoria são imutáveis.';
end;
$$;

create trigger auditoria_impedir_mutacao
before update or delete on public.auditoria
for each row execute function public.impedir_mutacao_auditoria();

create or replace function public.papel_usuario_atual()
returns public.papel_usuario
language sql
stable
security definer
set search_path = ''
as $$
    select usuario.papel
    from public.usuarios as usuario
    where usuario.id = (select auth.uid())
      and usuario.estado = 'ativo'
    limit 1
$$;

create or replace function public.conta_ativa()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.usuarios as usuario
        where usuario.id = (select auth.uid())
          and usuario.estado = 'ativo'
    )
$$;

create or replace function public.eh_administrador()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select coalesce(
        public.papel_usuario_atual() in ('master', 'submaster'),
        false
    )
$$;

create or replace function public.eh_master()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select coalesce(public.papel_usuario_atual() = 'master', false)
$$;

revoke all on function public.definir_atualizada_em() from public;
revoke all on function public.impedir_mutacao_auditoria() from public;
revoke all on function public.papel_usuario_atual() from public;
revoke all on function public.conta_ativa() from public;
revoke all on function public.eh_administrador() from public;
revoke all on function public.eh_master() from public;

grant execute on function public.papel_usuario_atual() to authenticated;
grant execute on function public.conta_ativa() to authenticated;
grant execute on function public.eh_administrador() to authenticated;
grant execute on function public.eh_master() to authenticated;

alter table public.turmas enable row level security;
alter table public.usuarios enable row level security;
alter table public.matriculas enable row level security;
alter table public.convites enable row level security;
alter table public.reservas_analise enable row level security;
alter table public.movimentos_cota enable row level security;
alter table public.transferencias_master enable row level security;
alter table public.auditoria enable row level security;

create policy usuarios_leitura_propria_ou_admin
on public.usuarios
for select
to authenticated
using (
    id = (select auth.uid())
    or public.eh_administrador()
);

create policy turmas_leitura_conta_ativa
on public.turmas
for select
to authenticated
using (public.conta_ativa());

create policy matriculas_leitura_propria_ou_admin
on public.matriculas
for select
to authenticated
using (
    usuario_id = (select auth.uid())
    or public.eh_administrador()
);

create policy convites_leitura_admin
on public.convites
for select
to authenticated
using (public.eh_administrador());

create policy reservas_leitura_propria_ou_admin
on public.reservas_analise
for select
to authenticated
using (
    usuario_id = (select auth.uid())
    or public.eh_administrador()
);

create policy movimentos_leitura_propria_ou_admin
on public.movimentos_cota
for select
to authenticated
using (
    usuario_id = (select auth.uid())
    or public.eh_administrador()
);

create policy transferencias_leitura_master
on public.transferencias_master
for select
to authenticated
using (public.eh_master());

create policy auditoria_leitura_admin
on public.auditoria
for select
to authenticated
using (public.eh_administrador());

revoke all on table public.turmas from anon, authenticated;
revoke all on table public.usuarios from anon, authenticated;
revoke all on table public.matriculas from anon, authenticated;
revoke all on table public.convites from anon, authenticated;
revoke all on table public.reservas_analise from anon, authenticated;
revoke all on table public.movimentos_cota from anon, authenticated;
revoke all on table public.transferencias_master from anon, authenticated;
revoke all on table public.auditoria from anon, authenticated;

grant select on table public.turmas to authenticated;
grant select on table public.usuarios to authenticated;
grant select on table public.matriculas to authenticated;
grant select on table public.convites to authenticated;
grant select on table public.reservas_analise to authenticated;
grant select on table public.movimentos_cota to authenticated;
grant select on table public.transferencias_master to authenticated;
grant select on table public.auditoria to authenticated;

grant all on table public.turmas to service_role;
grant all on table public.usuarios to service_role;
grant all on table public.matriculas to service_role;
grant all on table public.convites to service_role;
grant all on table public.reservas_analise to service_role;
grant all on table public.movimentos_cota to service_role;
grant all on table public.transferencias_master to service_role;
grant all on table public.auditoria to service_role;
grant usage, select on all sequences in schema public to service_role;
