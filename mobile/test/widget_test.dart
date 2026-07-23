import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mapa_karnaugh_app/analise/modelos_analise.dart';
import 'package:mapa_karnaugh_app/analise/servico_analise.dart';
import 'package:mapa_karnaugh_app/app.dart';
import 'package:mapa_karnaugh_app/autenticacao/modelos_autenticacao.dart';
import 'package:mapa_karnaugh_app/autenticacao/servico_autenticacao.dart';
import 'package:mapa_karnaugh_app/visual/identidade_visual.dart';

class ServicoAutenticacaoFake implements ServicoAutenticacao {
  final _mudancas = StreamController<UsuarioSessao?>.broadcast();
  final _solicitacoesSenha =
      StreamController<MotivoDefinicaoSenha>.broadcast();
  UsuarioSessao? usuario;
  MotivoDefinicaoSenha? senhaPendente;
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
  String? emailRecuperacao;
  String? novaSenha;

  @override
  UsuarioSessao? get usuarioAtual => usuario;

  @override
  MotivoDefinicaoSenha? get definicaoSenhaPendente => senhaPendente;

  @override
  Stream<UsuarioSessao?> get mudancasSessao => _mudancas.stream;

  @override
  Stream<MotivoDefinicaoSenha> get solicitacoesDefinicaoSenha =>
      _solicitacoesSenha.stream;

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
  Future<String> obterTokenAcesso() async => 'token-teste';

  @override
  Future<void> solicitarRedefinicaoSenha(String email) async {
    emailRecuperacao = email;
  }

  @override
  Future<void> definirNovaSenha(String senha) async {
    novaSenha = senha;
    senhaPendente = null;
  }

  @override
  Future<void> sair() async {
    usuario = null;
    _mudancas.add(null);
  }

  Future<void> fechar() async {
    await _mudancas.close();
    await _solicitacoesSenha.close();
  }
}

class ServicoAnaliseFake implements ServicoAnalise {
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

MapaKarnaughApp _aplicativo(ServicoAutenticacao autenticacao) {
  return MapaKarnaughApp(
    servicoAutenticacao: autenticacao,
    servicoAnalise: ServicoAnaliseFake(),
  );
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
    final aplicativo = tester.widget<MaterialApp>(find.byType(MaterialApp));
    expect(aplicativo.theme?.colorScheme.primary, CoresInstitucionais.vinho);
  });

  testWidgets('valida os campos antes de tentar login', (tester) async {
    final servico = ServicoAutenticacaoFake();
    await tester.pumpWidget(_aplicativo(servico));

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
    await tester.pumpWidget(_aplicativo(servico));

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
    expect(find.text('Nova análise'), findsOneWidget);
    await servico.fechar();
  });

  testWidgets('cadastro informa que o email precisa ser confirmado', (
    tester,
  ) async {
    final servico = ServicoAutenticacaoFake();
    await tester.pumpWidget(_aplicativo(servico));

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

  testWidgets('solicita recuperação sem revelar se a conta existe', (
    tester,
  ) async {
    final servico = ServicoAutenticacaoFake();
    await tester.pumpWidget(_aplicativo(servico));

    await tester.tap(find.text('Esqueci minha senha'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byType(TextFormField).last,
      'aluno@example.com',
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Enviar link'));
    await tester.pumpAndSettle();

    expect(servico.emailRecuperacao, 'aluno@example.com');
    expect(
      find.text(
        'Se o e-mail estiver cadastrado, você receberá um link para '
        'redefinir a senha.',
      ),
      findsOneWidget,
    );
    await servico.fechar();
  });

  testWidgets('convite exige a criação da primeira senha', (tester) async {
    final servico = ServicoAutenticacaoFake()
      ..usuario = const UsuarioSessao(
        id: 'usuario-1',
        email: 'convidado@example.com',
      )
      ..senhaPendente = MotivoDefinicaoSenha.convite;
    await tester.pumpWidget(_aplicativo(servico));

    expect(find.text('Crie sua senha'), findsOneWidget);
    await tester.enterText(find.byType(TextFormField).first, 'senha-segura');
    await tester.enterText(find.byType(TextFormField).last, 'senha-segura');
    await tester.tap(
      find.widgetWithText(FilledButton, 'Concluir meu acesso'),
    );
    await tester.pumpAndSettle();

    expect(servico.novaSenha, 'senha-segura');
    expect(find.text('Acesso liberado'), findsOneWidget);
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

    await tester.pumpWidget(_aplicativo(servico));
    await tester.pumpAndSettle();

    expect(
      find.text('Seu cadastro está aguardando aprovação do professor.'),
      findsOneWidget,
    );
    expect(find.text('Aluno'), findsOneWidget);
    await servico.fechar();
  });
}
