import 'modelos.dart';

final _reMovimento = RegExp(
  r'^([A-Za-z][A-Za-z0-9_]*)\s*([+-])(?:\s*(?:(?:até|ate|para)\s*([A-Za-z][A-Za-z0-9_]*)|(?:->|→)\s*([A-Za-z][A-Za-z0-9_]*)|\(\s*(\d+)\s*\)))?$',
  caseSensitive: false,
);

final _reLoop = RegExp(
  r'^\[(.*)\]\s*(?:repetir\s+)?enquanto\s*([A-Za-z][A-Za-z0-9_]*)\s*=\s*([01])$',
  caseSensitive: false,
  dotAll: true,
);

final _reSensorNumerico = RegExp(
  r'^([A-Za-z][A-Za-z0-9_]*?)[_]?(\d+)$',
);

final class _MovimentoBruto {
  const _MovimentoBruto({
    required this.atuador,
    required this.sentido,
    this.sensorDestino,
  });

  final String atuador;
  final String sentido;
  final String? sensorDestino;
}

final class _EtapaBruta {
  const _EtapaBruta(this.movimentos);

  final List<_MovimentoBruto> movimentos;
}

final class _LoopBruto {
  const _LoopBruto({
    required this.inicio,
    required this.fim,
    required this.sensor,
    required this.repetirQuando,
  });

  final int inicio;
  final int fim;
  final String sensor;
  final int repetirQuando;
}

final class _FluxoBruto {
  const _FluxoBruto({
    required this.etapas,
    required this.loops,
    required this.entradasExternas,
  });

  final List<_EtapaBruta> etapas;
  final List<_LoopBruto> loops;
  final List<String> entradasExternas;
}

String _normalizarTexto(String texto) => texto
    .trim()
    .replaceAll('−', '-')
    .replaceAll('–', '-')
    .replaceAll('—', '-');

String _sensorPorIndice(String atuador, int indice) =>
    '${atuador.toLowerCase()}$indice';

int _indiceSensor(String sensor, String atuador) {
  final sensorLimpo = sensor.trim();
  final correspondencia = _reSensorNumerico.firstMatch(sensorLimpo);

  if (correspondencia == null) {
    throw EntradaInvalidaException(
      'Não foi possível determinar a ordem do sensor '
      "'$sensor'. Na entrada textual, utilize nomes como "
      '${atuador.toLowerCase()}0, ${atuador.toLowerCase()}1, '
      '${atuador.toLowerCase()}2 etc.',
    );
  }

  final prefixo = correspondencia.group(1)!.replaceFirst(RegExp(r'_$'), '');
  if (prefixo.toLowerCase() != atuador.toLowerCase()) {
    throw EntradaInvalidaException(
      "O sensor '$sensor' não corresponde ao atuador $atuador.",
    );
  }

  return int.parse(correspondencia.group(2)!);
}

List<String> _separarTopo(String texto) {
  final partes = <String>[];
  var atual = StringBuffer();
  var nivelParenteses = 0;
  var nivelColchetes = 0;

  for (final codigo in texto.runes) {
    final caractere = String.fromCharCode(codigo);

    if (caractere == '(') {
      nivelParenteses++;
      atual.write(caractere);
      continue;
    }

    if (caractere == ')') {
      nivelParenteses--;
      if (nivelParenteses < 0) {
        throw const EntradaInvalidaException(
          'Foi encontrado um parêntese de fechamento sem abertura.',
        );
      }
      atual.write(caractere);
      continue;
    }

    if (caractere == '[') {
      nivelColchetes++;
      if (nivelColchetes > 1) {
        throw const EntradaInvalidaException(
          'Loops aninhados ainda não são permitidos.',
        );
      }
      atual.write(caractere);
      continue;
    }

    if (caractere == ']') {
      nivelColchetes--;
      if (nivelColchetes < 0) {
        throw const EntradaInvalidaException(
          'Foi encontrado um colchete de fechamento sem abertura.',
        );
      }
      atual.write(caractere);
      continue;
    }

    if ((caractere == ',' || caractere == ';') &&
        nivelParenteses == 0 &&
        nivelColchetes == 0) {
      final trecho = atual.toString().trim();
      if (trecho.isNotEmpty) {
        partes.add(trecho);
      }
      atual = StringBuffer();
      continue;
    }

    atual.write(caractere);
  }

  if (nivelParenteses != 0) {
    throw const EntradaInvalidaException(
      'Os parênteses da sequência não estão balanceados.',
    );
  }

  if (nivelColchetes != 0) {
    throw const EntradaInvalidaException(
      'Os colchetes da sequência não estão balanceados.',
    );
  }

  final trecho = atual.toString().trim();
  if (trecho.isNotEmpty) {
    partes.add(trecho);
  }

  return partes;
}

