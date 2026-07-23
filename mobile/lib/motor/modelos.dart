/// Erro de validação apresentado ao usuário quando a sequência é inválida.
final class EntradaInvalidaException implements Exception {
  const EntradaInvalidaException(this.mensagem);

  final String mensagem;

  @override
  String toString() => mensagem;
}

String _nomeNormalizado(String nome) => nome.trim().toLowerCase();

void _validarNome(String nome, String descricao) {
  if (nome.trim().isEmpty) {
    throw EntradaInvalidaException('$descricao precisa possuir um nome.');
  }
}

void _verificarRepetidos(Iterable<String> nomes, String descricao) {
  final normalizados = nomes.map(_nomeNormalizado).toList(growable: false);
  final repetidos = normalizados
      .where(
        (nome) => normalizados.where((candidato) => candidato == nome).length > 1,
      )
      .toSet()
      .toList()
    ..sort();

  if (repetidos.isNotEmpty) {
    throw EntradaInvalidaException(
      '$descricao possui nomes repetidos: ${repetidos.join(', ')}.',
    );
  }
}

/// Configuração de um atuador e de suas posições monitoradas.
final class AtuadorConfig {
  AtuadorConfig({
    required this.nome,
    required List<String> sensores,
    required this.sensorInicial,
  }) : sensores = List.unmodifiable(sensores);

  final String nome;
  final List<String> sensores;
  final String sensorInicial;

  void validar() {
    _validarNome(nome, 'O atuador');

    if (sensores.length < 2) {
      throw EntradaInvalidaException(
        'O atuador $nome precisa possuir pelo menos dois sensores.',
      );
    }

    for (final sensor in sensores) {
      _validarNome(sensor, 'Um sensor do atuador $nome');
    }

    _verificarRepetidos(sensores, 'O atuador $nome');

    if (!sensores.any(
      (sensor) => _nomeNormalizado(sensor) == _nomeNormalizado(sensorInicial),
    )) {
      throw EntradaInvalidaException(
        'O sensor inicial $sensorInicial não pertence ao atuador $nome.',
      );
    }
  }

  int indiceSensor(String sensor) {
    final procurado = _nomeNormalizado(sensor);

    for (var indice = 0; indice < sensores.length; indice++) {
      if (_nomeNormalizado(sensores[indice]) == procurado) {
        return indice;
      }
    }

    throw EntradaInvalidaException(
      'O sensor $sensor não pertence ao atuador $nome.',
    );
  }

  String sensorCanonico(String sensor) => sensores[indiceSensor(sensor)];

  int get quantidadePosicoes => sensores.length;

  String get sensorMinimo => sensores.first;

  String get sensorMaximo => sensores.last;
}

/// Movimento normalizado de um atuador, sempre com destino explícito.
final class Movimento {
  const Movimento({
    required this.atuador,
    required this.sentido,
    required this.sensorDestino,
  });

  final String atuador;
  final String sentido;
  final String sensorDestino;

  void validar() {
    _validarNome(atuador, 'O movimento');

    if (sentido != '+' && sentido != '-') {
      throw EntradaInvalidaException(
        "Sentido inválido no movimento do atuador $atuador: '$sentido'.",
      );
    }

    _validarNome(
      sensorDestino,
      'O sensor de destino do movimento $atuador$sentido',
    );
  }

  String get saida => '$atuador$sentido';

  String get descricao => '$saida até $sensorDestino';
}

/// Uma etapa com um ou mais movimentos simultâneos.
final class EtapaSequencial {
  EtapaSequencial({required List<Movimento> movimentos})
    : movimentos = List.unmodifiable(movimentos);

  final List<Movimento> movimentos;

  void validar() {
    if (movimentos.isEmpty) {
      throw const EntradaInvalidaException('Uma etapa não pode estar vazia.');
    }

    for (final movimento in movimentos) {
      movimento.validar();
    }

    final atuadores = movimentos
        .map((movimento) => _nomeNormalizado(movimento.atuador))
        .toList(growable: false);

    if (atuadores.toSet().length != atuadores.length) {
      throw const EntradaInvalidaException(
        'Um mesmo atuador não pode aparecer duas vezes na mesma etapa.',
      );
    }
  }

  bool get simultanea => movimentos.length > 1;

  String get descricao {
    final textos = movimentos.map((movimento) => movimento.descricao).toList();
    return simultanea ? '(${textos.join(', ')})' : textos.single;
  }
}

/// Configuração de um trecho repetitivo da sequência.
final class LoopConfig {
  const LoopConfig({
    required this.inicio,
    required this.fim,
    required this.sensor,
    this.repetirQuando = 0,
  });

  final int inicio;
  final int fim;
  final String sensor;
  final int repetirQuando;

  int get sairQuando => 1 - repetirQuando;

  int get quantidadeEtapas => fim - inicio + 1;

