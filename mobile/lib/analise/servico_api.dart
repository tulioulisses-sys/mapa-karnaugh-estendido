import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../autenticacao/modelos_autenticacao.dart';
import '../autenticacao/servico_autenticacao.dart';
import 'modelos_analise.dart';
import 'servico_analise.dart';

class ServicoAnaliseApi implements ServicoAnalise {
  ServicoAnaliseApi({
    required String apiBaseUrl,
    required this.autenticacao,
    http.Client? cliente,
  }) : _apiBaseUrl = apiBaseUrl.replaceFirst(RegExp(r'/+$'), ''),
       _cliente = cliente ?? http.Client();

  final String _apiBaseUrl;
  final ServicoAutenticacao autenticacao;
  final http.Client _cliente;

  @override
  Future<ResultadoAnalise> resolver({
    required String sequencia,
    required String chaveIdempotencia,
    required bool cicloContinuo,
    required bool incluirMapa,
  }) async {
    try {
      final token = await autenticacao.obterTokenAcesso();
      final resposta = await _cliente
          .post(
            Uri.parse('$_apiBaseUrl/api/v1/resolucoes'),
            headers: {
              'Authorization': 'Bearer $token',
              'Content-Type': 'application/json',
            },
            body: jsonEncode({
              'sequencia': sequencia.trim(),
              'ciclo_continuo': cicloContinuo,
              'incluir_mapa': incluirMapa,
            }),
          )
          .timeout(const Duration(seconds: 120));

      final corpo = _decodificarCorpo(resposta.body);
      if (resposta.statusCode < 200 || resposta.statusCode >= 300) {
        throw _falhaDaApi(corpo, resposta.statusCode);
      }
      return ResultadoAnalise.deJson(corpo);
    } on FalhaAnalise {
      rethrow;
    } on FalhaAutenticacao catch (erro) {
      throw FalhaAnalise(erro.mensagem, codigo: 'SESSAO_INVALIDA');
    } on TimeoutException {
      throw const FalhaAnalise(
        'A anÃ¡lise demorou mais que o esperado. Tente novamente.',
        codigo: 'TEMPO_ESGOTADO',
      );
    } on http.ClientException {
      throw const FalhaAnalise(
        'NÃ£o foi possÃ­vel acessar o servidor da anÃ¡lise. Tente novamente.',
        codigo: 'API_INDISPONIVEL',
      );
    } on FormatException {
      throw const FalhaAnalise(
        'A API retornou uma resposta invÃ¡lida.',
        codigo: 'RESPOSTA_INVALIDA',
      );
    } catch (_) {
      throw const FalhaAnalise(
        'NÃ£o foi possÃ­vel processar a resposta da anÃ¡lise.',
        codigo: 'FALHA_PROCESSAMENTO_RESPOSTA',
      );
    }
  }
}

Map<String, dynamic> _decodificarCorpo(String corpo) {
  final valor = jsonDecode(corpo);
  if (valor is! Map) throw const FormatException();
  return valor.map((chave, conteudo) => MapEntry(chave.toString(), conteudo));
}

FalhaAnalise _falhaDaApi(Map<String, dynamic> corpo, int statusCode) {
  final erro = corpo['erro'];
  if (erro is Map) {
    return FalhaAnalise(
      erro['mensagem']?.toString() ?? 'NÃ£o foi possÃ­vel realizar a anÃ¡lise.',
      codigo: erro['codigo']?.toString(),
    );
  }
  return FalhaAnalise(
    'NÃ£o foi possÃ­vel realizar a anÃ¡lise (HTTP $statusCode).',
    codigo: 'ERRO_HTTP_$statusCode',
  );
}
