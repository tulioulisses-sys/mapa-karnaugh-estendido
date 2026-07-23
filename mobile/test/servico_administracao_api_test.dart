import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mapa_karnaugh_app/administracao/servico_administracao.dart';
import 'package:mapa_karnaugh_app/administracao/servico_administracao_api.dart';
import 'package:mapa_karnaugh_app/autenticacao/modelos_autenticacao.dart';
import 'package:mapa_karnaugh_app/autenticacao/servico_autenticacao.dart';

class _AutenticacaoFake implements ServicoAutenticacao {
  @override
  UsuarioSessao? get usuarioAtual => null;

  @override
  Stream<UsuarioSessao?> get mudancasSessao => const Stream.empty();

  @override
  Future<PerfilUsuario> carregarPerfil(String usuarioId) {
    throw UnimplementedError();
  }

  @override
  Future<ResultadoCadastro> cadastrar({
    required String email,
    required String senha,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<void> entrar({required String email, required String senha}) {
    throw UnimplementedError();
  }

  @override
  Future<String> obterTokenAcesso() async => 'token-admin';

  @override
  Future<void> sair() {
    throw UnimplementedError();
  }
}

void main() {
  test('lista usuários com o token da sessão', () async {
    late http.Request recebida;
    final cliente = MockClient((requisicao) async {
      recebida = requisicao;
      return http.Response(
        jsonEncode([
          {
            'id': 'aluno-1',
            'email': 'aluno@ufpe.br',
            'papel': 'usuario',
            'estado': 'aguardando_aprovacao',
            'acesso': 'limitado',
            'analises_restantes': 0,
          },
        ]),
        200,
      );
    });
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000/',
      autenticacao: _AutenticacaoFake(),
      cliente: cliente,
    );

    final usuarios = await servico.listarUsuarios();

    expect(usuarios.single.email, 'aluno@ufpe.br');
    expect(usuarios.single.aguardando, isTrue);
    expect(recebida.method, 'GET');
    expect(recebida.url.path, '/api/v1/admin/usuarios');
    expect(recebida.headers['Authorization'], 'Bearer token-admin');
  });

  test('envia ajuste de acesso limitado', () async {
    late http.Request recebida;
    final cliente = MockClient((requisicao) async {
      recebida = requisicao;
      return http.Response('{}', 200);
    });
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000',
      autenticacao: _AutenticacaoFake(),
      cliente: cliente,
    );

    await servico.definirAcesso(
      'aluno-1',
      TipoAcesso.limitado,
      3,
    );

    expect(recebida.method, 'PATCH');
    expect(
      recebida.url.path,
      '/api/v1/admin/usuarios/aluno-1/acesso',
    );
    expect(jsonDecode(recebida.body), {
      'acesso': 'limitado',
      'analises_restantes': 3,
    });
  });

  test('envia convites em lote com turma e cota inicial', () async {
    late http.Request recebida;
    final cliente = MockClient((requisicao) async {
      recebida = requisicao;
      return http.Response(
        jsonEncode({
          'total': 2,
          'emails_enviados': 2,
          'emails_com_falha': 0,
          'convites': <Object>[],
        }),
        200,
      );
    });
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000',
      autenticacao: _AutenticacaoFake(),
      cliente: cliente,
    );

    final resultado = await servico.convidarEmLote(
      emails: ['aluno1@ufpe.br', 'aluno2@ufpe.br'],
      papelDestino: PapelUsuario.usuario,
      acessoDestino: TipoAcesso.limitado,
      analisesIniciais: 3,
      turmaId: 'turma-1',
    );

    expect(resultado.emailsEnviados, 2);
    expect(recebida.url.path, '/api/v1/admin/convites/lote');
    expect(jsonDecode(recebida.body), {
      'emails': ['aluno1@ufpe.br', 'aluno2@ufpe.br'],
      'papel_destino': 'usuario',
      'acesso_destino': 'limitado',
      'analises_iniciais': 3,
      'turma_id': 'turma-1',
      'dias_validade': 7,
    });
  });

  test('preserva mensagem segura da API administrativa', () async {
    final cliente = MockClient(
      (_) async => http.Response(
        jsonEncode({
          'erro': {
            'codigo': 'PERMISSAO_ADMINISTRATIVA_NEGADA',
            'mensagem': 'Sua conta não pode realizar essa operação.',
          },
        }),
        403,
      ),
    );
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000',
      autenticacao: _AutenticacaoFake(),
      cliente: cliente,
    );

    await expectLater(
      servico.listarUsuarios(),
      throwsA(
        isA<FalhaAdministracao>()
            .having(
              (erro) => erro.codigo,
              'codigo',
              'PERMISSAO_ADMINISTRATIVA_NEGADA',
            )
            .having(
              (erro) => erro.mensagem,
              'mensagem',
              'Sua conta não pode realizar essa operação.',
            ),
      ),
    );
  });
}