  String get descricao =>
      'etapas ${inicio + 1} a ${fim + 1}, '
      'repetir enquanto $sensor = $repetirQuando';

  void validar(int quantidadeTotalEtapas) {
    if (quantidadeTotalEtapas <= 0) {
      throw const EntradaInvalidaException(
        'Não é possível criar um loop sem etapas.',
      );
    }

    if (inicio < 0 || inicio >= quantidadeTotalEtapas) {
      throw const EntradaInvalidaException('O início do loop é inválido.');
    }

    if (fim < inicio || fim >= quantidadeTotalEtapas) {
      throw const EntradaInvalidaException('O final do loop é inválido.');
    }

    if (repetirQuando != 0 && repetirQuando != 1) {
      throw const EntradaInvalidaException(
        'A condição de repetição precisa ser 0 ou 1.',
      );
    }

    _validarNome(sensor, 'O sensor de decisão do loop');
  }
}

/// Modelo completo e validado de entrada do solucionador.
final class ProjetoSequencial {
  ProjetoSequencial({
    required Map<String, AtuadorConfig> atuadores,
    required List<EtapaSequencial> etapas,
    List<LoopConfig> loops = const [],
    this.sinalPartida = 'S',
    List<String> entradasExternas = const [],
  }) : atuadores = Map.unmodifiable(atuadores),
       etapas = List.unmodifiable(etapas),
       loops = List.unmodifiable(loops),
       entradasExternas = List.unmodifiable(entradasExternas);

  final Map<String, AtuadorConfig> atuadores;
  final List<EtapaSequencial> etapas;
  final List<LoopConfig> loops;
  final String sinalPartida;
  final List<String> entradasExternas;

  void validar() {
    _validarEstruturaBasica();
    _validarAtuadores();
    _validarEntradasExternas();
    _validarConflitosDeNomes();
    final estados = _validarESimularEtapas();
    _validarLoops(estados);
  }

  void _validarEstruturaBasica() {
    if (atuadores.isEmpty) {
      throw const EntradaInvalidaException(
        'É necessário cadastrar pelo menos um atuador.',
      );
    }

    if (etapas.isEmpty) {
      throw const EntradaInvalidaException(
        'É necessário cadastrar pelo menos uma etapa.',
      );
    }

    _validarNome(sinalPartida, 'O sinal de partida');
  }

  void _validarAtuadores() {
    final nomesAtuadores = <String>[];

    for (final entrada in atuadores.entries) {
      entrada.value.validar();

      if (_nomeNormalizado(entrada.key) !=
          _nomeNormalizado(entrada.value.nome)) {
        throw EntradaInvalidaException(
          "A chave '${entrada.key}' não corresponde ao atuador "
          "'${entrada.value.nome}'.",
        );
      }

      nomesAtuadores.add(entrada.value.nome);
    }

    _verificarRepetidos(nomesAtuadores, 'O cadastro de atuadores');
  }

  void _validarEntradasExternas() {
    for (final entrada in entradasExternas) {
      _validarNome(entrada, 'Uma entrada externa');
    }
    _verificarRepetidos(entradasExternas, 'O cadastro de entradas externas');
  }

  void _validarConflitosDeNomes() {
    final ocupados = <String, String>{};

    void registrar(String nome, String descricao) {
      final chave = _nomeNormalizado(nome);
      final anterior = ocupados[chave];

      if (anterior != null) {
        throw EntradaInvalidaException(
          "O nome '$nome' está sendo utilizado por $descricao "
          'e também por $anterior.',
        );
      }

      ocupados[chave] = descricao;
    }

    for (final atuador in atuadores.values) {
      registrar(atuador.nome, 'o atuador ${atuador.nome}');
      for (final sensor in atuador.sensores) {
        registrar(sensor, 'o sensor $sensor do atuador ${atuador.nome}');
      }
    }

    for (final entrada in entradasExternas) {
      registrar(entrada, 'a entrada externa $entrada');
    }

    registrar(sinalPartida, 'o sinal de partida $sinalPartida');
  }

  AtuadorConfig _obterAtuador(String nome) {
    final procurado = _nomeNormalizado(nome);

    for (final entrada in atuadores.entries) {
      if (_nomeNormalizado(entrada.key) == procurado ||
          _nomeNormalizado(entrada.value.nome) == procurado) {
        return entrada.value;
      }
    }

    throw EntradaInvalidaException('O atuador $nome não foi cadastrado.');
  }

