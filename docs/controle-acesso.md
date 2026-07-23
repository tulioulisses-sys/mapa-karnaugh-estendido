# Controle de acesso do aplicativo

## 1. Objetivo

Este documento define as regras permanentes de autenticação, autorização e
consumo de análises do aplicativo Mapa de Karnaugh Estendido. As regras são
independentes do fornecedor de autenticação e precisam ser aplicadas no
servidor, nunca somente na interface Flutter.

## 2. Papéis

| Papel | Quantidade | Responsabilidades |
| --- | --- | --- |
| `master` | exatamente um | proprietário, transferência, submasters e controle total |
| `submaster` | zero ou mais | administração de usuários, turmas, convites e cotas |
| `usuario` | zero ou mais | realização de análises conforme seu acesso |

Master e submaster possuem acesso ilimitado às análises.

### 2.1 Master

O master pode:

- convidar, aprovar, suspender e revogar usuários;
- definir ou adicionar cotas individualmente e em lote;
- criar, encerrar e selecionar turmas;
- promover e remover submasters;
- consultar o histórico administrativo;
- transferir a propriedade para outro email verificado.

O master não pode remover ou rebaixar a própria conta. Primeiro precisa
concluir a transferência de propriedade.

### 2.2 Submaster

O submaster pode administrar usuários comuns, inclusive convites, aprovação,
suspensão, revogação e cotas. Ele não pode:

- alterar o master;
- alterar a própria função;
- criar, promover, rebaixar ou remover submasters;
- transferir a propriedade.

### 2.3 Usuário

O usuário pode consultar seu próprio estado e saldo e solicitar uma análise
quando sua conta estiver ativa e sua cota permitir.

## 3. Ciclo de vida das contas

| Estado | Significado | Pode analisar? |
| --- | --- | --- |
| `convidado` | email previamente autorizado, cadastro não concluído | não |
| `aguardando_aprovacao` | email verificado, aguardando administrador | não |
| `ativo` | acesso liberado | conforme a cota |
| `suspenso` | bloqueio reversível | não |
| `revogado` | removido da disciplina | não |

Revogar é preferível a apagar. O usuário perde imediatamente o acesso, mas o
histórico administrativo permanece íntegro.

## 4. Convites e cadastros espontâneos

### 4.1 Usuário convidado

1. Master ou submaster informa o email e a turma.
2. O servidor registra um convite pendente.
3. O serviço de email envia um link de instalação e ativação.
4. A pessoa comprova a posse do mesmo email.
5. O convite é marcado como aceito e a conta se torna ativa.

Digitar um email convidado não basta: o endereço precisa ser verificado pelo
provedor de autenticação.

### 4.2 Cadastro sem convite

1. A pessoa cria a conta e verifica o email.
2. A conta recebe o estado `aguardando_aprovacao`.
3. Master ou submaster aprova ou recusa a solicitação.
4. Somente a aprovação muda o estado para `ativo`.

## 5. Turmas

Toda operação em lote deve selecionar explicitamente uma turma, por exemplo
`2026.1 — Circuitos Fluido Mecânicos`. Usuários de períodos anteriores não
podem ser afetados por engano.

Encerrar uma turma não apaga seus registros. A operação pode suspender ou
revogar todos os usuários comuns daquela turma, conforme confirmação do
administrador. Ela também encerra as matrículas ativas e cancela os convites
pendentes da turma. Para evitar enganos, o código da turma precisa ser
digitado novamente na confirmação.

## 6. Tipos de acesso e cotas

| Tipo | Saldo | Regra |
| --- | --- | --- |
| `ilimitado` | inexistente | análises livres |
| `limitado` | inteiro maior ou igual a zero | uma unidade por análise concluída |

Existem duas operações numéricas diferentes:

- **definir N:** substitui o saldo atual por N e converte o usuário para
  acesso limitado;
- **adicionar N:** soma N ao saldo limitado atual; usuários ilimitados
  continuam ilimitados.

As operações em lote atingem apenas usuários comuns da turma selecionada.
Master e submasters nunca são convertidos para acesso limitado.

## 7. Consumo de uma análise

Erros de digitação e validações locais não consomem cota. Para uma resolução
completa:

1. o Flutter valida a sequência localmente;
2. envia uma chave de idempotência e a solicitação autenticada;
3. o servidor verifica conta, turma, papel e saldo;
4. uma unidade é reservada atomicamente;
5. o motor Python executa a resolução;
6. em caso de sucesso, a reserva vira consumo;
7. em falha interna, a reserva é liberada;
8. a resposta só é entregue depois da confirmação do consumo.

A chave de idempotência impede que repetição de uma mesma requisição por falha
de rede desconte duas análises.

## 8. Transferência de propriedade

A transferência exige:

- master atual ativo e reautenticado;
- email do sucessor verificado;
- confirmação explícita do sucessor;
- transação única que mantenha exatamente um master;
- registro imutável na auditoria.

Ao final, o antigo master torna-se submaster automaticamente. O novo master
pode remover ou rebaixar essa conta depois, mas a troca nunca deixa o sistema
sem um administrador. Um fluxo de recuperação administrativa separado será
necessário para a perda definitiva do email do master.

## 9. Auditoria mínima

Devem ser registrados:

- ator, data e tipo de operação;
- usuário ou turma afetada;
- valor anterior e valor posterior de papel, estado ou cota;
- criação, aceitação, expiração e cancelamento de convites;
- reservas, consumos e estornos de análises;
- início e conclusão de transferências de propriedade.

Senhas, tokens e conteúdo das sequências não devem aparecer na auditoria.
Master e submasters podem consultar no painel as operações mais recentes, com
ator, data, ação e um resumo seguro da alteração.

## 10. Fronteiras de segurança

- O aplicativo nunca recebe chaves administrativas do provedor.
- Esconder uma tela não substitui autorização no servidor.
- Toda operação administrativa é revalidada no backend.
- O banco deve impedir mais de um master ativo.
- O consumo de cota precisa ocorrer em transação atômica.
- Revogação encerra sessões ou impede seu uso na próxima requisição.
- Emails administrativos são enviados pelo backend, nunca diretamente pelo
  aplicativo.

## 11. Modelo de dados planejado

| Entidade | Finalidade |
| --- | --- |
| `usuarios` | email, papel, estado e vínculo de autenticação |
| `turmas` | período, nome e estado da turma |
| `matriculas` | relação entre usuários e turmas |
| `convites` | preautorização de emails e expiração |
| `cotas` | tipo de acesso e saldo atual |
| `movimentos_cota` | definir, adicionar, reservar, consumir e estornar |
| `transferencias_master` | confirmação segura de sucessão |
| `auditoria` | histórico administrativo imutável |

As migrações incrementais desse modelo estão em
[`../supabase/migrations/202607220001_controle_acesso.sql`](../supabase/migrations/202607220001_controle_acesso.sql).
A migração `202607230004_auditoria_encerramento_turmas.sql` expõe o histórico
administrativo somente ao backend, implementa o encerramento preservando os
registros e obriga operações de cota em lote a selecionar uma turma ativa.

## 12. Decisão de arquitetura

O parser Dart permanece no Flutter para validação rápida e mensagens de erro.
A resolução completa fica na API Python para que a autorização e o consumo da
cota sejam confiáveis. Por isso, a realização de análises exigirá conexão com a
internet, embora partes da interface possam continuar disponíveis offline.

O fornecedor de autenticação, banco, hospedagem da API e SMTP será escolhido
em uma etapa posterior. As regras deste documento não dependem dessa escolha.
