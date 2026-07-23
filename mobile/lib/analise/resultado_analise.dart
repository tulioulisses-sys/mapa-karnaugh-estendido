import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../visual/identidade_visual.dart';
import 'modelos_analise.dart';

class ResultadoAnaliseView extends StatefulWidget {
  const ResultadoAnaliseView({super.key, required this.resultado});

  final ResultadoAnalise resultado;

  @override
  State<ResultadoAnaliseView> createState() => _ResultadoAnaliseViewState();
}

class _ResultadoAnaliseViewState extends State<ResultadoAnaliseView> {
  int _abaAtual = 0;

  @override
  Widget build(BuildContext context) {
    final conteudos = <Widget>[
      _AbaResumo(resultado: widget.resultado),
      _AbaMapa(resultado: widget.resultado),
      _AbaEtapas(resultado: widget.resultado),
      _AbaResolucao(resultado: widget.resultado),
      _AbaEquacoes(resultado: widget.resultado),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CartaoInstitucional(
          destaque: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const CabecalhoEtapa(
                numero: 2,
                titulo: 'Resultado da resolução',
                descricao:
                    'Consulte o resumo, o mapa, a evolução das etapas, a '
                    'resolução completa do método e as equações finais.',
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  Chip(label: Text('${widget.resultado.etapas.length} etapas')),
                  Chip(
                    label: Text(
                      '${widget.resultado.atuadores.length} atuador(es)',
                    ),
                  ),
                  Chip(
                    label: Text(
                      widget.resultado.memorias.isEmpty
                          ? 'Sem memórias'
                          : 'Memórias: ${widget.resultado.memorias.join(', ')}',
                    ),
                  ),
                  Chip(
                    label: Text(widget.resultado.controleAcesso.rotuloCota),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        CartaoInstitucional(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: DefaultTabController(
            key: ValueKey(_abaAtual),
            length: 5,
            initialIndex: _abaAtual,
            child: TabBar(
              isScrollable: true,
              tabAlignment: TabAlignment.start,
              dividerColor: Colors.transparent,
              labelColor: CoresInstitucionais.vinho,
              unselectedLabelColor: CoresInstitucionais.textoSuave,
              indicatorColor: CoresInstitucionais.vinho,
              onTap: (indice) => setState(() => _abaAtual = indice),
              tabs: const [
                Tab(icon: Icon(Icons.dashboard_outlined), text: 'Resumo'),
                Tab(icon: Icon(Icons.grid_on_outlined), text: 'Mapa'),
                Tab(icon: Icon(Icons.timeline_outlined), text: 'Etapas'),
                Tab(
                  icon: Icon(Icons.fact_check_outlined),
                  text: 'Resolução do método',
                ),
                Tab(icon: Icon(Icons.functions), text: 'Equações'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: KeyedSubtree(
            key: ValueKey(_abaAtual),
            child: conteudos[_abaAtual],
          ),
        ),
      ],
    );
  }
}

class _AbaResumo extends StatelessWidget {
  const _AbaResumo({required this.resultado});

  final ResultadoAnalise resultado;

  @override
  Widget build(BuildContext context) {
    final quantidadeMemorias = resultado.memorias.length;
    final capacidade = 1 << quantidadeMemorias;
    final conflitos = _conflitosMemoria(resultado.etapas);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final largura = constraints.maxWidth >= 840
                ? (constraints.maxWidth - 36) / 4
                : constraints.maxWidth >= 480
                ? (constraints.maxWidth - 12) / 2
                : constraints.maxWidth;
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                SizedBox(
                  width: largura,
                  child: _Metrica(
                    rotulo: 'Atuadores',
                    valor: resultado.atuadores.length.toString(),
                    icone: Icons.precision_manufacturing_outlined,
                  ),
                ),
                SizedBox(
                  width: largura,
                  child: _Metrica(
                    rotulo: 'Etapas',
                    valor: resultado.etapas.length.toString(),
                    icone: Icons.route_outlined,
                  ),
                ),
                SizedBox(
                  width: largura,
                  child: _Metrica(
                    rotulo: 'Memórias',
                    valor: quantidadeMemorias.toString(),
                    icone: Icons.memory_outlined,
                  ),
                ),
                SizedBox(
                  width: largura,
                  child: _Metrica(
                    rotulo: 'Loops',
                    valor: resultado.loops.length.toString(),
                    icone: Icons.loop,
                  ),
                ),
              ],
            );
          },
        ),
        const SizedBox(height: 16),
        _AvisoResumo(
          icone: Icons.sensors_outlined,
          texto:
              'Estado inicial: ${_formatarSensores(resultado.sensoresIniciais)}',
        ),
        if (resultado.atuadoresMultiposicao.isNotEmpty) ...[
          const SizedBox(height: 12),
          _AvisoResumo(
            icone: Icons.linear_scale,
            texto:
                'Atuadores multiposição considerados: '
                '${resultado.atuadoresMultiposicao.join(', ')}',
            sucesso: true,
          ),
        ],
        if (resultado.loops.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SecaoResultado(
            titulo: 'Decisões do loop',
            descricao:
                'Condições usadas para repetir o trecho ou continuar a '
                'sequência.',
            child: _TabelaResultado(
              colunas: const [
                _ColunaTabela('Loop', 'Loop', 60),
                _ColunaTabela('Trecho', 'Trecho', 150),
                _ColunaTabela('Repetição', 'Repetição', 130),
                _ColunaTabela('Saída', 'Saída', 110),
                _ColunaTabela('Retorno', 'Retorno', 110),
                _ColunaTabela('Continuação', 'Continuação', 120),
              ],
              linhas: _linhasLoops(resultado.loops),
            ),
          ),
        ],
        const SizedBox(height: 16),
        _SecaoResultado(
          titulo: 'Necessidade de memórias',
          descricao:
              'Quantidade de estados auxiliares necessária para diferenciar '
              'regiões fisicamente repetidas.',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  Chip(label: Text('Memórias encontradas: $quantidadeMemorias')),
                  Chip(
                    label: Text(
                      'Capacidade: 2^$quantidadeMemorias = $capacidade',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                quantidadeMemorias == 0
                    ? 'Nenhuma memória interna foi necessária. Os sensores '
                          'físicos e as condições externas distinguem todas '
                          'as decisões.'
                    : 'Memórias utilizadas: ${resultado.memorias.join(', ')}',
              ),
              if (conflitos.isNotEmpty) ...[
                const SizedBox(height: 16),
                _TabelaResultado(
                  colunas: const [
                    _ColunaTabela(
                      'Estado físico repetido',
                      'Estado físico repetido',
                      200,
                    ),
                    _ColunaTabela('Etapas', 'Etapas', 110),
                    _ColunaTabela(
                      'Comandos seguintes',
                      'Comandos seguintes',
                      190,
                    ),
                    _ColunaTabela(
                      'Códigos utilizados',
                      'Códigos utilizados',
                      180,
                    ),
                  ],
                  linhas: conflitos,
                ),
              ],
            ],
          ),
        ),
        if (resultado.observacoes.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SecaoResultado(
            titulo: 'Observações',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final observacao in resultado.observacoes)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.info_outline, size: 18),
                        const SizedBox(width: 10),
                        Expanded(child: Text(observacao)),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
        if (resultado.versaoMotor.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(
            'Motor: ${resultado.versaoMotor}',
            textAlign: TextAlign.right,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ],
    );
  }
}

class _AbaMapa extends StatelessWidget {
  const _AbaMapa({required this.resultado});

