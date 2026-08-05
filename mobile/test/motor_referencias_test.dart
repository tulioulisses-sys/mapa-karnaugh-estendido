import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('referências do motor Python cobrem os recursos principais', () {
    final arquivo = File('test/fixtures/motor_referencias.json');

    expect(arquivo.existsSync(), isTrue);

    final referencias =
        jsonDecode(arquivo.readAsStringSync()) as Map<String, dynamic>;
    final casos = referencias['casos'] as List<dynamic>;
    final ids = casos
        .map((caso) => (caso as Map<String, dynamic>)['id'] as String)
        .toSet();

    expect(referencias['schema_version'], 1);
    expect(referencias['motor_python_version'], isNotEmpty);
    expect(ids, {'simples', 'simultaneo', 'multiposicao', 'loop'});
  });
}
