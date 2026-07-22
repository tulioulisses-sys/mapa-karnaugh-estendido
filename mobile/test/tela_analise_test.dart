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
        {'numero': 1},
        {'numero': 2},
        {'numero': 3},
        {'numero': 4},
      ],
      memorias: ['X'],
      equacoes: {'A+': 'S.x0', 'B+': 'a1.x0'},
      equacoesMemorias: {'X': '(b1 + x).¬(a0)'},
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

    await tester.tap(find.text('Usar exemplo A+, B+, B-, A-'));
    await tester.pump();
    await _tocarBotaoAnalise(tester);
    await tester.pumpAndSettle();

    expect(find.text('Resultado da análise'), findsOneWidget);
    expect(find.text('4 etapas'), findsOneWidget);
    expect(find.text('A+ = S.x0'), findsOneWidget);
    expect(find.text('Análises ilimitadas'), findsOneWidget);
    expect(find.text('Validações'), findsNothing);
    expect(servico.chamadas, 1);
  });

  testWidgets('repetição após falha reutiliza a chave de idempotência', (
    tester,
  ) async {
    final servico = AnaliseFake(falharPrimeira: true);
    await tester.pumpWidget(MaterialApp(home: TelaAnalise(servico: servico)));

    await tester.tap(find.text('Usar exemplo A+, B+, B-, A-'));
    await _tocarBotaoAnalise(tester);
    await tester.pumpAndSettle();
    expect(find.text('Falha temporária.'), findsOneWidget);

    await _tocarBotaoAnalise(tester);
    await tester.pumpAndSettle();

    expect(servico.chamadas, 2);
    expect(servico.chavesRecebidas[1], servico.chavesRecebidas[0]);
    expect(find.text('Resultado da análise'), findsOneWidget);
  });
}

Future<void> _tocarBotaoAnalise(WidgetTester tester) async {
  final botao = find.widgetWithText(FilledButton, 'Realizar análise');
  await tester.ensureVisible(botao);
  await tester.pumpAndSettle();
  await tester.tap(botao);
}
