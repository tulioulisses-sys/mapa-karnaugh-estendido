import 'package:flutter/material.dart';

import 'autenticacao/portao_autenticacao.dart';
import 'autenticacao/servico_autenticacao.dart';

class MapaKarnaughApp extends StatelessWidget {
  const MapaKarnaughApp({super.key, this.servicoAutenticacao, this.erroInicial})
    : assert(
        servicoAutenticacao != null || erroInicial != null,
        'Informe o serviço de autenticação ou um erro inicial.',
      );

  final ServicoAutenticacao? servicoAutenticacao;
  final String? erroInicial;

  @override
  Widget build(BuildContext context) {
    final esquema = ColorScheme.fromSeed(
      seedColor: const Color(0xFF135D66),
      brightness: Brightness.light,
    );

    return MaterialApp(
      title: 'Mapa de Karnaugh Estendido',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: esquema,
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF4F7F7),
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
          filled: true,
          fillColor: Colors.white,
        ),
      ),
      home: erroInicial == null
          ? PortaoAutenticacao(servico: servicoAutenticacao!)
          : TelaConfiguracaoAusente(mensagem: erroInicial!),
    );
  }
}

class TelaConfiguracaoAusente extends StatelessWidget {
  const TelaConfiguracaoAusente({super.key, required this.mensagem});

  final String mensagem;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.settings_outlined,
                      size: 48,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Configuração necessária',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 12),
                    Text(mensagem, textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    const Text(
                      'Inicie o aplicativo com SUPABASE_URL e '
                      'SUPABASE_PUBLISHABLE_KEY. Nunca informe a chave '
                      'secreta do servidor ao Flutter.',
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
