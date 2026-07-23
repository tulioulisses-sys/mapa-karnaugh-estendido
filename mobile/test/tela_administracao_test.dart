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
  Future<ResultadoCotasLote> ajustarCotasEmLote({
    required bool adicionar,
    required int quantidade,
    List<String>? usuarioIds,
  }) async {
    operacoes.add('lote:$adicionar:$quantidade');
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
}
