import 'dart:async';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import 'administracao/servico_administracao_api.dart';
import 'analise/servico_api.dart';
import 'app.dart';
import 'autenticacao/servico_supabase.dart';
import 'configuracao/configuracao_aplicativo.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  const configuracao = ConfiguracaoAplicativo.doAmbiente();
  final erroConfiguracao = configuracao.validar();
  if (erroConfiguracao != null) {
    runApp(MapaKarnaughApp(erroInicial: erroConfiguracao));
    return;
  }

  unawaited(_aquecerApi(configuracao.apiBaseUrl));

  try {
    await Supabase.initialize(
      url: configuracao.supabaseUrl,
      publishableKey: configuracao.supabasePublishableKey,
    );
    final autenticacao = ServicoAutenticacaoSupabase(Supabase.instance.client);
    final analise = ServicoAnaliseApi(
      apiBaseUrl: configuracao.apiBaseUrl,
      autenticacao: autenticacao,
    );
    final administracao = ServicoAdministracaoApi(
      apiBaseUrl: configuracao.apiBaseUrl,
      autenticacao: autenticacao,
    );
    runApp(
      MapaKarnaughApp(
        servicoAutenticacao: autenticacao,
        servicoAnalise: analise,
        servicoAdministracao: administracao,
      ),
    );
  } catch (_) {
    runApp(
      const MapaKarnaughApp(
        erroInicial: 'Não foi possível iniciar o serviço de login.',
      ),
    );
  }
}

Future<void> _aquecerApi(String apiBaseUrl) async {
  final base = apiBaseUrl.replaceFirst(RegExp(r'/+$'), '');
  try {
    await http
        .get(Uri.parse('$base/health'))
        .timeout(const Duration(seconds: 75));
  } catch (_) {
    // O aquecimento é preventivo. As telas tratam uma indisponibilidade real.
  }
}
