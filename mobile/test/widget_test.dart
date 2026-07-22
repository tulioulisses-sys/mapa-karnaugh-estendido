import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mapa_karnaugh_app/app.dart';
import 'package:mapa_karnaugh_app/autenticacao/modelos_autenticacao.dart';
import 'package:mapa_karnaugh_app/autenticacao/servico_autenticacao.dart';

class ServicoAutenticacaoFake implements ServicoAutenticacao {
  final _mudancas = StreamController<UsuarioSessao?>.broadcast();
  UsuarioSessao? usuario;
  PerfilUsuario perfil = const PerfilUsuario(
    id: 'usuario-1',
    email: 'teste@example.com',
    papel: PapelUsuario.master,
    estado: EstadoConta.ativo,
    acesso: TipoAcesso.ilimitado,
    analisesRestantes: null,
  );
  bool cadastroRequerConfirmacao = true;
  int tentativasEntrada = 0;

  @override
  UsuarioSessao? get usuarioAtual => usuario;

  @override
  Stream<UsuarioSessao?> get mudancasSessao => _mudancas.stream;

  @override
  Future<void> entrar({required String email, required String senha}) async {
    tentativasEntrada++;
    usuario = UsuarioSessao(id: 'usuario-1', email: email);
    _mudancas.add(usuario);
  }

  @override
  Future<ResultadoCadastro> cadastrar({
    required String email,
    required String senha,
  }) async {
    return ResultadoCadastro(requerConfirmacaoEmail: cadastroRequerConfirmacao);
  }

  @override
  Future<PerfilUsuario> carregarPerfil(String usuarioId) async => perfil;

  @override
  Future<void> sair() async {
    usuario = null;
    _mudancas.add(null);
  }

  Future<void> fechar() => _mudancas.close();
}

void main() {
  testWidgets('avisa quando as configurações públicas estão ausentes', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MapaKarnaughApp(erroInicial: 'Configuração ausente.'),
    );

    expect(find.text('Configuração necessária'), findsOneWidget);
    expect(find.text('Configuração ausente.'), findsOneWidget);
  });

  testWidgets('valida os campos antes de tentar login', (tester) async {
    final servico = ServicoAutenticacaoFake();
    await tester.pumpWidget(MapaKarnaughApp(servicoAutenticacao: servico));

    await tester.tap(find.widgetWithText(FilledButton, 'Entrar'));
    await tester.pump();

    expect(find.text('Informe um e-mail válido.'), findsOneWidget);
    expect(
      find.text('A senha precisa ter pelo menos 6 caracteres.'),
      findsOneWidget,
    );
    expect(servico.tentativasEntrada, 0);
    await servico.fechar();
  });

  testWidgets('login abre o resumo da conta master', (tester) async {
    final servico = ServicoAutenticacaoFake();
    await tester.pumpWidget(MapaKarnaughApp(servicoAutenticacao: servico));

    await tester.enterText(
      find.byType(TextFormField).first,
      'teste@example.com',
    );
    await tester.enterText(find.byType(TextFormField).last, 'senha-segura');
    await tester.tap(find.widgetWithText(FilledButton, 'Entrar'));
    await tester.pumpAndSettle();

    expect(find.text('Acesso liberado'), findsOneWidget);
    expect(find.text('Master'), findsOneWidget);
    expect(find.text('Análises ilimitadas'), findsOneWidget);
    await servico.fechar();
  });

  testWidgets('cadastro informa que o email precisa ser confirmado', (
    tester,
  ) async {
    final servico = ServicoAutenticacaoFake();
    await tester.pumpWidget(MapaKarnaughApp(servicoAutenticacao: servico));

    await tester.tap(find.text('Criar uma conta'));
    await tester.pump();
    await tester.enterText(
      find.byType(TextFormField).first,
      'novo@example.com',
    );
    await tester.enterText(find.byType(TextFormField).last, 'senha-segura');
    await tester.tap(find.widgetWithText(FilledButton, 'Criar conta'));
    await tester.pumpAndSettle();

    expect(
      find.text('Cadastro criado. Confira seu e-mail para confirmar a conta.'),
      findsOneWidget,
    );
    await servico.fechar();
  });

  testWidgets('mostra cadastro aguardando aprovação', (tester) async {
    final servico = ServicoAutenticacaoFake()
      ..usuario = const UsuarioSessao(
        id: 'usuario-1',
        email: 'teste@example.com',
      )
      ..perfil = const PerfilUsuario(
        id: 'usuario-1',
        email: 'teste@example.com',
        papel: PapelUsuario.usuario,
        estado: EstadoConta.aguardandoAprovacao,
        acesso: TipoAcesso.limitado,
        analisesRestantes: 0,
      );

    await tester.pumpWidget(MapaKarnaughApp(servicoAutenticacao: servico));
    await tester.pumpAndSettle();

    expect(
      find.text('Seu cadastro está aguardando aprovação do professor.'),
      findsOneWidget,
    );
    expect(find.text('Aluno'), findsOneWidget);
    await servico.fechar();
  });
}
