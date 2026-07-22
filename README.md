# Mapa de Karnaugh Estendido

Ferramenta para resolver sistemas sequenciais pneumáticos, eletropneumáticos e
fluídicos pelo Método do Mapa de Karnaugh Estendido.

O projeto interpreta a sequência de movimentos, determina estados físicos,
calcula as memórias necessárias, qualifica os comandos, verifica condições de
segurança e gera o mapa em SVG.

## Recursos atuais

- sequências lineares e movimentos simultâneos;
- atuadores tradicionais e multiposição;
- loops condicionais e entradas externas;
- cálculo automático de memórias;
- equações booleanas de comando, SET, RESET e retenção;
- identificação e qualificação de pontos perigosos;
- mapa de Karnaugh Estendido em SVG;
- interface web responsiva em Streamlit;
- API HTTP v1 para análise e resolução;
- estrutura Flutter para Android, iOS e Web;
- parser Dart validado contra referências do motor Python;
- testes automatizados com GitHub Actions.

## Executar localmente

Requer Python 3.12 ou superior.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Executar os testes

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Executar a API

```bash
python -m pip install -r requirements-api.txt
cp .env.example .env
python -m uvicorn api.main:app --reload --env-file .env
```

A documentação interativa ficará disponível em
`http://127.0.0.1:8000/docs`. Para permitir um frontend em outro domínio,
configure `CORS_ORIGINS` com uma lista separada por vírgulas.

Preencha o arquivo `.env` local com a URL, a chave publicável e uma chave
secreta do projeto Supabase. O arquivo real é ignorado pelo Git. A chave
`SUPABASE_SECRET_KEY` é exclusiva do servidor e nunca deve ser copiada para o
Flutter, para o navegador, para commits ou para mensagens.

`POST /api/v1/analises` permanece público porque faz apenas validação de
entrada e não consome cota. `POST /api/v1/resolucoes` exige um token Bearer do
Supabase, uma `chave_idempotencia` e, para usuários comuns, o `turma_id`. A API
reserva a cota, executa o motor e confirma ou estorna a reserva.

## Entrada básica

```text
A+, B+, B-, A-
```

Outros formatos aceitos:

```text
A+, (B+, C+), C-, B-, A-
A+, B+ até b1, C+, B+ até b2, C-, B+ até b3, A-, B- até b0
A+, B+, [C+, D+, C-, D-] enquanto e=0, A-, B-
```

## Organização

```text
app.py                 Entrada da aplicação Streamlit
pages/                 Telas da interface
src/parser_entrada.py  Interpretação das sequências
src/modelos.py         Modelos do domínio
src/engine.py          Motor do método
src/solver.py          Fachada usada pela interface
src/mapa.py            Geração do mapa SVG
tests/                 Testes automatizados
docs/                  Contratos e documentação técnica
```

## Aplicativo móvel

O motor Python é exposto por uma API HTTP. O aplicativo Flutter fará a
validação inicial no dispositivo e solicitará a resolução completa ao servidor.
O contrato está em [`docs/contrato-motor.md`](docs/contrato-motor.md).

As regras planejadas de master, submaster, turmas, convites e cotas estão em
[`docs/controle-acesso.md`](docs/controle-acesso.md).

O esquema PostgreSQL/Supabase correspondente está em
[`supabase/migrations`](supabase/migrations).
