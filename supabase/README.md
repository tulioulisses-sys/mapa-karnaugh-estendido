# Banco de dados do controle de acesso

As migrações desta pasta definem o banco PostgreSQL usado pelo aplicativo.
Elas foram escritas para o Supabase, mas mantêm as regras de negócio separadas
do provedor de autenticação.

## Segurança

- Nunca coloque `service_role` ou credenciais SMTP no Flutter.
- O aplicativo usa apenas a chave pública do projeto.
- Operações administrativas passam pelo backend Python.
- As políticas RLS protegem leituras feitas pelo aplicativo.
- A criação do primeiro master será feita por um procedimento de bootstrap
  separado e auditado.

## Validação futura

Depois que o projeto Supabase for criado, a migração deverá ser executada
primeiro em um ambiente local ou de homologação:

```bash
supabase start
supabase db reset
```

O repositório ainda não contém credenciais nem está vinculado a um projeto
remoto.
