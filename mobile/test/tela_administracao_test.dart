import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mapa_karnaugh_app/administracao/modelos_administracao.dart';
import 'package:mapa_karnaugh_app/administracao/servico_administracao.dart';
import 'package:mapa_karnaugh_app/administracao/tela_administracao.dart';
import 'package:mapa_karnaugh_app/autenticacao/modelos_autenticacao.dart';
import 'package:mapa_karnaugh_app/visual/identidade_visual.dart';

class _AdministracaoFake implements ServicoAdministracao {
  var usuarios = <UsuarioAdministrado>[
    const UsuarioAdministrado(
      id: 'master-1',
      email: 'professor@ufpe.br',
      papel: PapelUsuario.master,
      estado: EstadoConta.ativo,
      acesso: TipoAcesso.ilimitado,
      analisesRestantes: null,
    ),
    const UsuarioAdministrado(
      id: 'aluno-1',
      email: 'aluno@ufpe.br',
      papel: PapelUsuario.usuario,
      estado: EstadoConta.aguardandoAprovacao,
      acesso: TipoAcesso.limitado,
      analisesRestantes: 0,
    ),
  ];
  final operacoes = <String>[];
  TransferenciaMaster? transferencia;

  @override
  Future<List<UsuarioAdministrado>> listarUsuarios() async => usuarios;

  @override
  Future<void> alterarEstado(String usuarioId, EstadoConta estado) async {
    operacoes.add('estado:$usuarioId:${estado.name}');
    usuarios = usuarios
        .map(
          (usuario) => usuario.id != usuarioId
              ? usuario
              : UsuarioAdministrado(
                  id: usuario.id,
                  email: usuario.email,
                  papel: usuario.papel,
                  estado: estado,
                  acesso: usuario.acesso,
                  analisesRestantes: usuario.analisesRestantes,
                ),
        )
        .toList();
  }

  @override
  Future<void> alterarPapel(String usuarioId, PapelUsuario papel) async {
    operacoes.add('papel:$usuarioId:${papel.name}');
  }

  @override
  Future<void> reautenticar(String senha) async {
    operacoes.add('reautenticar:$senha');
  }

  @override
  Future<TransferenciaMaster?> obterTransferenciaMaster() async =>
      transferencia;

  @override
  Future<TransferenciaMaster> iniciarTransferenciaMaster({
    required String emailDestino,
    int diasValidade = 7,
  }) async {
    operacoes.add('transferir:$emailDestino:$diasValidade');
    transferencia = TransferenciaMaster(
      id: 'transferencia-1',
      masterAtualId: 'master-1',
      masterAtualEmail: 'professor@ufpe.br',
      emailDestino: emailDestino,
      usuarioDestinoId: null,
      estado: 'pendente',
      expiraEm: DateTime.utc(2026, 7, 30),
      souOrigem: true,
      souDestino: false,
      envioEmail: 'enviado',
    );
    return transferencia!;
  }

  @override
  Future<void> cancelarTransferenciaMaster(String transferenciaId) async {
    operacoes.add('cancelar-transferencia:$transferenciaId');
    transferencia = null;
  }

  @override
  Future<void> aceitarTransferenciaMaster(String transferenciaId) async {
    operacoes.add('aceitar-transferencia:$transferenciaId');
  }

  @override
  Future<ResultadoCotasLote> ajustarCotasEmLote({
    required bool adicionar,
    required int quantidade,
    required String turmaId,
    List<String>? usuarioIds,
  }) async {
    operacoes.add('lote:$adicionar:$quantidade:$turmaId');
    return const ResultadoCotasLote(
      usuariosAlterados: 1,
      usuariosIgnorados: 0,
    );
  }

  @override
  Future<void> definirAcesso(
    String usuarioId,
    TipoAcesso acesso,
    int? analisesRestantes,
  ) async {
    operacoes.add('acesso:$usuarioId:${acesso.name}:$analisesRestantes');
  }

  @override
  Future<List<TurmaAdministrada>> listarTurmas() async => const [
    TurmaAdministrada(
      id: 'turma-1',
      codigo: '2026.1',
      nome: 'Circuitos Fluido Mecânicos',
      ativa: true,
      quantidadeAlunos: 0,
    ),
  ];

  @override
  Future<TurmaAdministrada> criarTurma({
    required String codigo,
    required String nome,
  }) async {
    operacoes.add('turma:$codigo:$nome');
    return TurmaAdministrada(
      id: 'turma-2',
      codigo: codigo,
      nome: nome,
      ativa: true,
      quantidadeAlunos: 0,
    );
  }

