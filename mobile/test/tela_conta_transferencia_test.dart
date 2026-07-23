import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mapa_karnaugh_app/administracao/modelos_administracao.dart';
import 'package:mapa_karnaugh_app/administracao/servico_administracao.dart';
import 'package:mapa_karnaugh_app/analise/modelos_analise.dart';
import 'package:mapa_karnaugh_app/analise/servico_analise.dart';
import 'package:mapa_karnaugh_app/autenticacao/modelos_autenticacao.dart';
import 'package:mapa_karnaugh_app/autenticacao/servico_autenticacao.dart';
import 'package:mapa_karnaugh_app/autenticacao/tela_conta.dart';
import 'package:mapa_karnaugh_app/visual/identidade_visual.dart';

class _AutenticacaoFake implements ServicoAutenticacao {
  @override
  UsuarioSessao? get usuarioAtual =>
      const UsuarioSessao(id: 'destino-1', email: 'destino@ufpe.br');

  @override
  MotivoDefinicaoSenha? get definicaoSenhaPendente => null;

  @override
  Stream<UsuarioSessao?> get mudancasSessao => const Stream.empty();

  @override
  Stream<MotivoDefinicaoSenha> get solicitacoesDefinicaoSenha =>
      const Stream.empty();

  @override
  Future<PerfilUsuario> carregarPerfil(String usuarioId) async {
    return const PerfilUsuario(
      id: 'destino-1',
      email: 'destino@ufpe.br',
      papel: PapelUsuario.usuario,
      estado: EstadoConta.aguardandoAprovacao,
      acesso: TipoAcesso.limitado,
      analisesRestantes: 0,
    );
  }

  @override
  Future<String> obterTokenAcesso() async => 'token';

  @override
  Future<ResultadoCadastro> cadastrar({
    required String email,
    required String senha,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<void> definirNovaSenha(String senha) {
    throw UnimplementedError();
  }

  @override
  Future<void> entrar({required String email, required String senha}) {
    throw UnimplementedError();
  }

  @override
  Future<void> sair() async {}

  @override
  Future<void> solicitarRedefinicaoSenha(String email) {
    throw UnimplementedError();
  }
}

class _AnaliseFake implements ServicoAnalise {
  @override
  Future<ResultadoAnalise> resolver({
    required String sequencia,
    required String chaveIdempotencia,
    required bool cicloContinuo,
    required bool incluirMapa,
  }) {
    throw UnimplementedError();
  }
}

class _AdministracaoFake implements ServicoAdministracao {
  TransferenciaMaster? transferencia = TransferenciaMaster(
    id: 'transferencia-1',
    masterAtualId: 'master-1',
    masterAtualEmail: 'professor@ufpe.br',
    emailDestino: 'destino@ufpe.br',
    usuarioDestinoId: 'destino-1',
    estado: 'pendente',
    expiraEm: DateTime.utc(2026, 7, 30),
    souOrigem: false,
    souDestino: true,
    envioEmail: null,
  );
  bool aceitou = false;

  @override
  Future<TransferenciaMaster?> obterTransferenciaMaster() async =>
      transferencia;

  @override
  Future<void> reautenticar(String senha) {
    throw UnimplementedError();
  }

  @override
  Future<void> aceitarTransferenciaMaster(String transferenciaId) async {
    aceitou = true;
    transferencia = null;
  }

  @override
  Future<void> alterarEstado(String usuarioId, EstadoConta estado) {
    throw UnimplementedError();
  }

  @override
  Future<void> alterarPapel(String usuarioId, PapelUsuario papel) {
    throw UnimplementedError();
  }

  @override
  Future<ResultadoCotasLote> ajustarCotasEmLote({
    required bool adicionar,
    required int quantidade,
    required String turmaId,
    List<String>? usuarioIds,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<void> cancelarConvite(String conviteId) {
    throw UnimplementedError();
  }

  @override
  Future<void> cancelarTransferenciaMaster(String transferenciaId) {
    throw UnimplementedError();
  }

  @override
  Future<TurmaAdministrada> criarTurma({
    required String codigo,
    required String nome,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<ResultadoEncerramentoTurma> encerrarTurma({
    required String turmaId,
    required EstadoConta estadoUsuarios,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<void> definirAcesso(
    String usuarioId,
    TipoAcesso acesso,
    int? analisesRestantes,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ResultadoConvitesLote> convidarEmLote({
    required List<String> emails,
    required PapelUsuario papelDestino,
    required TipoAcesso acessoDestino,
    required int? analisesIniciais,
    String? turmaId,
    int diasValidade = 7,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<TransferenciaMaster> iniciarTransferenciaMaster({
    required String emailDestino,
    int diasValidade = 7,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<List<ConviteAdministrado>> listarConvites() {
    throw UnimplementedError();
  }

  @override
  Future<List<RegistroAuditoria>> listarAuditoria({int limite = 80}) {
    throw UnimplementedError();
  }

  @override
  Future<List<TurmaAdministrada>> listarTurmas() {
    throw UnimplementedError();
  }

  @override
  Future<List<UsuarioAdministrado>> listarUsuarios() {
    throw UnimplementedError();
  }
}

void main() {
  testWidgets('destinatário autenticado aceita o controle master', (
    tester,
  ) async {
    final administracao = _AdministracaoFake();
    await tester.pumpWidget(
      MaterialApp(
        theme: criarTemaInstitucional(),
        home: TelaConta(
          servicoAutenticacao: _AutenticacaoFake(),
          servicoAnalise: _AnaliseFake(),
          servicoAdministracao: administracao,
          usuario: const UsuarioSessao(
            id: 'destino-1',
            email: 'destino@ufpe.br',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Convite para assumir o controle master'),
      findsOneWidget,
    );
    final aceitar = find.widgetWithText(
      FilledButton,
      'Aceitar controle master',
    );
    await tester.ensureVisible(aceitar);
    await tester.tap(aceitar);
    await tester.pumpAndSettle();
    await tester.tap(
      find.widgetWithText(FilledButton, 'Aceitar controle'),
    );
    await tester.pumpAndSettle();

    expect(administracao.aceitou, isTrue);
    expect(
      find.text('Transferência concluída. Agora você é o master.'),
      findsOneWidget,
    );
  });
}
