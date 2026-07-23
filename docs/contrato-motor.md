# Contrato do motor de resolução

## 1. Objetivo

Este documento define a fronteira entre o motor de Karnaugh e seus clientes.
Os clientes são a interface Streamlit e a API HTTP. O aplicativo Flutter
consumirá a API após a autorização da análise.

O contrato v1 deve preservar o comportamento público de
`src.solver.resolver_site` e não expor classes internas de `src.engine`.

## 2. Operações do motor

### Analisar entrada

Interpreta e valida a sequência sem executar a busca de memórias e equações.

Função atual:

```python
analisar_entrada(sequencia: str) -> dict
```

Uso futuro na API:

```http
POST /api/v1/analises
```

### Resolver sequência

Executa todo o método e devolve uma representação serializável do resultado.

Função atual:

```python
resolver_site(
    sequencia: str,
    estados_iniciais: dict[str, int | bool | str] | None = None,
    *,
    ciclo_continuo: bool = False,
) -> dict
```

Uso futuro na API:

```http
POST /api/v1/resolucoes
```

### Gerar mapa

Converte o resultado da resolução em SVG.

Função atual:

```python
gerar_mapa_svg(resultado: dict) -> MapaSVG
```

O endpoint de resolução poderá devolver o SVG diretamente ou disponibilizá-lo
em um endpoint próprio. Essa decisão será tomada na implementação da API.

## 3. Solicitação de resolução

Corpo JSON:

```json
{
  "sequencia": "A+, B+, B-, A-",
  "estados_iniciais": {
    "A": 0,
    "B": 0
  },
  "ciclo_continuo": false,
  "incluir_mapa": true
}
```

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `sequencia` | string | sim | Entre 1 e 20.000 caracteres após remover espaços externos |
| `estados_iniciais` | objeto ou `null` | não | Chaves são atuadores; valores são índice, booleano ou nome do sensor |
| `ciclo_continuo` | booleano | não | Padrão `false`; exige estado final igual ao inicial |
| `incluir_mapa` | booleano | não | Padrão `true`; controla a geração do SVG pela API |

O schema correspondente está em
[`schemas/solicitacao-resolucao.schema.json`](schemas/solicitacao-resolucao.schema.json).

## 4. Resposta de resolução

Resposta bem-sucedida: `200 OK`.

Campos estáveis da versão v1:

| Campo | Tipo | Significado |
| --- | --- | --- |
| `atuadores` | `string[]` | Atuadores encontrados, na ordem canônica |
| `variaveis_fisicas` | `string[]` | Variáveis usadas pelo motor |
| `sensores_por_atuador` | objeto | Sensores válidos de cada atuador |
| `estado_inicial` | objeto | Índice inicial de cada atuador |
| `sensores_iniciais` | objeto | Sensor inicialmente ativo por atuador |
| `etapas` | `object[]` | Evolução física e lógica da sequência |
| `memorias` | `string[]` | Memórias encontradas pelo método |
| `quantidade_memorias` | inteiro | Número de memórias encontradas |
| `equacoes` | objeto | Equações prontas para apresentação |
| `equacoes_comandos` | objeto | Equações por comando lógico |
| `equacoes_fisicas` | objeto | Equações agregadas por saída física |
| `equacoes_memorias` | objeto | Equações de retenção das memórias |
| `resolucao` | `object[]` | Qualificação didática de cada comando |
| `eventos_mapa` | `object[]` | Eventos necessários para desenhar o mapa |
| `validacoes` | `string[]` | Invariantes verificadas pelo motor |
| `observacoes` | `string[]` | Informações adicionais da resolução |
| `versao_motor` | string | Versão interna que produziu o resultado |
| `mapa_svg` | string ou `null` | SVG quando solicitado e gerado pela API |

Campos de detecção de recursos, como `possui_loop`, `entradas_externas` e
`atuadores_multiposicao`, também permanecem públicos na v1.

O schema estrutural está em
[`schemas/resposta-resolucao.schema.json`](schemas/resposta-resolucao.schema.json).

## 5. Erros

Todos os erros da API usarão o mesmo formato:

```json
{
  "erro": {
    "codigo": "SEQUENCIA_INVALIDA",
    "mensagem": "Movimento inválido: 'B'.",
    "campo": "sequencia",
    "detalhes": {}
  }
}
```

| HTTP | Código | Situação |
| --- | --- | --- |
| `400` | `JSON_INVALIDO` | Corpo ausente ou JSON malformado |
| `422` | `SEQUENCIA_INVALIDA` | Sintaxe ou movimento inválido |
| `422` | `ESTADO_INICIAL_INVALIDO` | Estado incompatível com os atuadores |
| `422` | `CICLO_NAO_FECHA` | Ciclo contínuo sem retorno ao estado inicial |
| `422` | `RESOLUCAO_IMPOSSIVEL` | Motor não encontrou solução no limite de busca |
| `413` | `ENTRADA_MUITO_GRANDE` | Limite de caracteres excedido |
| `429` | `LIMITE_REQUISICOES` | Muitas solicitações em pouco tempo |
| `500` | `ERRO_INTERNO` | Falha não prevista; detalhes internos não são expostos |

O schema correspondente está em
[`schemas/erro.schema.json`](schemas/erro.schema.json).

## 6. Compatibilidade

- A URL contém a versão principal: `/api/v1`.
- Campos existentes não mudam de significado dentro da v1.
- Novos campos opcionais podem ser acrescentados sem criar a v2.
- Remoções, renomeações ou mudanças de tipo exigem `/api/v2`.
- O cliente deve ignorar campos adicionais que não reconheça.
- A versão do motor não substitui a versão do contrato HTTP.

## 7. Limites e segurança na fronteira

- Toda entrada será validada novamente no servidor.
- O aplicativo móvel nunca será considerado fonte confiável.
- Erros internos e rastros de execução não serão devolvidos ao cliente.
- A API terá limite por usuário e endereço de origem.
- O tempo máximo de resolução será limitado.
- SVG será produzido exclusivamente pelo servidor e tratado como conteúdo não
  executável no cliente.
- Autenticação, autorização e cotas seguem as regras de
  [`controle-acesso.md`](controle-acesso.md).

## 8. Fora do escopo desta etapa

Este contrato não define o provedor de autenticação nem o banco de dados. Ele
estabiliza a fronteira do motor para que essas partes sejam criadas sem
acoplamento às classes internas da resolução.