List<String> _separarMovimentosSimultaneos(String texto) {
  var conteudo = texto.trim();

  if (conteudo.startsWith('(')) {
    if (!conteudo.endsWith(')')) {
      throw EntradaInvalidaException(
        "Parênteses inválidos na etapa '$texto'.",
      );
    }
    conteudo = conteudo.substring(1, conteudo.length - 1).trim();
  }

  final partes = conteudo
      .split(RegExp(r'[,;]'))
      .map((parte) => parte.trim())
      .where((parte) => parte.isNotEmpty)
      .toList();

  if (partes.isEmpty) {
    throw const EntradaInvalidaException('Foi encontrada uma etapa vazia.');
  }

  return partes;
}

_MovimentoBruto _interpretarMovimento(String texto) {
  final textoNormalizado = _normalizarTexto(texto);
  final correspondencia = _reMovimento.firstMatch(textoNormalizado);

  if (correspondencia == null) {
    throw EntradaInvalidaException(
      "Movimento inválido: '$textoNormalizado'. Use formatos como A+, B-, "
      'B+ até b2 ou B+(2).',
    );
  }

  final atuador = correspondencia.group(1)!.toUpperCase();
  final sentido = correspondencia.group(2)!;
  final sensor = correspondencia.group(3) ?? correspondencia.group(4);
  final indice = correspondencia.group(5);
  String? sensorDestino;

  if (sensor != null) {
    sensorDestino = _sensorPorIndice(
      atuador,
      _indiceSensor(sensor, atuador),
    );
  } else if (indice != null) {
    sensorDestino = _sensorPorIndice(atuador, int.parse(indice));
  }

  return _MovimentoBruto(
    atuador: atuador,
    sentido: sentido,
    sensorDestino: sensorDestino,
  );
}

_EtapaBruta _interpretarEtapa(String texto) {
  final movimentos = _separarMovimentosSimultaneos(texto)
      .map(_interpretarMovimento)
      .toList(growable: false);
  final atuadores = movimentos.map((movimento) => movimento.atuador).toList();

  if (atuadores.toSet().length != atuadores.length) {
    throw const EntradaInvalidaException(
      'Um mesmo atuador não pode aparecer duas vezes na mesma etapa.',
    );
  }

  return _EtapaBruta(movimentos);
}

_FluxoBruto _interpretarFluxo(String texto) {
  final trechos = _separarTopo(texto);
  if (trechos.isEmpty) {
    throw const EntradaInvalidaException('A sequência não pode estar vazia.');
  }

  final etapas = <_EtapaBruta>[];
  final loops = <_LoopBruto>[];
  final entradasExternas = <String>[];

  for (final trecho in trechos) {
    final trechoLimpo = trecho.trim();

    if (trechoLimpo.startsWith('[')) {
      final correspondencia = _reLoop.firstMatch(trechoLimpo);
      if (correspondencia == null) {
        throw EntradaInvalidaException(
          "Loop inválido: '$trecho'. Use o formato "
          '[C+, D+, C-, D-] enquanto e=0.',
        );
      }

      final conteudo = correspondencia.group(1)!.trim();
      if (conteudo.contains('[') || conteudo.contains(']')) {
        throw const EntradaInvalidaException(
          'Loops aninhados ainda não são permitidos.',
        );
      }

      final etapasLoopTexto = _separarTopo(conteudo);
      if (etapasLoopTexto.isEmpty) {
        throw const EntradaInvalidaException(
          'O loop precisa possuir pelo menos uma etapa.',
        );
      }

      final inicio = etapas.length;
      etapas.addAll(etapasLoopTexto.map(_interpretarEtapa));
      final fim = etapas.length - 1;
      final sensor = correspondencia.group(2)!.toLowerCase();
      final repetirQuando = int.parse(correspondencia.group(3)!);

      loops.add(
        _LoopBruto(
          inicio: inicio,
          fim: fim,
          sensor: sensor,
          repetirQuando: repetirQuando,
        ),
      );

      if (!entradasExternas.contains(sensor)) {
        entradasExternas.add(sensor);
      }
      continue;
    }

    if (trechoLimpo.contains('[') || trechoLimpo.contains(']')) {
      throw EntradaInvalidaException(
        "Colchetes inválidos no trecho '$trecho'.",
      );
    }

    etapas.add(_interpretarEtapa(trechoLimpo));
  }

  return _FluxoBruto(
    etapas: etapas,
    loops: loops,
    entradasExternas: entradasExternas,
  );
}

