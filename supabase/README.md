# Banco de dados do controle de acesso

As migrações desta pasta definem o banco PostgreSQL usado pelo aplicativo.
Elas foram escritas para o Supabase, mas mantêm as regras de negócio separadas
do provedor de autenticação.

## Segurança

- Nunca coloque `service_role` ou credenciais SMTP no Flutter.
- O aplicativo usa apenas a chave pública do projeto.
- Operações administrativas passam pelo backend Python.
- As políticas RLS protegem leituras feitas pelo aplicativo.
- A criação do primeiro master usa um procedimento de bootstrap separado,
  restrito ao backend e registrado na auditoria.

## Ordem das migrações

1. `202607220001_controle_acesso.sql`: tabelas, restrições e RLS;
2. `202607220002_cadastro_e_bootstrap.sql`: sincronização do Auth, aceite de
   convites após a confirmação do email e bootstrap do primeiro master.

Cadastros sem convite entram como `aguardando_aprovacao`. Um convite válido
só é aceito quando o mesmo endereço aparece confirmado no Supabase Auth.

O bootstrap exige que a conta já exista e que o email esteja confirmado. Ele
recusa novas execuções assim que existe um master e nunca deve ser chamado
diretamente pelo Flutter.

## Validação futura

Depois que o projeto Supabase for criado, a migração deverá ser executada
primeiro em um ambiente local ou de homologação:

```bash
supabase start
supabase db reset
```

O repositório não contém credenciais nem identificadores de projetos remotos.
