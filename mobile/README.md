# Aplicativo Flutter

Cliente Android, iOS e Web do Mapa de Karnaugh Estendido.

## Configuração local

Crie `config/dev.json` a partir de `config/dev.example.json` e preencha somente
a URL e a chave **publicável** do Supabase. Esse arquivo é ignorado pelo Git.
Nunca coloque a chave secreta da API Python dentro da pasta `mobile`.

```powershell
Copy-Item config/dev.example.json config/dev.json
```

## Executar no navegador

Mantenha a API Python em outra janela e use uma porta fixa para o CORS:

```powershell
flutter pub get
flutter run -d chrome --web-port 3000 --dart-define-from-file=config/dev.json
```

## Validar

```powershell
flutter test
flutter analyze
```
