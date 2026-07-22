# Estratégia do cliente Flutter e validação local

O plano inicial previa executar toda a resolução no Flutter sem conexão. Essa
decisão foi revista após a definição de cotas por usuário: um motor completo
distribuído no cliente permitiria contornar o consumo de análises.

O parser Dart continua responsável pela validação rápida e pelas mensagens de
erro. A resolução completa permanece no motor Python e será autorizada pela API
antes do consumo de cada cota. As regras estão em
[`controle-acesso.md`](controle-acesso.md).

## Estratégia de equivalência

O arquivo `mobile/test/fixtures/motor_referencias.json` contém resultados
canônicos produzidos pelo motor Python para quatro classes de entrada:

- sequência linear simples;
- movimentos simultâneos;
- atuador multiposição;
- loop condicional.

Os testes Dart comparam a análise local com esses resultados. Uma alteração
futura no motor Python só pode atualizar as referências de forma intencional e
acompanhada pelos testes.

## Atualizar as referências

Na raiz do repositório, execute:

```bash
python tools/gerar_referencias_mobile.py
python -m pytest
```

O teste `tests/test_referencias_mobile.py` falha quando o JSON salvo não
corresponde mais ao resultado atual do motor Python.

## Ordem planejada

1. modelos do domínio — concluído;
2. parser de sequências — concluído;
3. autenticação e autorização na API;
4. consumo atômico de cotas;
5. integração do Flutter com o motor Python;
6. interface de resolução e resultados;
7. painel administrativo;
8. distribuição para Android e Web/PWA.