  List<Map<String, String>> _validarESimularEtapas() {
    var estadoAtual = <String, String>{
      for (final atuador in atuadores.values)
        atuador.nome: atuador.sensorCanonico(atuador.sensorInicial),
    };
    final estados = <Map<String, String>>[Map.of(estadoAtual)];

    for (var indiceEtapa = 0; indiceEtapa < etapas.length; indiceEtapa++) {
      final etapa = etapas[indiceEtapa];
      etapa.validar();
      final proximoEstado = Map<String, String>.of(estadoAtual);

      for (final movimento in etapa.movimentos) {
        final configuracao = _obterAtuador(movimento.atuador);
        final sensorAtual = estadoAtual[configuracao.nome]!;
        final indiceAtual = configuracao.indiceSensor(sensorAtual);
        final indiceDestino = configuracao.indiceSensor(
          movimento.sensorDestino,
        );

        if (indiceDestino == indiceAtual) {
          throw EntradaInvalidaException(
            'Etapa ${indiceEtapa + 1}: o atuador ${configuracao.nome} '
            'já está no sensor ${movimento.sensorDestino}.',
          );
        }

        if (movimento.sentido == '+' && indiceDestino < indiceAtual) {
          throw EntradaInvalidaException(
            'Etapa ${indiceEtapa + 1}: o movimento ${movimento.saida} '
            'não pode ir de $sensorAtual para ${movimento.sensorDestino}. '
            'O sentido positivo deve avançar na ordem dos sensores.',
          );
        }

        if (movimento.sentido == '-' && indiceDestino > indiceAtual) {
          throw EntradaInvalidaException(
            'Etapa ${indiceEtapa + 1}: o movimento ${movimento.saida} '
            'não pode ir de $sensorAtual para ${movimento.sensorDestino}. '
            'O sentido negativo deve retornar na ordem dos sensores.',
          );
        }

        proximoEstado[configuracao.nome] = configuracao.sensorCanonico(
          movimento.sensorDestino,
        );
      }

      estadoAtual = proximoEstado;
      estados.add(Map.of(estadoAtual));
    }

    return estados;
  }

  void _validarLoops(List<Map<String, String>> estados) {
    final entradasNormalizadas = entradasExternas.map(_nomeNormalizado).toSet();

    for (final loop in loops) {
      loop.validar(etapas.length);
      if (!entradasNormalizadas.contains(_nomeNormalizado(loop.sensor))) {
        throw EntradaInvalidaException(
          'O sensor externo ${loop.sensor} utilizado no loop não foi '
          'cadastrado.',
        );
      }
    }

    _validarSobreposicaoLoops();

    for (final loop in loops) {
      final estadoEntrada = estados[loop.inicio];
      final estadoSaida = estados[loop.fim + 1];

      if (!_mapasIguais(estadoEntrada, estadoSaida)) {
        final diferencas = <String>[];
        for (final atuador in atuadores.values) {
          final antes = estadoEntrada[atuador.nome];
          final depois = estadoSaida[atuador.nome];
          if (antes != depois) {
            diferencas.add('${atuador.nome}: $antes → $depois');
          }
        }

        throw EntradaInvalidaException(
          'O trecho configurado como loop não retorna ao estado físico '
          'necessário para uma nova repetição. Diferenças encontradas: '
          '${diferencas.join(', ')}.',
        );
      }
    }
  }

  void _validarSobreposicaoLoops() {
    final ordenados = List<LoopConfig>.of(loops)
      ..sort((a, b) {
        final porInicio = a.inicio.compareTo(b.inicio);
        return porInicio != 0 ? porInicio : a.fim.compareTo(b.fim);
      });

    for (var indice = 1; indice < ordenados.length; indice++) {
      final anterior = ordenados[indice - 1];
      final atual = ordenados[indice];
      if (atual.inicio <= anterior.fim) {
        throw EntradaInvalidaException(
          'Os loops configurados entre as etapas '
          '${anterior.inicio + 1}–${anterior.fim + 1} e '
          '${atual.inicio + 1}–${atual.fim + 1} estão sobrepostos. '
          'Loops sobrepostos ou aninhados ainda não são permitidos.',
        );
      }
    }
  }

  Map<String, String> estadoInicial() => <String, String>{
    for (final atuador in atuadores.values)
      atuador.nome: atuador.sensorCanonico(atuador.sensorInicial),
  };

  List<Map<String, String>> simularEstados() {
    validar();
    return _validarESimularEtapas();
  }

  List<String> sensoresFisicos() => <String>[
    for (final atuador in atuadores.values) ...atuador.sensores,
  ];

  LoopConfig? obterLoopDaEtapa(int indiceEtapa) {
    for (final loop in loops) {
      if (loop.inicio <= indiceEtapa && indiceEtapa <= loop.fim) {
        return loop;
      }
    }
    return null;
  }
}

bool _mapasIguais(Map<String, String> primeiro, Map<String, String> segundo) {
  if (primeiro.length != segundo.length) {
    return false;
  }

  for (final entrada in primeiro.entries) {
    if (segundo[entrada.key] != entrada.value) {
      return false;
    }
  }

  return true;
}
