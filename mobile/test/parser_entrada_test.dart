import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:mapa_karnaugh_app/motor.dart';

void main() {
  group('parser offline', () {
    test('reproduz integralmente as análises de referência do Python', () {
      final referencias = jsonDecode(
        File('test/fixtures/motor_referencias.json').readAsStringSync(),
      ) as Map<String, dynamic>;
      final casos = referencias['casos'] as List<dynamic>;

      for (final item in casos) {
        final caso = item as Map<String, dynamic>;
        final atual = analisarEntrada(caso['sequencia'] as String);

        expect(atual, equals(caso['analise']), reason: 'caso ${caso['id']}');
      }
    });

    test('aceita destinos pelas três notações previstas', () {
      final porTexto = interpretarEntrada('B+ até b1, B+ para b2, B- -> b0');
      final porIndice = interpretarEntrada('B+(1), B+(2), B-(0)');

      expect(formatarProjeto(porTexto), formatarProjeto(porIndice));
      expect(porTexto.atuadores['B']!.sensores, ['b0', 'b1', 'b2']);
    });

    test('normaliza diferentes sinais de menos', () {
      final projeto = interpretarEntrada('A+, A−');

      expect(formatarProjeto(projeto), 'A+ até a1, A- até a0');
    });
  });

  group('validação de entrada', () {
    final casos = <(String, String)>[
      ('', 'não pode estar vazia'),
      ('A+, B', 'Movimento inválido'),
      ('A+, A+', 'já está no sensor a1'),
      (
        'A+, (B+, B-), A-',
        'Um mesmo atuador não pode aparecer duas vezes',
      ),
    ];

    for (final caso in casos) {
      test('rejeita ${caso.$1.isEmpty ? 'entrada vazia' : caso.$1}', () {
        expect(
          () => interpretarEntrada(caso.$1),
          throwsA(
            isA<EntradaInvalidaException>().having(
              (erro) => erro.mensagem,
              'mensagem',
              contains(caso.$2),
            ),
          ),
        );
      });
    }
  });
}
