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
  String? emailEntrada;
  String? senhaEntrada;

  @override
  UsuarioSessao? get usuarioAtual =>
      const UsuarioSessao(id: 'master-1', email: 'professor@ufpe.br');

  @override
  MotivoDefinicaoSenha? get definicaoSenhaPendente => null;

  @override
  Stream<UsuarioSessao?> get mudancasSessao => const Stream.empty();

  @override
  Stream<MotivoDefinicaoSenha> get solicitacoesDefinicaoSenha =>
      const Stream.empty();

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
  Future<void> entrar({required String email, required String senha}) async {
    emailEntrada = email;
    senhaEntrada = senha;
  }

  @override
  Future<void> solicitarRedefinicaoSenha(String email) {
    throw UnimplementedError();
  }

  @override
  Future<void> definirNovaSenha(String senha) {
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
  test('reautentica o master diretamente no provedor de login', () async {
    final autenticacao = _AutenticacaoFake();
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000',
      autenticacao: autenticacao,
      cliente: MockClient((_) async => http.Response('{}', 200)),
    );

    await servico.reautenticar('senha-atual');

    expect(autenticacao.emailEntrada, 'professor@ufpe.br');
    expect(autenticacao.senhaEntrada, 'senha-atual');
  });

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

  test('limita ajuste em lote à turma selecionada', () async {
    late http.Request recebida;
    final cliente = MockClient((requisicao) async {
      recebida = requisicao;
      return http.Response(
        '{"usuarios_alterados":2,"usuarios_ignorados":0}',
        200,
      );
    });
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000',
      autenticacao: _AutenticacaoFake(),
      cliente: cliente,
    );

    await servico.ajustarCotasEmLote(
      adicionar: true,
      quantidade: 1,
      turmaId: 'turma-1',
    );

    expect(recebida.url.path, '/api/v1/admin/usuarios/cotas-em-lote');
    expect(jsonDecode(recebida.body), {
      'operacao': 'adicionar',
      'quantidade': 1,
      'turma_id': 'turma-1',
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

  test('inicia transferência master com e-mail confirmado', () async {
    late http.Request recebida;
    final cliente = MockClient((requisicao) async {
      recebida = requisicao;
      return http.Response(
        jsonEncode({
          'id': 'transferencia-1',
          'master_atual_id': 'master-1',
          'master_atual_email': 'professor@ufpe.br',
          'email_destino': 'novo.professor@ufpe.br',
          'estado': 'pendente',
          'sou_origem': true,
          'sou_destino': false,
          'envio_email': 'enviado',
        }),
        200,
      );
    });
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000',
      autenticacao: _AutenticacaoFake(),
      cliente: cliente,
    );

    final transferencia = await servico.iniciarTransferenciaMaster(
      emailDestino: 'novo.professor@ufpe.br',
    );

    expect(transferencia.emailEnviado, isTrue);
    expect(recebida.url.path, '/api/v1/admin/transferencia-master');
    expect(jsonDecode(recebida.body), {
      'email_destino': 'novo.professor@ufpe.br',
      'dias_validade': 7,
    });
  });

  test('encerra turma com remoção de acessos', () async {
    late http.Request recebida;
    final cliente = MockClient((requisicao) async {
      recebida = requisicao;
      return http.Response(
        '{"usuarios_alterados":2,'
        '"matriculas_encerradas":2,"convites_cancelados":1}',
        200,
      );
    });
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000',
      autenticacao: _AutenticacaoFake(),
      cliente: cliente,
    );

    final resultado = await servico.encerrarTurma(
      turmaId: 'turma-1',
      estadoUsuarios: EstadoConta.suspenso,
    );

    expect(resultado.usuariosAlterados, 2);
    expect(resultado.convitesCancelados, 1);
    expect(recebida.method, 'PATCH');
    expect(
      recebida.url.path,
      '/api/v1/admin/turmas/turma-1/encerrar',
    );
    expect(jsonDecode(recebida.body), {'estado_usuarios': 'revogado'});
  });

  test('lista histórico administrativo', () async {
    late http.Request recebida;
    final cliente = MockClient((requisicao) async {
      recebida = requisicao;
      return http.Response(
        jsonEncode([
          {
            'id': 10,
            'ator_email': 'professor@ufpe.br',
            'acao': 'criar_turma',
            'entidade': 'turma',
            'valor_posterior': {'codigo': '2026.1'},
            'criada_em': '2026-07-23T12:00:00Z',
          },
        ]),
        200,
      );
    });
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000',
      autenticacao: _AutenticacaoFake(),
      cliente: cliente,
    );

    final registros = await servico.listarAuditoria(limite: 30);

    expect(registros.single.acao, 'criar_turma');
    expect(registros.single.atorEmail, 'professor@ufpe.br');
    expect(recebida.url.path, '/api/v1/admin/auditoria');
    expect(recebida.url.queryParameters['limite'], '30');
  });

  test('aceita transferência master autenticada', () async {
    late http.Request recebida;
    final cliente = MockClient((requisicao) async {
      recebida = requisicao;
      return http.Response('{"estado":"aceita"}', 200);
    });
    final servico = ServicoAdministracaoApi(
      apiBaseUrl: 'http://localhost:8000',
      autenticacao: _AutenticacaoFake(),
      cliente: cliente,
    );

    await servico.aceitarTransferenciaMaster('transferencia-1');

    expect(recebida.method, 'POST');
    expect(
      recebida.url.path,
      '/api/v1/transferencia-master/transferencia-1/aceitar',
    );
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
