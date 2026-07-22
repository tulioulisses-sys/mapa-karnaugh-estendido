import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import 'modelos_analise.dart';
import 'servico_analise.dart';

class TelaAnalise extends StatefulWidget {
  const TelaAnalise({
    super.key,
    required this.servico,
    this.onAnaliseConcluida,
  });

  final ServicoAnalise servico;
  final VoidCallback? onAnaliseConcluida;

  @override
  State<TelaAnalise> createState() => _TelaAnaliseState();
}

class _TelaAnaliseState extends State<TelaAnalise> {
  final _formulario = GlobalKey<FormState>();
  final _sequencia = TextEditingController();
  bool _cicloContinuo = false;
  bool _incluirMapa = true;
  bool _processando = false;
  String? _chavePendente;
  String? _mensagemErro;
  ResultadoAnalise? _resultado;

  @override
  void initState() {
    super.initState();
    _sequencia.addListener(_entradaAlterada);
  }

  @override
  void dispose() {
    _sequencia
      ..removeListener(_entradaAlterada)
      ..dispose();
    super.dispose();
  }

  void _entradaAlterada() {
    if (!_processando) _chavePendente = null;
  }

  void _alterarCiclo(bool valor) {
    setState(() {
      _cicloContinuo = valor;
      _chavePendente = null;
    });
  }

  void _alterarMapa(bool valor) {
    setState(() {
      _incluirMapa = valor;
      _chavePendente = null;
    });
  }

  void _usarExemplo() {
    _sequencia.text = 'A+, B+, B-, A-';
  }

  Future<void> _resolver() async {
    if (_processando || !_formulario.currentState!.validate()) return;
    final chave = _chavePendente ?? _novaChaveIdempotencia();
    _chavePendente = chave;

    setState(() {
      _processando = true;
      _mensagemErro = null;
    });

    try {
      final resultado = await widget.servico.resolver(
        sequencia: _sequencia.text,
        chaveIdempotencia: chave,
        cicloContinuo: _cicloContinuo,
        incluirMapa: _incluirMapa,
      );
      if (!mounted) return;
      setState(() {
        _resultado = resultado;
        _chavePendente = null;
      });
      widget.onAnaliseConcluida?.call();
    } on FalhaAnalise catch (erro) {
      if (!mounted) return;
      setState(() => _mensagemErro = erro.mensagem);
    } finally {
      if (mounted) setState(() => _processando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nova análise')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 980),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _FormularioAnalise(
                      formulario: _formulario,
                      sequencia: _sequencia,
                      cicloContinuo: _cicloContinuo,
                      incluirMapa: _incluirMapa,
                      processando: _processando,
                      onAlterarCiclo: _alterarCiclo,
                      onAlterarMapa: _alterarMapa,
                      onUsarExemplo: _usarExemplo,
                      onResolver: _resolver,
                    ),
                    if (_mensagemErro != null) ...[
                      const SizedBox(height: 16),
                      _AvisoErro(mensagem: _mensagemErro!),
                    ],
                    if (_resultado != null) ...[
                      const SizedBox(height: 24),
                      _Resultado(resultado: _resultado!),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FormularioAnalise extends StatelessWidget {
  const _FormularioAnalise({
    required this.formulario,
    required this.sequencia,
    required this.cicloContinuo,
    required this.incluirMapa,
    required this.processando,
    required this.onAlterarCiclo,
    required this.onAlterarMapa,
    required this.onUsarExemplo,
    required this.onResolver,
  });

  final GlobalKey<FormState> formulario;
  final TextEditingController sequencia;
  final bool cicloContinuo;
  final bool incluirMapa;
  final bool processando;
  final ValueChanged<bool> onAlterarCiclo;
  final ValueChanged<bool> onAlterarMapa;
  final VoidCallback onUsarExemplo;
  final VoidCallback onResolver;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: formulario,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Sequência de movimentos',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              const Text(
                'Informe os movimentos na ordem de execução. Movimentos '
                'simultâneos podem ser escritos entre parênteses.',
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: sequencia,
                enabled: !processando,
                minLines: 3,
                maxLines: 8,
                maxLength: 20000,
                decoration: const InputDecoration(
                  labelText: 'Sequência',
                  hintText: 'Exemplo: A+, B+, B-, A-',
                  alignLabelWithHint: true,
                ),
                validator: (valor) {
                  if ((valor ?? '').trim().isEmpty) {
                    return 'Informe a sequência que deseja analisar.';
                  }
                  return null;
                },
              ),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: processando ? null : onUsarExemplo,
                  icon: const Icon(Icons.auto_fix_high_outlined),
                  label: const Text('Usar exemplo A+, B+, B-, A-'),
                ),
              ),
              const Divider(height: 28),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Ciclo contínuo'),
                subtitle: const Text(
                  'Ative somente quando o estado final fechar o ciclo.',
                ),
                value: cicloContinuo,
                onChanged: processando ? null : onAlterarCiclo,
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Gerar mapa de Karnaugh'),
                subtitle: const Text(
                  'Inclui a representação visual completa no resultado.',
                ),
                value: incluirMapa,
                onChanged: processando ? null : onAlterarMapa,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: processando ? null : onResolver,
                icon: processando
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.play_arrow),
                label: Text(processando ? 'Analisando...' : 'Realizar análise'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Resultado extends StatelessWidget {
  const _Resultado({required this.resultado});

  final ResultadoAnalise resultado;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.check_circle_outline,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(width: 12),
                    Text(
                      'Análise concluída',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    Chip(label: Text('${resultado.etapas.length} etapas')),
                    Chip(
                      label: Text('${resultado.atuadores.length} atuador(es)'),
                    ),
                    Chip(
                      label: Text(
                        resultado.memorias.isEmpty
                            ? 'Sem memórias'
                            : 'Memórias: ${resultado.memorias.join(', ')}',
                      ),
                    ),
                    Chip(label: Text(resultado.controleAcesso.rotuloCota)),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        _SecaoEquacoes(
          titulo: 'Equações dos comandos',
          equacoes: resultado.equacoes,
        ),
        if (resultado.equacoesMemorias.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SecaoEquacoes(
            titulo: 'Equações completas das memórias',
            equacoes: resultado.equacoesMemorias,
          ),
        ],
        if (resultado.mapaSvg != null) ...[
          const SizedBox(height: 16),
          _SecaoMapa(resultado: resultado),
        ],
        if (resultado.validacoes.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SecaoLista(
            titulo: 'Validações',
            itens: resultado.validacoes,
            icone: Icons.verified_outlined,
          ),
        ],
        if (resultado.observacoes.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SecaoLista(
            titulo: 'Observações',
            itens: resultado.observacoes,
            icone: Icons.info_outline,
          ),
        ],
      ],
    );
  }
}

