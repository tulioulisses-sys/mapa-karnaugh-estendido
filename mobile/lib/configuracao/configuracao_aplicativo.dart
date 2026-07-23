class ConfiguracaoAplicativo {
  const ConfiguracaoAplicativo({
    required this.supabaseUrl,
    required this.supabasePublishableKey,
    required this.apiBaseUrl,
  });

  const ConfiguracaoAplicativo.doAmbiente()
    : supabaseUrl = const String.fromEnvironment('SUPABASE_URL'),
      supabasePublishableKey = const String.fromEnvironment(
        'SUPABASE_PUBLISHABLE_KEY',
      ),
      apiBaseUrl = const String.fromEnvironment(
        'API_BASE_URL',
        defaultValue: 'http://127.0.0.1:8000',
      );

  final String supabaseUrl;
  final String supabasePublishableKey;
  final String apiBaseUrl;

  String? validar() {
    if (supabaseUrl.trim().isEmpty || supabasePublishableKey.trim().isEmpty) {
      return 'As configurações públicas do Supabase não foram informadas.';
    }
    if (!supabaseUrl.startsWith('https://')) {
      return 'A URL pública do Supabase é inválida.';
    }
    if (!supabasePublishableKey.startsWith('sb_publishable_')) {
      return 'A chave publicável do Supabase é inválida.';
    }
    return null;
  }
}
