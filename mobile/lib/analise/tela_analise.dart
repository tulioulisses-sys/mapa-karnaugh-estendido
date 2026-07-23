import 'package:flutter/material.dart';

import '../metodo/tela_sobre_metodo.dart';
import '../visual/identidade_visual.dart';
import 'modelos_analise.dart';
import 'resultado_analise.dart';
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

  void _usarExemplo(String sequencia) {
    _sequencia.text = sequencia;
  }

  void _abrirSobreMetodo() {
    Navigator.of(
      context,
    ).push<void>(MaterialPageRoute(builder: (_) => const TelaSobreMetodo()));
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
      appBar: AppBar(
        title: const Text('Resolver'),
        actions: [
          IconButton(
            onPressed: _abrirSobreMetodo,
            tooltip: 'Sobre o método',
            icon: const Icon(Icons.menu_book_outlined),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1180),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const CabecalhoInstitucional(
                      sobretitulo: 'UFPE · Engenharia Mecânica',
                      titulo:
                          'Resolução das Equações de Comando de Circuitos '
                          'Fluido Mecânicos Utilizando o Método do Mapa de '
                          'Karnaugh Estendido',
                      descricao:
                          'Informe a sequência de movimentos para determinar as '
                          'memórias, equações de comando e o mapa estendido.',
                    ),
                    const SizedBox(height: 18),
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
                      ResultadoAnaliseView(resultado: _resultado!),
                    ],
                    const SizedBox(height: 28),
                    const RodapeUfpe(),
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
  final ValueChanged<String> onUsarExemplo;
  final VoidCallback onResolver;

  @override
  Widget build(BuildContext context) {
    return CartaoInstitucional(
      child: Form(
        key: formulario,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const CabecalhoEtapa(
              numero: 1,
              titulo: 'Informe a sequência de movimentos',
              descricao:
                  'Escreva os movimentos na ordem de execução. Movimentos '
                  'simultâneos podem ser informados entre parênteses.',
            ),
            const SizedBox(height: 12),
            ExpansionTile(
              initiallyExpanded: true,
              tilePadding: EdgeInsets.zero,
              childrenPadding: const EdgeInsets.only(bottom: 10),
              title: const Text('Como escrever a sequência?'),
              subtitle: const Text(
                'O sistema identifica atuadores, sensores, movimentos '
                'simultâneos, multiposição e loops.',
              ),
              children: [
                const _ExemploEntrada(
                  titulo: 'Sequência simples',
                  exemplo: 'A+, B+, B-, A-',
                ),
                const _ExemploEntrada(
                  titulo: 'Movimentos simultâneos',
                  exemplo: 'A+, B+, (C-, D+), (D-, A-)',
                ),
                const _ExemploEntrada(
                  titulo: 'Atuador com várias posições',
                  exemplo:
                      'A+, B+ até b1, C+, B+ até b2, C-, B+ até b3, '
                      'A-, B- até b0',
                ),
                const _ExemploEntrada(
                  titulo: 'Loop condicional',
                  exemplo:
                      'A+, B+, [C+, D+, C-, D-] enquanto e=0, A-, B-',
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    TextButton.icon(
                      onPressed: processando
                          ? null
                          : () => onUsarExemplo('A+, B+, B-, A-'),
                      icon: const Icon(Icons.auto_fix_high_outlined),
                      label: const Text('Usar exemplo A+, B+, B-, A-'),
                    ),
                    TextButton.icon(
                      onPressed: processando
                          ? null
                          : () => onUsarExemplo(
                              'A+, B+ até b1, C+, B+ até b2, C-, '
                              'B+ até b3, A-, B- até b0',
                            ),
                      icon: const Icon(Icons.linear_scale),
                      label: const Text('Usar exemplo multiposição'),
                    ),
                    TextButton.icon(
                      onPressed: processando
                          ? null
                          : () => onUsarExemplo(
                              'A+, B+, [C+, D+, C-, D-] enquanto e=0, '
                              'A-, B-',
                            ),
                      icon: const Icon(Icons.loop),
                      label: const Text('Usar exemplo com loop'),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: CoresInstitucionais.vinhoFundo,
                    border: Border.all(color: const Color(0xFFEBD0D7)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Text(
                    'Para entender os símbolos das equações e consultar os '
                    'materiais completos, use o ícone “Sobre o método” no '
                    'topo da tela.',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 22),
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
    );
  }
}

class _ExemploEntrada extends StatelessWidget {
  const _ExemploEntrada({required this.titulo, required this.exemplo});

  final String titulo;
  final String exemplo;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(titulo, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 5),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
            decoration: BoxDecoration(
              color: CoresInstitucionais.vinhoFundo,
              border: Border.all(color: const Color(0xFFEBD0D7)),
              borderRadius: BorderRadius.circular(9),
            ),
            child: SelectableText(
              exemplo,
              style: const TextStyle(
                color: CoresInstitucionais.vinhoEscuro,
                fontFamily: 'monospace',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AvisoErro extends StatelessWidget {
  const _AvisoErro({required this.mensagem});

  final String mensagem;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFBECEF),
        border: Border.all(color: const Color(0xFFF0C8D0)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: CoresInstitucionais.erro),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              mensagem,
              style: const TextStyle(color: CoresInstitucionais.erro),
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