  final ResultadoAnalise resultado;

  @override
  Widget build(BuildContext context) {
    if (resultado.mapaSvg == null) {
      return const _SecaoResultado(
        titulo: 'Mapa de Karnaugh estendido',
        child: Text(
          'O mapa não foi solicitado nesta análise. Ative “Gerar mapa de '
          'Karnaugh” e realize uma nova análise para visualizá-lo.',
        ),
      );
    }

    final largura = resultado.mapaLargura ?? 1200;
    final altura = resultado.mapaAltura ?? 720;
    final alturaExibicao = (altura * (900 / largura))
        .clamp(380.0, 720.0)
        .toDouble();

    return _SecaoResultado(
      titulo: 'Mapa de Karnaugh estendido',
      descricao: 'Use o gesto de pinça ou a roda do mouse para ampliar.',
      child: ClipRect(
        child: SizedBox(
          height: alturaExibicao,
          child: InteractiveViewer(
            minScale: 0.7,
            maxScale: 5,
            child: SvgPicture.string(
              resultado.mapaSvg!,
              width: largura,
              height: altura,
              fit: BoxFit.contain,
            ),
          ),
        ),
      ),
    );
  }
}

class _AbaEtapas extends StatelessWidget {
  const _AbaEtapas({required this.resultado});

