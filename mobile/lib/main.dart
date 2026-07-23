import 'package:flutter/material.dart';
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
