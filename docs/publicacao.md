# Publicação do aplicativo

Arquitetura prevista para a publicação sem custo fixo:

- Supabase: autenticação, banco de dados e regras de acesso;
- Brevo: entrega dos e-mails enviados pelo Supabase;
- Render Web Service: API FastAPI;
- Render Static Site: aplicativo Flutter Web/PWA;
- GitHub Releases: distribuição do APK Android.

Os planos gratuitos possuem limites e podem mudar. Antes de cada semestre,
confira a situação dos serviços e faça um teste completo com uma conta de aluno.

## API no Render

O `Dockerfile` da raiz contém somente o necessário para executar a API. Segredos
não são copiados para a imagem.

Configuração do Web Service:

- nome: `mapa-karnaugh-api-cfm`;
- branch: `app-flutter-offline`;
- runtime: `Docker`;
- plano: `Free`;
- diretório raiz: vazio;
- caminho de saúde: `/health`;
- implantação automática: ativada.

Variáveis de ambiente:

- `SUPABASE_URL`;
- `SUPABASE_PUBLISHABLE_KEY`;
- `SUPABASE_SECRET_KEY`;
- `SUPABASE_TIMEOUT_SEGUNDOS`, com o valor `10`;
- `APP_PUBLIC_URL`;
- `CORS_ORIGINS`.

Nunca coloque `SUPABASE_SECRET_KEY` em arquivo versionado, no Flutter ou no
navegador.

Depois do deploy, a rota `/health` deve informar `"status": "ok"`.

## Aplicativo web no Render

O script `tools/build_flutter_web.sh` instala o canal estável do Flutter durante
o build e gera os arquivos estáticos em `mobile/build/web`.

Configuração do Static Site:

- nome: `mapa-karnaugh-app-cfm`;
- branch: `app-flutter-offline`;
- diretório raiz: vazio;
- comando de build: `bash tools/build_flutter_web.sh`;
- diretório de publicação: `mobile/build/web`;
- implantação automática: ativada.

Variáveis públicas do Static Site:

- `SUPABASE_URL`;
- `SUPABASE_PUBLISHABLE_KEY`;
- `API_BASE_URL`, com a URL HTTPS da API no Render.

O Static Site não recebe `SUPABASE_SECRET_KEY`.

Após a primeira publicação:

1. altere `APP_PUBLIC_URL` da API para a URL do Static Site;
2. altere `CORS_ORIGINS` da API para incluir a origem do Static Site;
3. cadastre a URL pública e o redirecionamento correspondente nas configurações
   de autenticação do Supabase;
4. faça um teste de cadastro, convite, recuperação de senha e análise.

## Inicialização do plano gratuito

O Web Service gratuito pode adormecer quando fica sem tráfego. O Flutter envia
uma chamada preventiva à rota `/health` ao iniciar e aceita uma espera maior nas
requisições de análise e administração. O primeiro acesso depois de um período
ocioso ainda pode demorar; os seguintes tendem a ser imediatos.

## APK Android assinado

O aplicativo usa o identificador permanente
`br.ufpe.cfm.mapa_karnaugh_app`. Para que as atualizações sejam reconhecidas
como pertencentes ao mesmo aplicativo, todos os APKs de produção precisam ser
assinados com a mesma chave.

Crie a chave uma única vez, fora do repositório:

```powershell
New-Item -ItemType Directory -Force C:\chaves-mapa-karnaugh | Out-Null
keytool -genkeypair -v `
  -keystore C:\chaves-mapa-karnaugh\mapa-karnaugh-upload.jks `
  -keyalg RSA -keysize 2048 -validity 10000 `
  -alias mapa-karnaugh
```

Se `keytool` não estiver no `Path`, use o executável instalado com o Android
Studio:

```powershell
& "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" `
  -genkeypair -v `
  -keystore C:\chaves-mapa-karnaugh\mapa-karnaugh-upload.jks `
  -keyalg RSA -keysize 2048 -validity 10000 `
  -alias mapa-karnaugh
```

Copie `mobile\android\key.properties.example` para
`mobile\android\key.properties` e preencha as duas senhas. O caminho do arquivo
de chave pode permanecer como está no exemplo. Esses dois arquivos são
ignorados pelo Git e nunca devem ser enviados ao repositório.

Guarde cópias seguras do `.jks`, das senhas e do alias. Sem a mesma chave, não é
possível publicar uma atualização por cima do aplicativo já instalado.

Com `mobile\config\dev.json` apontando para os serviços de produção, gere o APK:

```powershell
cd C:\projetos\mapa-karnaugh-estendido\mobile
flutter build apk --release --dart-define-from-file=config\dev.json
```

O arquivo para distribuição será:

```text
mobile\build\app\outputs\flutter-apk\app-release.apk
```

Antes de uma nova versão, aumente o número após `+` no campo `version` de
`mobile/pubspec.yaml`, por exemplo de `1.0.0+1` para `1.0.1+2`.
