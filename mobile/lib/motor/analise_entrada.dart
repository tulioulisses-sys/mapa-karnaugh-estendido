import 'modelos.dart';
import 'parser_entrada.dart';

Map<(String, String, String), String> _registroRotulosProjeto(
  ProjetoSequencial projeto,
) {
  final destinosPorSaida = <String, List<String>>{};

  for (final etapa in projeto.etapas) {
    for (final movimento in etapa.movimentos) {
      final destinos = destinosPorSaida.putIfAbsent(movimento.saida, () => []);
      if (!destinos.contains(movimento.sensorDestino)) {
        destinos.add(movimento.sensorDestino);
      }
    }
  }

  final registro = <(String, String, String), String>{};
  for (final entrada in destinosPorSaida.entries) {
    final saida = entrada.key;
    final atuador = saida.substring(0, saida.length - 1);
    final sentido = saida.substring(saida.length - 1);
    final variosDestinos = entrada.value.length > 1;

    for (var indice = 0; indice < entrada.value.length; indice++) {
      final sensor = entrada.value[indice];
      registro[(atuador, sentido, sensor)] = variosDestinos
          ? '$saida(${indice + 1})'
          : saida;
    }
  }

  return registro;
}

String _descricaoMovimentoEntrada(
  ProjetoSequencial projeto,
  Movimento movimento,
) {
  final configuracao = projeto.atuadores[movimento.atuador]!;
  final destinoPadrao = movimento.sentido == '+'
      ? configuracao.sensorMaximo
      : configuracao.sensorMinimo;

  if (configuracao.quantidadePosicoes == 2 &&
      movimento.sensorDestino == destinoPadrao) {
    return movimento.saida;
  }

  return movimento.descricao;
}

String _descricaoEtapaCompacta(
  ProjetoSequencial projeto,
  EtapaSequencial etapa,
) {
  final movimentos = etapa.movimentos
      .map((movimento) => _descricaoMovimentoEntrada(projeto, movimento))
      .toList(growable: false);
  return movimentos.length > 1
      ? '(${movimentos.join(' ∥ ')})'
      : movimentos.single;
}

String _formatarProjetoCompacto(ProjetoSequencial projeto) {
  final loopsPorInicio = <int, LoopConfig>{
    for (final loop in projeto.loops) loop.inicio: loop,
  };
  final partes = <String>[];
  var indice = 0;

  while (indice < projeto.etapas.length) {
    final loop = loopsPorInicio[indice];
    if (loop == null) {
      partes.add(_descricaoEtapaCompacta(projeto, projeto.etapas[indice]));
      indice++;
      continue;
    }

    final conteudo = <String>[
      for (var posicao = loop.inicio; posicao <= loop.fim; posicao++)
        _descricaoEtapaCompacta(projeto, projeto.etapas[posicao]),
    ].join(', ');
    partes.add('[$conteudo] enquanto ${loop.sensor}=${loop.repetirQuando}');
    indice = loop.fim + 1;
  }

  return partes.join(' → ');
}

Map<String, Object> _loopParaMap(LoopConfig loop) {
  String literal(int valor) => valor == 1 ? loop.sensor : "${loop.sensor}'";

  return <String, Object>{
    'inicio': loop.inicio,
    'fim': loop.fim,
    'etapa_inicial': loop.inicio + 1,
    'etapa_final': loop.fim + 1,
    'retorna_para_etapa': loop.inicio + 1,
    'continua_na_etapa': loop.fim + 2,
    'sensor': loop.sensor,
    'repetir_quando': loop.repetirQuando,
    'sair_quando': loop.sairQuando,
    'condicao_repeticao': <String, int>{
      loop.sensor: loop.repetirQuando,
    },
    'condicao_saida': <String, int>{loop.sensor: loop.sairQuando},
    'condicao_repeticao_texto':
        '${loop.sensor} = ${loop.repetirQuando}',
    'condicao_saida_texto': '${loop.sensor} = ${loop.sairQuando}',
    'literal_repeticao': literal(loop.repetirQuando),
    'literal_saida': literal(loop.sairQuando),
    'quantidade_etapas': loop.quantidadeEtapas,
    'descricao': loop.descricao,
  };
}

/// Interpreta e valida a entrada sem calcular ainda as equações.
///
/// O formato retornado é equivalente ao `analisar_entrada` do motor Python e
/// funciona como contrato para as próximas etapas da migração.
Map<String, Object> analisarEntrada(Object sequencia) {
  final projeto = switch (sequencia) {
    ProjetoSequencial valor => valor,
    String valor => interpretarEntrada(valor),
    _ => throw const EntradaInvalidaException(
      'A entrada precisa ser um texto ou um ProjetoSequencial.',
    ),
  };
  projeto.validar();

  final registro = _registroRotulosProjeto(projeto);
  final etapas = <List<String>>[
    for (final etapa in projeto.etapas)
      <String>[
        for (final movimento in etapa.movimentos)
          registro[
            (movimento.atuador, movimento.sentido, movimento.sensorDestino)
          ]!,
      ],
  ];
  final multiposicao = <String>[
    for (final entrada in projeto.atuadores.entries)
      if (entrada.value.quantidadePosicoes > 2) entrada.key,
  ];

  return <String, Object>{
    'atuadores': projeto.atuadores.keys.toList(growable: false),
    'sensores_por_atuador': <String, List<String>>{
      for (final entrada in projeto.atuadores.entries)
        entrada.key: List.of(entrada.value.sensores),
    },
    'atuadores_multiposicao': multiposicao,
    'possui_atuador_multiposicao': multiposicao.isNotEmpty,
    'etapas': etapas,
    'quantidade_etapas': projeto.etapas.length,
    'sequencia_formatada': _formatarProjetoCompacto(projeto),
    'sequencia_normalizada': formatarProjeto(projeto),
    'estado_inicial': <String, int>{
      for (final entrada in projeto.atuadores.entries)
        entrada.key: entrada.value.indiceSensor(entrada.value.sensorInicial),
    },
    'sensores_iniciais': <String, String>{
      for (final entrada in projeto.atuadores.entries)
        entrada.key: entrada.value.sensorInicial,
    },
    'entradas_externas': List.of(projeto.entradasExternas),
    'loops': projeto.loops.map(_loopParaMap).toList(growable: false),
    'possui_loop': projeto.loops.isNotEmpty,
    'sinal_partida': projeto.sinalPartida,
  };
}
