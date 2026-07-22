import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mapa_karnaugh_app/analise/modelos_analise.dart';
import 'package:mapa_karnaugh_app/analise/servico_api.dart';
import 'package:mapa_karnaugh_app/autenticacao/modelos_autenticacao.dart';
import 'package:mapa_karnaugh_app/autenticacao/servico_autenticacao.dart';

class AutenticacaoFake implements ServicoAutenticacao {
  @override
  UsuarioSessao? get usuarioAtual =>
      const UsuarioSessao(id: 'usuario-1', email: 'teste@example.com');

  @override
  Stream<UsuarioSessao?> get mudancasSessao => const Stream.empty();

  @override
  Future<String> obterTokenAcesso() async => 'token-valido';

  @override
  Future<PerfilUsuario> carregarPerfil(String usuarioId) =>
      throw UnimplementedError();

  @override
  Future<ResultadoCadastro> cadastrar({
    required String email,
    required String senha,
  }) => throw UnimplementedError();

  @override
  Future<void> entrar({required String email, required String senha}) =>
      throw UnimplementedError();

  @override
  Future<void> sair() => throw UnimplementedError();
}

void main() {
  test('envia token, opções e chave de idempotência para a API', () async {
    late http.Request requisicaoRecebida;
    final cliente = MockClient((requisicao) async {
      requisicaoRecebida = requisicao;
      return http.Response(
        jsonEncode({
          'atuadores': ['A', 'B'],
          'etapas': [
            {'numero': 1},
            {'numero': 2},
          ],
          'memorias': ['X'],
          'equacoes': {'A+': 'S.x0'},
          'equacoes_memorias': {'X': '(b1 + x).¬(a0)'},
          'validacoes': ['Sequência validada.'],
          'observacoes': <String>[],
          'mapa_svg': '<svg></svg>',
          'mapa_largura': 1200,
          'mapa_altura': 700,
          'controle_acesso': {
            'estado': 'consumida',
            'acesso': 'limitado',
            'analises_restantes': 2,
            'requisicao_repetida': false,
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final servico = ServicoAnaliseApi(
      apiBaseUrl: 'http://127.0.0.1:8000/',
      autenticacao: AutenticacaoFake(),
      cliente: cliente,
    );

    final resultado = await servico.resolver(
      sequencia: ' A+, B+ ',
      chaveIdempotencia: 'chave-001',
      cicloContinuo: false,
      incluirMapa: true,
    );

    expect(
      requisicaoRecebida.url.toString(),
      'http://127.0.0.1:8000/api/v1/resolucoes',
    );
    expect(requisicaoRecebida.headers['Authorization'], 'Bearer token-valido');
    final corpo = jsonDecode(requisicaoRecebida.body) as Map<String, dynamic>;
    expect(corpo['sequencia'], 'A+, B+');
    expect(corpo['chave_idempotencia'], 'chave-001');
    expect(corpo['incluir_mapa'], isTrue);
    expect(resultado.etapas, hasLength(2));
    expect(resultado.controleAcesso.analisesRestantes, 2);
  });

  test('preserva a mensagem segura devolvida pela API', () async {
    final cliente = MockClient(
      (_) async => http.Response(
        jsonEncode({
          'erro': {
            'codigo': 'COTA_ESGOTADA',
            'mensagem': 'Você não possui análises disponíveis.',
          },
        }),
        403,
      ),
    );
    final servico = ServicoAnaliseApi(
      apiBaseUrl: 'http://127.0.0.1:8000',
      autenticacao: AutenticacaoFake(),
      cliente: cliente,
    );

    await expectLater(
      servico.resolver(
        sequencia: 'A+',
        chaveIdempotencia: 'chave-002',
        cicloContinuo: false,
        incluirMapa: false,
      ),
      throwsA(
        isA<FalhaAnalise>()
            .having((erro) => erro.codigo, 'codigo', 'COTA_ESGOTADA')
            .having(
              (erro) => erro.mensagem,
              'mensagem',
              'Você não possui análises disponíveis.',
            ),
      ),
    );
  });
}
