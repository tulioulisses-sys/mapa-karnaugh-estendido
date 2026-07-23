import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mapa_karnaugh_app/metodo/tela_sobre_metodo.dart';

void main() {
  testWidgets('apresenta a explicação completa do método', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: TelaSobreMetodo()),
    );

    const titulos = [
      'Objetivo do método',
      'Como o método funciona',
      'Condição mínima e qualificação dos comandos',
      'Pontos perigosos',
      'Recursos adicionais da plataforma',
      'Resultado fornecido pelo método',
    ];
    for (final titulo in titulos) {
      await tester.scrollUntilVisible(
        find.text(titulo),
        450,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text(titulo), findsOneWidget);
    }
  });

  testWidgets('inclui os três materiais de referência', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: TelaSobreMetodo()),
    );

    await tester.scrollUntilVisible(
      find.text('Guia rápido da plataforma'),
      600,
      scrollable: find.byType(Scrollable).first,
    );

    expect(find.text('Guia rápido da plataforma'), findsOneWidget);
    expect(find.text('Artigo sobre o método'), findsOneWidget);
    expect(find.text('Sistemas Automáticos'), findsOneWidget);

    const caminhos = [
      'assets/documentos/guia_rapido.pdf',
      'assets/documentos/metodo_projeto_otimo.pdf',
      'assets/documentos/sistemas_automaticos.pdf',
    ];
    for (final caminho in caminhos) {
      final documento = await rootBundle.load(caminho);
      expect(documento.lengthInBytes, greaterThan(0));
    }
  });
}
