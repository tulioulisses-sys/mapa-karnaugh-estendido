import 'package:flutter/material.dart';

import 'analise/servico_analise.dart';
import 'autenticacao/portao_autenticacao.dart';
import 'autenticacao/servico_autenticacao.dart';
import 'visual/identidade_visual.dart';

class MapaKarnaughApp extends StatelessWidget {
  const MapaKarnaughApp({
    super.key,
    this.servicoAutenticacao,
    this.servicoAnalise,
    this.erroInicial,
  }) : assert(
         (servicoAutenticacao != null && servicoAnalise != null) ||
             erroInicial != null,
         'Informe os serviços do aplicativo ou um erro inicial.',
       );

  final ServicoAutenticacao? servicoAutenticacao;
  final ServicoAnalise? servicoAnalise;
  final String? erroInicial;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mapa de Karnaugh Estendido',
      debugShowCheckedModeBanner: false,
      theme: criarTemaInstitucional(),
      builder: (context, child) => FundoInstitucional(child: child!),
      home: erroInicial == null
          ? PortaoAutenticacao(
              servicoAutenticacao: servicoAutenticacao!,
              servicoAnalise: servicoAnalise!,
            )
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
            child: CartaoInstitucional(
              destaque: true,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.settings_outlined,
                    size: 48,
                    color: CoresInstitucionais.vinho,
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
    );
  }
}