Map<String, List<_MovimentoBruto>> _movimentosPorAtuador(
  List<_EtapaBruta> etapas,
) {
  final resultado = <String, List<_MovimentoBruto>>{};

  for (final etapa in etapas) {
    for (final movimento in etapa.movimentos) {
      resultado.putIfAbsent(movimento.atuador, () => []).add(movimento);
    }
  }

  return resultado;
}

Map<String, AtuadorConfig> _inferirAtuadores(List<_EtapaBruta> etapas) {
  final atuadores = <String, AtuadorConfig>{};

  for (final entrada in _movimentosPorAtuador(etapas).entries) {
    final nome = entrada.key;
    final movimentos = entrada.value;
    final primeiroMovimento = movimentos.first;
    final indices = <int>{
      for (final movimento in movimentos)
        if (movimento.sensorDestino != null)
          _indiceSensor(movimento.sensorDestino!, nome),
    };

    if (indices.isEmpty) {
      indices.addAll([0, 1]);
    } else {
      final primeiroDestino = primeiroMovimento.sensorDestino == null
          ? null
          : _indiceSensor(primeiroMovimento.sensorDestino!, nome);

      if (primeiroMovimento.sentido == '+') {
        indices.add(0);
        if (primeiroDestino == 0) {
          throw EntradaInvalidaException(
            'O primeiro movimento de $nome é positivo, mas seu destino foi '
            'informado como ${_sensorPorIndice(nome, 0)}.',
          );
        }
      } else if (primeiroDestino == null) {
        final maior = indices.isEmpty
            ? 0
            : indices.reduce((a, b) => a > b ? a : b);
        indices.add(maior + 1);
      } else if (!indices.any((indice) => indice > primeiroDestino)) {
        indices.add(primeiroDestino + 1);
      }
    }

    if (indices.length < 2) {
      final menor = indices.isEmpty
          ? 0
          : indices.reduce((a, b) => a < b ? a : b);
      indices.add(menor + 1);
    }

    final indicesOrdenados = indices.toList()..sort();
    final sensores = indicesOrdenados
        .map((indice) => _sensorPorIndice(nome, indice))
        .toList(growable: false);
    final sensorInicial = primeiroMovimento.sentido == '+'
        ? sensores.first
        : sensores.last;

    atuadores[nome] = AtuadorConfig(
      nome: nome,
      sensores: sensores,
      sensorInicial: sensorInicial,
    );
  }

  return atuadores;
}