  final ResultadoAnalise resultado;

  @override
  Widget build(BuildContext context) {
    return _SecaoResultado(
      titulo: 'Evolução da sequência',
      descricao:
          'Estado físico, condição externa, fase e código das memórias em '
          'cada movimento.',
      child: _TabelaResultado(
        alturaMaximaLinha: 120,
        colunas: const [
          _ColunaTabela('Etapa', 'Etapa', 65),
          _ColunaTabela('Comando', 'Comando', 150),
          _ColunaTabela('Estado antes', 'Estado antes', 190),
          _ColunaTabela('Estado depois', 'Estado depois', 190),
          _ColunaTabela('Condição externa', 'Condição externa', 160),
          _ColunaTabela('No loop', 'No loop', 75),
          _ColunaTabela('Fase', 'Fase', 65),
          _ColunaTabela('Memórias', 'Memórias', 140),
        ],
        linhas: _linhasEtapas(resultado.etapas),
      ),
    );
  }
}

class _AbaResolucao extends StatelessWidget {
  const _AbaResolucao({required this.resultado});

  final ResultadoAnalise resultado;

  @override
  Widget build(BuildContext context) {
    return _SecaoResultado(
      titulo: 'Qualificação dos comandos',
      descricao:
          'Demonstração completa da condição mínima até a equação final. '
          'Deslize a tabela horizontalmente para consultar todas as colunas.',
      child: resultado.resolucao.isEmpty
          ? const Text('Nenhuma linha de resolução foi produzida.')
          : _TabelaResultado(
              alturaMaximaLinha: 190,
              destacarResolucao: true,
              colunas: const [
                _ColunaTabela('Passo', 'Passo', 60),
                _ColunaTabela('Comando', 'Comando', 120),
                _ColunaTabela('Condição mínima', 'Condição mínima', 150),
                _ColunaTabela('Condição externa', 'Condição externa', 140),
                _ColunaTabela('Restrição do ramo', 'Restrição do ramo', 165),
                _ColunaTabela('Contracomando', 'Contracomando', 150),
                _ColunaTabela(
                  'Qualificador de diferenciação',
                  'Qualificador de diferenciação',
                  205,
                ),
                _ColunaTabela('Contato de parada', 'Contato de parada', 155),
                _ColunaTabela(
                  'Equação qualificada',
                  'Equação qualificada',
                  220,
                ),
                _ColunaTabela('Pontos perigosos', 'Pontos perigosos', 250),
                _ColunaTabela(
                  'Qualificador complementar',
                  'Qualificador complementar',
                  205,
                ),
                _ColunaTabela('Equação final', 'Equação final', 240),
              ],
              linhas: resultado.resolucao,
            ),
    );
  }
}

class _AbaEquacoes extends StatelessWidget {
  const _AbaEquacoes({required this.resultado});

  final ResultadoAnalise resultado;

  @override
  Widget build(BuildContext context) {
    return _SecaoResultado(
      titulo: 'Equações booleanas de comando',
      descricao:
          'Ocorrências lógicas, saídas físicas agregadas e equações completas '
          'das memórias.',
      child: _TabelaResultado(
        alturaMaximaLinha: 100,
        destacarEquacoes: true,
        colunas: const [
          _ColunaTabela('Tipo', 'Tipo', 190),
          _ColunaTabela('Saída', 'Saída', 120),
          _ColunaTabela('Equação', 'Equação', 430),
        ],
        linhas: _linhasEquacoes(resultado),
      ),
    );
  }
}

class _Metrica extends StatelessWidget {
  const _Metrica({
    required this.rotulo,
    required this.valor,
    required this.icone,
  });

  final String rotulo;
  final String valor;
  final IconData icone;