  @override
  Future<ResultadoEncerramentoTurma> encerrarTurma({
    required String turmaId,
    required EstadoConta estadoUsuarios,
  }) async {
    operacoes.add('encerrar:$turmaId:${estadoUsuarios.name}');
    return const ResultadoEncerramentoTurma(
      usuariosAlterados: 1,
      matriculasEncerradas: 1,
      convitesCancelados: 0,
    );
  }

  @override
  Future<List<RegistroAuditoria>> listarAuditoria({int limite = 80}) async =>
      [
        RegistroAuditoria(
          id: 1,
          atorId: 'master-1',
          atorEmail: 'professor@ufpe.br',
          acao: 'criar_turma',
          entidade: 'turma',
          entidadeId: 'turma-1',
          valorAnterior: null,
          valorPosterior: const {'codigo': '2026.1'},
          criadaEm: DateTime.utc(2026, 7, 23, 12),
        ),
      ];

  @override
  Future<List<ConviteAdministrado>> listarConvites() async => const [];

  @override
  Future<ResultadoConvitesLote> convidarEmLote({
    required List<String> emails,
    required PapelUsuario papelDestino,
    required TipoAcesso acessoDestino,
    required int? analisesIniciais,
    String? turmaId,
    int diasValidade = 7,
  }) async {
    operacoes.add('convites:${emails.length}:$analisesIniciais:$turmaId');
    return ResultadoConvitesLote(
      total: emails.length,
      emailsEnviados: emails.length,
      emailsComFalha: 0,
    );
  }

  @override
  Future<void> cancelarConvite(String conviteId) async {
    operacoes.add('cancelar-convite:$conviteId');
  }
}

const _perfilMaster = PerfilUsuario(
  id: 'master-1',
  email: 'professor@ufpe.br',
  papel: PapelUsuario.master,
  estado: EstadoConta.ativo,
  acesso: TipoAcesso.ilimitado,
  analisesRestantes: null,
);

void main() {
  testWidgets('painel mostra contas e ações permitidas ao master', (
    tester,
  ) async {
    final servico = _AdministracaoFake();
    await tester.pumpWidget(
      MaterialApp(
        theme: criarTemaInstitucional(),
        home: TelaAdministracao(
          servico: servico,
          perfilAtual: _perfilMaster,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Usuários e permissões'), findsOneWidget);
    expect(find.text('professor@ufpe.br'), findsOneWidget);
    expect(find.text('aluno@ufpe.br'), findsOneWidget);
    expect(find.text('Aguardando aprovação'), findsOneWidget);
    expect(find.text('Aprovar'), findsOneWidget);
    expect(find.text('Tornar submaster'), findsOneWidget);
    expect(find.text('Convidar por e-mail'), findsOneWidget);
    expect(find.text('Criar turma'), findsOneWidget);
    expect(find.text('Transferir controle master'), findsOneWidget);
    expect(find.text('Histórico administrativo'), findsOneWidget);
    expect(find.text('Turma criada'), findsOneWidget);
  });

  testWidgets('master aprova cadastro pendente', (tester) async {
    final servico = _AdministracaoFake();
    await tester.pumpWidget(
      MaterialApp(
        theme: criarTemaInstitucional(),
        home: TelaAdministracao(
          servico: servico,
          perfilAtual: _perfilMaster,
        ),
      ),
    );
    await tester.pumpAndSettle();

    final aprovar = find.widgetWithText(FilledButton, 'Aprovar');
    await tester.ensureVisible(aprovar);
    await tester.tap(aprovar);
    await tester.pumpAndSettle();

    expect(servico.operacoes, contains('estado:aluno-1:ativo'));
    expect(find.text('Usuário aprovado.'), findsOneWidget);
    expect(find.text('Suspender'), findsOneWidget);
  });

  testWidgets('encerramento de turma exige o código e remove acessos', (
    tester,
  ) async {
    final servico = _AdministracaoFake();
    await tester.pumpWidget(
      MaterialApp(
        theme: criarTemaInstitucional(),
        home: TelaAdministracao(
          servico: servico,
          perfilAtual: _perfilMaster,
        ),
      ),
    );
    await tester.pumpAndSettle();

    final encerrar = find.widgetWithText(TextButton, 'Encerrar');
    await tester.ensureVisible(encerrar);
    await tester.tap(encerrar);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Remover acessos'));
    await tester.enterText(
      find.byType(TextField),
      '2026.1',
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Encerrar turma'));
    await tester.pumpAndSettle();

    expect(
      servico.operacoes,
      contains('encerrar:turma-1:revogado'),
    );
  });
}