List<EtapaSequencial> _resolverDestinos(
  List<_EtapaBruta> etapasBrutas,
  Map<String, AtuadorConfig> atuadores,
) {
  var estadoAtual = <String, String>{
    for (final entrada in atuadores.entries)
      entrada.key: entrada.value.sensorInicial,
  };
  final etapas = <EtapaSequencial>[];

  for (var numeroEtapa = 0; numeroEtapa < etapasBrutas.length; numeroEtapa++) {
    final movimentosResolvidos = <Movimento>[];
    final novoEstado = Map<String, String>.of(estadoAtual);

    for (final movimentoBruto in etapasBrutas[numeroEtapa].movimentos) {
      final configuracao = atuadores[movimentoBruto.atuador]!;
      final sensorAtual = estadoAtual[movimentoBruto.atuador]!;
      final indiceAtual = configuracao.indiceSensor(sensorAtual);
      late final String sensorDestino;

      if (movimentoBruto.sensorDestino != null) {
        sensorDestino = configuracao.sensorCanonico(
          movimentoBruto.sensorDestino!,
        );
      } else if (configuracao.quantidadePosicoes == 2) {
        sensorDestino = movimentoBruto.sentido == '+'
            ? configuracao.sensorMaximo
            : configuracao.sensorMinimo;
      } else {
        final deslocamento = movimentoBruto.sentido == '+' ? 1 : -1;
        final indiceDestino = indiceAtual + deslocamento;

        if (indiceDestino < 0 || indiceDestino >= configuracao.sensores.length) {
          throw EntradaInvalidaException(
            'Etapa ${numeroEtapa + 1}: o movimento '
            '${movimentoBruto.atuador}${movimentoBruto.sentido} não possui '
            'um próximo sensor disponível. Informe o destino explicitamente, '
            'por exemplo ${movimentoBruto.atuador}${movimentoBruto.sentido} '
            'até ${movimentoBruto.atuador.toLowerCase()}2.',
          );
        }

        sensorDestino = configuracao.sensores[indiceDestino];
      }

      movimentosResolvidos.add(
        Movimento(
          atuador: movimentoBruto.atuador,
          sentido: movimentoBruto.sentido,
          sensorDestino: sensorDestino,
        ),
      );
      novoEstado[movimentoBruto.atuador] = sensorDestino;
    }

    etapas.add(EtapaSequencial(movimentos: movimentosResolvidos));
    estadoAtual = novoEstado;
  }

  return etapas;
}

/// Converte a sequência textual no modelo de domínio validado.
ProjetoSequencial interpretarEntrada(
  String texto, {
  String sinalPartida = 'S',
}) {
  final textoNormalizado = _normalizarTexto(texto);
  if (textoNormalizado.isEmpty) {
    throw const EntradaInvalidaException('A sequência não pode estar vazia.');
  }

  final fluxo = _interpretarFluxo(textoNormalizado);
  final atuadores = _inferirAtuadores(fluxo.etapas);
  final etapas = _resolverDestinos(fluxo.etapas, atuadores);
  final loops = fluxo.loops
      .map(
        (loop) => LoopConfig(
          inicio: loop.inicio,
          fim: loop.fim,
          sensor: loop.sensor,
          repetirQuando: loop.repetirQuando,
        ),
      )
      .toList(growable: false);
  final projeto = ProjetoSequencial(
    atuadores: atuadores,
    etapas: etapas,
    loops: loops,
    sinalPartida: sinalPartida,
    entradasExternas: fluxo.entradasExternas,
  );

  projeto.validar();
  return projeto;
}

/// Nome alternativo mantido para espelhar a API do motor Python.
ProjetoSequencial parsearEntrada(
  String texto, {
  String sinalPartida = 'S',
}) => interpretarEntrada(texto, sinalPartida: sinalPartida);

/// Gera a representação normalizada, com todos os destinos explícitos.
String formatarProjeto(ProjetoSequencial projeto) {
  projeto.validar();
  final loopsPorInicio = <int, LoopConfig>{
    for (final loop in projeto.loops) loop.inicio: loop,
  };
  final partes = <String>[];
  var indice = 0;

  while (indice < projeto.etapas.length) {
    final loop = loopsPorInicio[indice];
    if (loop == null) {
      partes.add(projeto.etapas[indice].descricao);
      indice++;
      continue;
    }

    final conteudo = <String>[
      for (var posicao = loop.inicio; posicao <= loop.fim; posicao++)
        projeto.etapas[posicao].descricao,
    ].join(', ');
    partes.add('[$conteudo] enquanto ${loop.sensor}=${loop.repetirQuando}');
    indice = loop.fim + 1;
  }

  return partes.join(', ');
}