  @override
  Widget build(BuildContext context) {
    return CartaoInstitucional(
      padding: const EdgeInsets.all(18),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: CoresInstitucionais.vinhoFundo,
              borderRadius: BorderRadius.circular(11),
            ),
            child: Icon(icone, color: CoresInstitucionais.vinho),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  valor,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: CoresInstitucionais.vinho,
                  ),
                ),
                Text(rotulo),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AvisoResumo extends StatelessWidget {
  const _AvisoResumo({
    required this.icone,
    required this.texto,
    this.sucesso = false,
  });

  final IconData icone;
  final String texto;
  final bool sucesso;

  @override
  Widget build(BuildContext context) {
    final cor = sucesso
        ? CoresInstitucionais.sucesso
        : CoresInstitucionais.vinho;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: sucesso
            ? CoresInstitucionais.sucessoFundo
            : CoresInstitucionais.vinhoFundo,
        border: Border.all(
          color: sucesso
              ? const Color(0xFFCFE8D8)
              : const Color(0xFFEBD0D7),
        ),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(icone, color: cor),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              texto,
              style: TextStyle(color: cor, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _SecaoResultado extends StatelessWidget {
  const _SecaoResultado({
    required this.titulo,
    required this.child,
    this.descricao,
  });

  final String titulo;
  final String? descricao;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return CartaoInstitucional(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(titulo, style: Theme.of(context).textTheme.titleLarge),
          if (descricao != null) ...[
            const SizedBox(height: 5),
            Text(descricao!),
          ],
          const SizedBox(height: 16),
          child,
        ],
      ),
    );
  }
}

class _ColunaTabela {
  const _ColunaTabela(this.titulo, this.chave, this.largura);

  final String titulo;
  final String chave;
  final double largura;
}

class _TabelaResultado extends StatelessWidget {
  const _TabelaResultado({
    required this.colunas,
    required this.linhas,
    this.alturaMaximaLinha = 140,
    this.destacarResolucao = false,
    this.destacarEquacoes = false,
  });

  final List<_ColunaTabela> colunas;
  final List<Map<String, dynamic>> linhas;
  final double alturaMaximaLinha;
  final bool destacarResolucao;
  final bool destacarEquacoes;

