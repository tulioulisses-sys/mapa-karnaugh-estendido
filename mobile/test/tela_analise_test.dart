import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mapa_karnaugh_app/analise/modelos_analise.dart';
import 'package:mapa_karnaugh_app/analise/servico_analise.dart';
import 'package:mapa_karnaugh_app/analise/tela_analise.dart';

class AnaliseFake implements ServicoAnalise {
  AnaliseFake({this.falharPrimeira = false});

  final bool falharPrimeira;
  int chamadas = 0;
  final chavesRecebidas = <String>[];

  @override
  Future<ResultadoAnalise> resolver({
    required String sequencia,
    required String chaveIdempotencia,
    required bool cicloContinuo,
    required bool incluirMapa,
  }) async {
    chamadas++;
    chavesRecebidas.add(chaveIdempotencia);
    if (falharPrimeira && chamadas == 1) {
      throw const FalhaAnalise('Falha temporária.');
    }
    return const ResultadoAnalise(
      atuadores: ['A', 'B'],
      etapas: [
        {
          'numero': 1,
          'comando_texto': 'A+',
          'estado_antes_texto': 'a0 · b0',
          'estado_depois_texto': 'a1 · b0',
          'condicao_externa_texto': 'Nenhuma',
          'pertence_loop': false,
          'fase': 0,
          'codigo_memorias': {'X': 0},
        },
        {
          'numero': 2,
          'comando_texto': 'B+',
          'estado_antes_texto': 'a1 · b0',
          'estado_depois_texto': 'a1 · b1',
          'condicao_externa_texto': 'Nenhuma',
          'pertence_loop': false,
          'fase': 0,
          'codigo_memorias': {'X': 0},
        },
        {'numero': 3},
        {'numero': 4},
      ],
      memorias: ['X'],
      equacoes: {'A+': 'S.x0', 'B+': 'a1.x0'},
      equacoesComandos: {'A+': 'S.x0', 'B+': 'a1.x0'},
      equacoesFisicas: {'A+': 'S.x0', 'B+': 'a1.x0'},
      equacoesMemorias: {'X': '(b1 + x).¬(a0)'},
      sensoresPorAtuador: {
        'A': ['a0', 'a1'],
        'B': ['b0', 'b1'],
      },
      sensoresIniciais: {'A': 'a0', 'B': 'b0'},
      resolucao: [
        {
          'Passo': 1,
          'Comando': 'A+',
          'Condição mínima': 'S',
          'Condição externa': 'Nenhuma',
          'Restrição do ramo': 'Nenhuma',
          'Contracomando': 'A-',
          'Qualificador de diferenciação': 'x0',
          'Contato de parada': 'Nenhum',
          'Equação qualificada': 'A+ = S.x0',
          'Pontos perigosos': 'Nenhum',
          'Qualificador complementar': 'Nenhum',
          'Equação final': 'A+ = S.x0',
        },
      ],
      versaoMotor: 'teste',
      validacoes: ['Sequência validada.'],
      observacoes: [],
      mapaSvg: null,
      mapaLargura: null,
      mapaAltura: null,
      controleAcesso: ControleAcessoAnalise(
        acesso: 'ilimitado',
        estado: 'consumida',
        analisesRestantes: null,
        requisicaoRepetida: false,
      ),
    );
  }
}

void main() {
  testWidgets('valida a sequência antes de chamar a API', (tester) async {
    final servico = AnaliseFake();
    await tester.pumpWidget(MaterialApp(home: TelaAnalise(servico: servico)));

    await _tocarBotaoAnalise(tester);
    await tester.pump();

    expect(
      find.text('Informe a sequência que deseja analisar.'),
      findsOneWidget,
    );
    expect(servico.chamadas, 0);
  });

  testWidgets('exibe equações e resumo após concluir análise', (tester) async {
    final servico = AnaliseFake();
    await tester.pumpWidget(MaterialApp(home: TelaAnalise(servico: servico)));

    await _tocarUsarExemplo(tester);
    await _tocarBotaoAnalise(tester);
    await tester.pumpAndSettle();

    expect(find.text('Resultado da resolução'), findsOneWidget);
    expect(find.text('4 etapas'), findsOneWidget);
    expect(find.text('Análises ilimitadas'), findsOneWidget);
    expect(find.text('Validações'), findsNothing);
    expect(servico.chamadas, 1);

    await _tocarAba(tester, 'Equações');
    expect(find.text('Ocorrência lógica'), findsWidgets);
    expect(find.text('A+'), findsOneWidget);
    expect(find.text('S.x0'), findsOneWidget);

    await _tocarAba(tester, 'Resolução do método');
    expect(find.text('Condição mínima'), findsOneWidget);
    expect(find.text('Pontos perigosos'), findsOneWidget);
    expect(find.text('Equação final'), findsOneWidget);
  });

  testWidgets('repetição após falha reutiliza a chave de idempotência', (
    tester,
  ) async {
    final servico = AnaliseFake(falharPrimeira: true);
    await tester.pumpWidget(MaterialApp(home: TelaAnalise(servico: servico)));

    await _tocarUsarExemplo(tester);
    await _tocarBotaoAnalise(tester);
    await tester.pumpAndSettle();
    expect(find.text('Falha temporária.'), findsOneWidget);

    await _tocarBotaoAnalise(tester);
    await tester.pumpAndSettle();

    expect(servico.chamadas, 2);
    expect(servico.chavesRecebidas[1], servico.chavesRecebidas[0]);
    expect(find.text('Resultado da resolução'), findsOneWidget);
  });
}

Future<void> _tocarAba(WidgetTester tester, String nome) async {
  final aba = find.text(nome);
  await tester.ensureVisible(aba);
  await tester.pumpAndSettle();
  await tester.tap(aba);
  await tester.pumpAndSettle();
}

Future<void> _tocarUsarExemplo(WidgetTester tester) async {
  final exemplo = find.widgetWithText(
    TextButton,
    'Usar exemplo A+, B+, B-, A-',
  );
  await tester.ensureVisible(exemplo);
  await tester.pumpAndSettle();
  await tester.tap(exemplo);
  await tester.pump();
}

Future<void> _tocarBotaoAnalise(WidgetTester tester) async {
  final botao = find.widgetWithText(FilledButton, 'Realizar análise');
  await tester.ensureVisible(botao);
  await tester.pumpAndSettle();
  await tester.tap(botao);
}
