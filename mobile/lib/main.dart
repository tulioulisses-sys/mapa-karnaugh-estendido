import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

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
    runApp(
      MapaKarnaughApp(
        servicoAutenticacao: ServicoAutenticacaoSupabase(
          Supabase.instance.client,
        ),
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
