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
   convites após a confirmação do email e bootstrap do primeiro master;
3. `202607220003_cotas_atomicas.sql`: reserva idempotente, consumo, estorno e
   expiração de análises;
4. `202607230001_admin_usuarios_cotas.sql`: administração segura de contas,
   papéis e cotas;
5. `202607230002_turmas_convites.sql`: turmas, convites em lote, perfil e cota
   inicial aplicados após a confirmação do endereço;
6. `202607230003_transferencia_master.sql`: transferência segura da conta
   master;
7. `202607230004_auditoria_encerramento_turmas.sql`: auditoria e encerramento
   transacional das turmas;
8. `202607230005_turma_automatica_auditoria_compacta.sql`: reconciliação das
   matrículas e compactação da auditoria;
9. `202607230006_encerramento_revoga_acessos.sql`: revogação automática de
   todas as contas vinculadas quando uma turma é encerrada.

Cadastros sem convite entram como `aguardando_aprovacao`. Um convite válido
só é aceito quando o mesmo endereço aparece confirmado no Supabase Auth.

O bootstrap exige que a conta já exista e que o email esteja confirmado. Ele
recusa novas execuções assim que existe um master e nunca deve ser chamado
diretamente pelo Flutter.

## Ciclo seguro das análises

O backend reserva uma unidade antes de chamar o motor Python. Uma chave de
idempotência impede desconto duplicado quando a mesma requisição é repetida.
O sucesso consome a reserva; uma falha interna ou expiração devolve a unidade.
Usuários comuns também precisam estar matriculados em uma turma ativa.

Essas operações usam bloqueios transacionais no PostgreSQL e só podem ser
executadas pelo `service_role` mantido no backend. A chave correspondente
nunca pode ser enviada ao Flutter.

## Envio dos convites

A API cria primeiro a autorização auditada no banco e depois solicita o envio
ao Supabase Auth. Configure `APP_PUBLIC_URL` no servidor para que o link do
email leve à versão publicada do aplicativo. Em desenvolvimento, o valor pode
ser `http://localhost:3000`.

Para uso com turmas reais, configure um SMTP próprio no painel do Supabase.
A chave SMTP e a `SUPABASE_SECRET_KEY` pertencem somente ao ambiente do
backend; nenhuma delas entra no `mobile/config/dev.json`.

## Validação futura

Depois que o projeto Supabase for criado, a migração deverá ser executada
primeiro em um ambiente local ou de homologação:

```bash
supabase start
supabase db reset
```

O repositório não contém credenciais nem identificadores de projetos remotos.
