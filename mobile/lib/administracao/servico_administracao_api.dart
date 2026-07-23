import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../autenticacao/modelos_autenticacao.dart';
import '../autenticacao/servico_autenticacao.dart';
import 'modelos_administracao.dart';
import 'servico_administracao.dart';

class ServicoAdministracaoApi implements ServicoAdministracao {
  ServicoAdministracaoApi({
    required String apiBaseUrl,
    required this.autenticacao,
    http.Client? cliente,
  }) : _apiBaseUrl = apiBaseUrl.replaceFirst(RegExp(r'/+$'), ''),
       _cliente = cliente ?? http.Client();

  final String _apiBaseUrl;
  final ServicoAutenticacao autenticacao;
  final http.Client _cliente;

  @override
  Future<List<UsuarioAdministrado>> listarUsuarios() async {
    final dados = await _requisitar('GET', '/api/v1/admin/usuarios');
    if (dados is! List) throw _respostaInvalida();

    try {
      return dados
          .map(
            (item) => UsuarioAdministrado.deJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList(growable: false);
    } on Object {
      throw _respostaInvalida();
    }
  }

  @override
  Future<void> alterarEstado(String usuarioId, EstadoConta estado) async {
    await _requisitar(
      'PATCH',
      '/api/v1/admin/usuarios/$usuarioId/estado',
      {'estado': _estadoTexto(estado)},
    );
  }

  @override
  Future<void> definirAcesso(
    String usuarioId,
    TipoAcesso acesso,
    int? analisesRestantes,
  ) async {
    await _requisitar(
      'PATCH',
      '/api/v1/admin/usuarios/$usuarioId/acesso',
      {
        'acesso': acesso == TipoAcesso.ilimitado
            ? 'ilimitado'
            : 'limitado',
        'analises_restantes': analisesRestantes,
      },
    );
  }

  @override
  Future<ResultadoCotasLote> ajustarCotasEmLote({
    required bool adicionar,
    required int quantidade,
    required String turmaId,
    List<String>? usuarioIds,
  }) async {
    final corpo = <String, dynamic>{
      'operacao': adicionar ? 'adicionar' : 'definir',
      'quantidade': quantidade,
      'turma_id': turmaId,
    };
    if (usuarioIds != null) corpo['usuario_ids'] = usuarioIds;

    final dados = await _requisitar(
      'POST',
      '/api/v1/admin/usuarios/cotas-em-lote',
      corpo,
    );
    if (dados is! Map) throw _respostaInvalida();
    return ResultadoCotasLote.deJson(Map<String, dynamic>.from(dados));
  }

  @override
  Future<void> alterarPapel(String usuarioId, PapelUsuario papel) async {
    await _requisitar(
      'PATCH',
      '/api/v1/admin/usuarios/$usuarioId/papel',
      {'papel': papel == PapelUsuario.submaster ? 'submaster' : 'usuario'},
    );
  }

  @override
  Future<void> reautenticar(String senha) async {
    final email = autenticacao.usuarioAtual?.email;
    if (email == null || email.isEmpty) {
      throw const FalhaAdministracao(
        'Sua sessão não possui um e-mail válido.',
        codigo: 'SESSAO_INVALIDA',
      );
    }
    try {
      await autenticacao.entrar(email: email, senha: senha);
    } on FalhaAutenticacao catch (erro) {
      throw FalhaAdministracao(
        erro.mensagem,
        codigo: 'REAUTENTICACAO_FALHOU',
      );
    }
  }

  @override
  Future<TransferenciaMaster?> obterTransferenciaMaster() async {
    final dados = await _requisitar('GET', '/api/v1/transferencia-master');
    if (dados == null) return null;
    if (dados is! Map) throw _respostaInvalida();
    return TransferenciaMaster.deJson(Map<String, dynamic>.from(dados));
  }

  @override
  Future<TransferenciaMaster> iniciarTransferenciaMaster({
    required String emailDestino,
    int diasValidade = 7,
  }) async {
    final dados = await _requisitar(
      'POST',
      '/api/v1/admin/transferencia-master',
      {
        'email_destino': emailDestino,
        'dias_validade': diasValidade,
      },
    );
    if (dados is! Map) throw _respostaInvalida();
    return TransferenciaMaster.deJson(
      Map<String, dynamic>.from(dados),
    );
  }

  @override
  Future<void> cancelarTransferenciaMaster(String transferenciaId) async {
    await _requisitar(
      'PATCH',
      '/api/v1/admin/transferencia-master/$transferenciaId/cancelar',
    );
  }

  @override
  Future<void> aceitarTransferenciaMaster(String transferenciaId) async {
    await _requisitar(
      'POST',
      '/api/v1/transferencia-master/$transferenciaId/aceitar',
    );
  }

  @override
  Future<List<TurmaAdministrada>> listarTurmas() async {
    final dados = await _requisitar('GET', '/api/v1/admin/turmas');
    if (dados is! List) throw _respostaInvalida();

    try {
      return dados
          .map(
            (item) => TurmaAdministrada.deJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList(growable: false);
    } on Object {
      throw _respostaInvalida();
    }
  }

  @override
  Future<TurmaAdministrada> criarTurma({
    required String codigo,
    required String nome,
  }) async {
    final dados = await _requisitar('POST', '/api/v1/admin/turmas', {
      'codigo': codigo,
      'nome': nome,
    });
    if (dados is! Map) throw _respostaInvalida();
    return TurmaAdministrada.deJson(Map<String, dynamic>.from(dados));
  }

  @override
  Future<ResultadoEncerramentoTurma> encerrarTurma({
    required String turmaId,
    required EstadoConta estadoUsuarios,
  }) async {
    final dados = await _requisitar(
      'PATCH',
      '/api/v1/admin/turmas/$turmaId/encerrar',
      {
        'estado_usuarios': estadoUsuarios == EstadoConta.revogado
            ? 'revogado'
            : 'suspenso',
      },
    );
    if (dados is! Map) throw _respostaInvalida();
    return ResultadoEncerramentoTurma.deJson(
      Map<String, dynamic>.from(dados),
    );
  }

  @override
  Future<List<RegistroAuditoria>> listarAuditoria({int limite = 80}) async {
    final dados = await _requisitar(
      'GET',
      '/api/v1/admin/auditoria?limite=$limite',
    );
    if (dados is! List) throw _respostaInvalida();

    try {
      return dados
          .map(
            (item) => RegistroAuditoria.deJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList(growable: false);
    } on Object {
      throw _respostaInvalida();
    }
  }

  @override
  Future<List<ConviteAdministrado>> listarConvites() async {
    final dados = await _requisitar('GET', '/api/v1/admin/convites');
    if (dados is! List) throw _respostaInvalida();

    try {
      return dados
          .map(
            (item) => ConviteAdministrado.deJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList(growable: false);
    } on Object {
      throw _respostaInvalida();
    }
  }

  @override
  Future<ResultadoConvitesLote> convidarEmLote({
    required List<String> emails,
    required PapelUsuario papelDestino,
    required TipoAcesso acessoDestino,
    required int? analisesIniciais,
    String? turmaId,
    int diasValidade = 7,
  }) async {
    final dados = await _requisitar(
      'POST',
      '/api/v1/admin/convites/lote',
      {
        'emails': emails,
        'papel_destino': papelDestino == PapelUsuario.submaster
            ? 'submaster'
            : 'usuario',
        'acesso_destino': acessoDestino == TipoAcesso.ilimitado
            ? 'ilimitado'
            : 'limitado',
        'analises_iniciais': analisesIniciais,
        'turma_id': turmaId,
        'dias_validade': diasValidade,
      },
    );
    if (dados is! Map) throw _respostaInvalida();
    return ResultadoConvitesLote.deJson(Map<String, dynamic>.from(dados));
  }

  @override
  Future<void> cancelarConvite(String conviteId) async {
    await _requisitar(
      'PATCH',
      '/api/v1/admin/convites/$conviteId/cancelar',
    );
  }

  Future<Object?> _requisitar(
    String metodo,
    String caminho, [
    Map<String, dynamic>? corpo,
  ]) async {
    try {
      final token = await autenticacao.obterTokenAcesso();
      final requisicao = http.Request(
        metodo,
        Uri.parse('$_apiBaseUrl$caminho'),
      )
        ..headers.addAll({
          'Authorization': 'Bearer $token',
          'Accept': 'application/json',
          if (corpo != null) 'Content-Type': 'application/json',
        });
      if (corpo != null) requisicao.body = jsonEncode(corpo);

      final fluxo = await _cliente
          .send(requisicao)
          .timeout(const Duration(seconds: 20));
      final resposta = await http.Response.fromStream(fluxo);
      final dados = resposta.body.isEmpty ? <String, dynamic>{} : jsonDecode(
        resposta.body,
      );

      if (resposta.statusCode < 200 || resposta.statusCode >= 300) {
        throw _falhaDaApi(dados, resposta.statusCode);
      }
      return dados;
    } on FalhaAdministracao {
      rethrow;
    } on FalhaAutenticacao catch (erro) {
      throw FalhaAdministracao(erro.mensagem, codigo: 'SESSAO_INVALIDA');
    } on TimeoutException {
      throw const FalhaAdministracao(
        'A administração demorou mais que o esperado. Tente novamente.',
        codigo: 'TEMPO_ESGOTADO',
      );
    } on http.ClientException {
      throw const FalhaAdministracao(
        'Não foi possível conectar à API administrativa.',
        codigo: 'API_INDISPONIVEL',
      );
    } on FormatException {
      throw _respostaInvalida();
    }
  }
}

String _estadoTexto(EstadoConta estado) => switch (estado) {
  EstadoConta.ativo => 'ativo',
  EstadoConta.suspenso => 'suspenso',
  EstadoConta.revogado => 'revogado',
  EstadoConta.convidado => 'convidado',
  EstadoConta.aguardandoAprovacao => 'aguardando_aprovacao',
};

FalhaAdministracao _falhaDaApi(Object? corpo, int statusCode) {
  if (corpo is Map && corpo['erro'] is Map) {
    final erro = corpo['erro'] as Map;
    return FalhaAdministracao(
      erro['mensagem']?.toString() ?? 'Não foi possível concluir a operação.',
      codigo: erro['codigo']?.toString(),
    );
  }
  return FalhaAdministracao(
    'Não foi possível concluir a operação (HTTP $statusCode).',
    codigo: 'ERRO_HTTP_$statusCode',
  );
}

FalhaAdministracao _respostaInvalida() {
  return const FalhaAdministracao(
    'A API administrativa retornou uma resposta inválida.',
    codigo: 'RESPOSTA_INVALIDA',
  );
}