  @override
  Widget build(BuildContext context) {
    if (linhas.isEmpty) {
      return const Text('Nenhum dado foi produzido para esta seção.');
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(11),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingRowColor: const WidgetStatePropertyAll(
            CoresInstitucionais.vinhoFundo,
          ),
          headingTextStyle: const TextStyle(
            color: CoresInstitucionais.vinhoEscuro,
            fontWeight: FontWeight.w700,
          ),
          dataTextStyle: const TextStyle(
            color: CoresInstitucionais.texto,
            height: 1.35,
          ),
          border: TableBorder.all(color: CoresInstitucionais.borda),
          dividerThickness: 0,
          horizontalMargin: 14,
          columnSpacing: 18,
          dataRowMinHeight: 52,
          dataRowMaxHeight: alturaMaximaLinha,
          columns: [
            for (final coluna in colunas)
              DataColumn(
                label: SizedBox(
                  width: coluna.largura,
                  child: Text(coluna.titulo),
                ),
              ),
          ],
          rows: [
            for (final linha in linhas)
              DataRow(
                cells: [
                  for (final coluna in colunas)
                    DataCell(
                      SizedBox(
                        width: coluna.largura,
                        child: SelectableText(
                          _textoTabela(linha[coluna.chave]),
                          style: _estiloCelula(coluna, linha),
                        ),
                      ),
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  TextStyle? _estiloCelula(
    _ColunaTabela coluna,
    Map<String, dynamic> linha,
  ) {
    final texto = _textoTabela(linha[coluna.chave]);

    if (destacarResolucao && coluna.chave == 'Pontos perigosos') {
      return TextStyle(
        color: texto == 'Nenhum'
            ? CoresInstitucionais.sucesso
            : CoresInstitucionais.erro,
        fontWeight: FontWeight.w700,
      );
    }
    if (
        (destacarResolucao && coluna.chave.contains('Equação')) ||
        (destacarEquacoes && coluna.chave == 'Equação')) {
      return const TextStyle(
        color: CoresInstitucionais.vinhoEscuro,
        fontFamily: 'monospace',
        fontWeight: FontWeight.w600,
      );
    }
    if (destacarEquacoes && coluna.chave == 'Saída') {
      return const TextStyle(
        color: CoresInstitucionais.vinho,
        fontWeight: FontWeight.w700,
      );
    }
    return null;
  }
}

List<Map<String, dynamic>> _linhasEtapas(
  List<Map<String, dynamic>> etapas,
) {
  return [
    for (final etapa in etapas)
      {
        'Etapa': etapa['numero'] ?? '—',
        'Comando': etapa['comando_texto'] ?? '—',
        'Estado antes': _estadoEtapa(etapa, antes: true),
        'Estado depois': _estadoEtapa(etapa, antes: false),
        'Condição externa': _tracoSeNenhuma(
          etapa['condicao_externa_texto'],
        ),
        'No loop': etapa['pertence_loop'] == true ? 'Sim' : 'Não',
        'Fase': 'F${etapa['fase'] ?? 0}',
        'Memórias': _formatarMemorias(etapa['codigo_memorias']),
      },
  ];
}

List<Map<String, dynamic>> _linhasLoops(
  List<Map<String, dynamic>> loops,
) {
  return [
    for (var indice = 0; indice < loops.length; indice++)
      {
        'Loop': indice + 1,
        'Trecho':
            'Etapas ${loops[indice]['etapa_inicial'] ?? '—'} a '
            '${loops[indice]['etapa_final'] ?? '—'}',
        'Repetição': loops[indice]['condicao_repeticao_texto'] ?? '—',
        'Saída': loops[indice]['condicao_saida_texto'] ?? '—',
        'Retorno': 'Etapa ${loops[indice]['retorna_para_etapa'] ?? '—'}',
        'Continuação':
            'Etapa ${loops[indice]['continua_na_etapa'] ?? '—'}',
      },
  ];
}

List<Map<String, dynamic>> _linhasEquacoes(ResultadoAnalise resultado) {
  final linhas = <Map<String, dynamic>>[];
  final comandos = resultado.equacoesComandos.isEmpty
      ? resultado.equacoes
      : resultado.equacoesComandos;

  for (final equacao in comandos.entries) {
    linhas.add({
      'Tipo': 'Ocorrência lógica',
      'Saída': equacao.key,
      'Equação': equacao.value,
    });
  }

  for (final equacao in resultado.equacoesFisicas.entries) {
    if (comandos[equacao.key] == equacao.value) continue;
    linhas.add({
      'Tipo': 'Saída física agregada',
      'Saída': equacao.key,
      'Equação': equacao.value,
    });
  }

  for (final equacao in resultado.equacoesMemorias.entries) {
    linhas.add({
      'Tipo': 'Memória completa',
      'Saída': equacao.key,
      'Equação': equacao.value,
    });
  }

  return linhas;
}

List<Map<String, dynamic>> _conflitosMemoria(
  List<Map<String, dynamic>> etapas,
) {
  final grupos = <String, List<Map<String, dynamic>>>{};
  for (final etapa in etapas) {
    final estado = _estadoEtapa(etapa, antes: true);
    grupos.putIfAbsent(estado, () => []).add(etapa);
  }

  final conflitos = <Map<String, dynamic>>[];
  for (final grupo in grupos.entries) {
    final codigos = <String>{};
    for (final etapa in grupo.value) {
      codigos.add(_formatarMemorias(etapa['codigo_memorias']));
    }
    if (codigos.length <= 1) continue;

    conflitos.add({
      'Estado físico repetido': grupo.key,
      'Etapas': grupo.value.map((etapa) => etapa['numero']).join(', '),
      'Comandos seguintes': grupo.value
          .map((etapa) => etapa['comando_texto'] ?? '—')
          .join(', '),
      'Códigos utilizados': codigos.join(', '),
    });
  }
  return conflitos;
}

String _estadoEtapa(Map<String, dynamic> etapa, {required bool antes}) {
  final texto = etapa[antes ? 'estado_antes_texto' : 'estado_depois_texto'];
  if (texto != null && texto.toString().trim().isNotEmpty) {
    return texto.toString();
  }
  final sensores = etapa[
      antes ? 'sensores_ativos_antes' : 'sensores_ativos_depois'];
  return _formatarSensores(_mapaTexto(sensores));
}

String _formatarSensores(Map<String, String> sensores) {
  if (sensores.isEmpty) return '—';
  return sensores.values.join(' · ');
}

String _formatarMemorias(Object? valor) {
  final memorias = _mapaTexto(valor);
  if (memorias.isEmpty) return '—';
  return memorias.entries
      .map((item) => '${item.key.toLowerCase()}${item.value}')
      .join(' · ');
}

Map<String, String> _mapaTexto(Object? valor) {
  if (valor is! Map) return const {};
  return valor.map(
    (chave, conteudo) => MapEntry(chave.toString(), conteudo.toString()),
  );
}

String _tracoSeNenhuma(Object? valor) {
  final texto = _textoTabela(valor);
  return texto == 'Nenhuma' ? '—' : texto;
}

String _textoTabela(Object? valor) {
  if (valor == null || valor.toString().trim().isEmpty) return '—';
  return valor.toString();
}
