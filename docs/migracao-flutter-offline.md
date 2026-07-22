# Migração do motor para Flutter offline

O aplicativo móvel deve executar a resolução do Mapa de Karnaugh Estendido
sem depender de uma API ou de conexão com a internet. O motor Python continua
sendo a implementação de referência enquanto o equivalente em Dart é
construído e validado.

## Estratégia de equivalência

O arquivo `mobile/test/fixtures/motor_referencias.json` contém resultados
canônicos produzidos pelo motor Python para quatro classes de entrada:

- sequência linear simples;
- movimentos simultâneos;
- atuador multiposição;
- loop condicional.

Durante a migração, os testes Dart devem comparar cada parte da análise e da
resolução com esses resultados. Uma alteração futura no motor Python só pode
atualizar as referências de forma intencional e acompanhada pelos testes.

## Atualizar as referências

Na raiz do repositório, execute:

```bash
python tools/gerar_referencias_mobile.py
python -m pytest
```

O teste `tests/test_referencias_mobile.py` falha quando o JSON salvo não
corresponde mais ao resultado atual do motor Python.

## Ordem planejada da migração

1. modelos do domínio;
2. parser de sequências;
3. construção das etapas e estados;
4. cálculo e alocação das memórias;
5. qualificação e simplificação das equações;
6. geração do mapa em SVG;
7. interface Flutter para Android, iOS e Web.