class _SecaoEquacoes extends StatelessWidget {
  const _SecaoEquacoes({required this.titulo, required this.equacoes});

  final String titulo;
  final Map<String, String> equacoes;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(titulo, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            if (equacoes.isEmpty)
              const Text('Nenhuma equação foi necessária.')
            else
              SelectionArea(
                child: Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    for (final equacao in equacoes.entries)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 10,
                        ),
                        decoration: BoxDecoration(
                          color: Theme.of(
                            context,
                          ).colorScheme.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text(
                          '${equacao.key} = ${equacao.value}',
                          style: const TextStyle(
                            fontFamily: 'monospace',
                            fontSize: 15,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SecaoMapa extends StatelessWidget {
  const _SecaoMapa({required this.resultado});

  final ResultadoAnalise resultado;

  @override
  Widget build(BuildContext context) {
    final largura = resultado.mapaLargura ?? 1200;
    final altura = resultado.mapaAltura ?? 720;
    final alturaExibicao = (altura * (900 / largura))
        .clamp(380.0, 720.0)
        .toDouble();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Mapa de Karnaugh estendido',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 4),
            const Text('Use o gesto de pinça ou a roda do mouse para ampliar.'),
            const SizedBox(height: 16),
            ClipRect(
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
          ],
        ),
      ),
    );
  }
}

class _SecaoLista extends StatelessWidget {
  const _SecaoLista({
    required this.titulo,
    required this.itens,
    required this.icone,
  });

  final String titulo;
  final List<String> itens;
  final IconData icone;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(titulo, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            for (final item in itens)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(icone, size: 18),
                    const SizedBox(width: 10),
                    Expanded(child: Text(item)),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _AvisoErro extends StatelessWidget {
  const _AvisoErro({required this.mensagem});

  final String mensagem;

  @override
  Widget build(BuildContext context) {
    final cores = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cores.errorContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: cores.onErrorContainer),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              mensagem,
              style: TextStyle(color: cores.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}

int _contadorChaves = 0;

String _novaChaveIdempotencia() {
  _contadorChaves++;
  return 'app-${DateTime.now().toUtc().microsecondsSinceEpoch}-$_contadorChaves';
}
