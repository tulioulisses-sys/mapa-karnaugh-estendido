# Publicação do aplicativo

Arquitetura prevista para a publicação sem custo fixo:

- Supabase: autenticação, banco de dados e regras de acesso;
- Brevo: entrega dos e-mails enviados pelo Supabase;
- Koyeb: API FastAPI;
- GitHub Pages: aplicativo Flutter Web/PWA;
- GitHub Releases: distribuição do APK Android.

Os planos gratuitos possuem limites e podem mudar. Antes de cada semestre,
confira a situação dos serviços e faça um teste completo com uma conta de aluno.

## API no Koyeb

O `Dockerfile` da raiz contém somente o necessário para executar a API. Segredos
não são copiados para a imagem.

Ao criar o serviço:

1. conecte o repositório do GitHub;
2. selecione a branch de publicação;
3. escolha o construtor `Dockerfile`;
4. selecione exclusivamente a instância marcada como `Free`;
5. configure a porta HTTP com o valor `8000`;
6. configure a verificação de saúde com o caminho `/health`;
7. cadastre estas variáveis de ambiente:

   - `SUPABASE_URL`;
   - `SUPABASE_PUBLISHABLE_KEY`;
   - `SUPABASE_SECRET_KEY`;
   - `SUPABASE_TIMEOUT_SEGUNDOS` com o valor `10`;
   - `APP_PUBLIC_URL`, inicialmente com a URL local e depois com a URL pública;
   - `CORS_ORIGINS`, inicialmente com a origem local e depois com a origem
     pública do aplicativo.

Nunca coloque `SUPABASE_SECRET_KEY` em arquivo versionado, no Flutter ou no
navegador.

Depois do deploy, abra:

```text
https://endereco-fornecido-pelo-koyeb/health
```

A resposta deve informar `"status": "ok"`.

