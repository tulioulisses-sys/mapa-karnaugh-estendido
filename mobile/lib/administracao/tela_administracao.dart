import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../autenticacao/modelos_autenticacao.dart';
import '../visual/identidade_visual.dart';
import 'modelos_administracao.dart';
import 'servico_administracao.dart';

class TelaAdministracao extends StatefulWidget {
  const TelaAdministracao({
    super.key,
    required this.servico,
    required this.perfilAtual,
  });

  final ServicoAdministracao servico;
  final PerfilUsuario perfilAtual;

  @override
  State<TelaAdministracao> createState() => _TelaAdministracaoState();
}

class _TelaAdministracaoState extends State<TelaAdministracao> {
  List<UsuarioAdministrado> _usuarios = const [];
  List<TurmaAdministrada> _turmas = const [];
  List<ConviteAdministrado> _convites = const [];
  bool _carregando = true;
  bool _processando = false;
  String? _erro;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });
    try {
      final usuarios = await widget.servico.listarUsuarios();
      final turmas = await widget.servico.listarTurmas();
      final convites = await widget.servico.listarConvites();
      if (!mounted) return;
      setState(() {
        _usuarios = usuarios;
        _turmas = turmas;
        _convites = convites;
        _carregando = false;
      });
    } on FalhaAdministracao catch (erro) {
      if (!mounted) return;
      setState(() {
        _erro = erro.mensagem;
        _carregando = false;
      });
    }
  }

  Future<void> _executar(
    Future<void> Function() operacao,
    String mensagem,
  ) async {
    if (_processando) return;
    setState(() => _processando = true);
    try {
      await operacao();
      await _carregar();
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(mensagem)));
    } on FalhaAdministracao catch (erro) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(erro.mensagem)));
    } finally {
      if (mounted) setState(() => _processando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Gestão de acessos'),
        actions: [
          IconButton(
            onPressed: _processando ? null : _carregar,
            tooltip: 'Atualizar usuários',
            icon: const Icon(Icons.refresh),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: _carregando
          ? const Center(child: CircularProgressIndicator())
          : _erro != null
          ? _FalhaCarregamento(mensagem: _erro!, onTentar: _carregar)
          : _conteudo(),
    );
  }

  Widget _conteudo() {
    final pendentes = _usuarios.where((usuario) => usuario.aguardando).length;
    final alunos = _usuarios
        .where(
          (usuario) =>
              usuario.papel == PapelUsuario.usuario &&
              usuario.estado != EstadoConta.revogado,
        )
        .length;
    final submasters = _usuarios
        .where((usuario) => usuario.papel == PapelUsuario.submaster)
        .length;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              CabecalhoInstitucional(
                sobretitulo: 'Painel administrativo',
                titulo: 'Usuários e permissões',
                descricao: widget.perfilAtual.papel == PapelUsuario.master
                    ? 'Você possui o controle master. Aprove cadastros, '
                          'distribua análises e escolha submasters.'
                    : 'Como submaster, você pode administrar as contas '
                          'dos alunos.',
              ),
              const SizedBox(height: 18),
              _painelConvitesTurmas(),
              const SizedBox(height: 18),
              _ResumoAdministracao(
                total: _usuarios.length,
                alunos: alunos,
                pendentes: pendentes,
                submasters: submasters,
              ),
              const SizedBox(height: 18),
              _painelLote(alunos),
              const SizedBox(height: 18),
              Text(
                'Contas cadastradas',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 10),
              if (_usuarios.isEmpty)
                const CartaoInstitucional(
                  child: Text('Nenhuma conta cadastrada.'),
                )
              else
                ..._usuarios.map(
                  (usuario) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _cartaoUsuario(usuario),
                  ),
                ),
              const SizedBox(height: 12),
              const RodapeUfpe(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _painelLote(int quantidadeAlunos) {
    return CartaoInstitucional(
      destaque: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Cotas em lote',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 6),
          Text(
            'A operação alcança todas as contas de alunos não removidas '
            '($quantidadeAlunos cadastrada(s)).',
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.tonalIcon(
                onPressed: _processando || quantidadeAlunos == 0
                    ? null
                    : () => _ajustarLote(adicionar: false),
                icon: const Icon(Icons.tune),
                label: const Text('Definir para todos'),
              ),
              OutlinedButton.icon(
                onPressed: _processando || quantidadeAlunos == 0
                    ? null
                    : () => _ajustarLote(adicionar: true),
                icon: const Icon(Icons.exposure_plus_1),
                label: const Text('Adicionar para todos'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _painelConvitesTurmas() {
    final turmasAtivas = _turmas.where((turma) => turma.ativa).toList();
    final convitesVisiveis = _convites.take(8).toList();

    return CartaoInstitucional(
      destaque: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Turmas e convites',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 6),
          const Text(
            'Convide vários alunos de uma vez e já defina a turma, '
            'o perfil e a quantidade inicial de análises.',
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.icon(
                onPressed: _processando ? null : _abrirConviteEmLote,
                icon: const Icon(Icons.forward_to_inbox_outlined),
                label: const Text('Convidar por e-mail'),
              ),
              OutlinedButton.icon(
                onPressed: _processando ? null : _abrirNovaTurma,
                icon: const Icon(Icons.group_add_outlined),
                label: const Text('Criar turma'),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            'Turmas ativas',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          if (turmasAtivas.isEmpty)
            const Text(
              'Nenhuma turma criada. Crie uma turma antes de convidar '
              'os alunos deste período.',
              style: TextStyle(color: CoresInstitucionais.textoSuave),
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: turmasAtivas
                  .map<Widget>(
                    (turma) => Tooltip(
                      message: turma.nome,
                      child: Chip(
                        avatar: const Icon(Icons.groups_outlined, size: 18),
                        label: Text(
                          '${turma.codigo} · '
                          '${turma.quantidadeAlunos} aluno(s)',
                        ),
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          const Divider(height: 30),
          Text(
            'Convites recentes',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          if (convitesVisiveis.isEmpty)
            const Text(
              'Nenhum convite enviado.',
              style: TextStyle(color: CoresInstitucionais.textoSuave),
            )
          else
            ...convitesVisiveis.map(_linhaConvite),
        ],
      ),
    );
  }

  Widget _linhaConvite(ConviteAdministrado convite) {
    final cota = convite.acessoDestino == TipoAcesso.ilimitado
        ? 'Ilimitado'
        : '${convite.analisesIniciais ?? 0} análise(s)';

    return Padding(
      padding: const EdgeInsets.only(bottom: 9),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: CoresInstitucionais.creme,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: CoresInstitucionais.borda),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
          child: Row(
            children: [
              const Icon(
                Icons.mail_outline,
                color: CoresInstitucionais.vinho,
              ),
              const SizedBox(width: 11),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      convite.email,
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 3),
                    Text(
                      [
                        _rotuloEstadoConvite(convite.estado),
                        convite.turmaCodigo,
                        convite.papelDestino.rotulo,
                        cota,
                      ].whereType<String>().join(' · '),
                      style: const TextStyle(
                        color: CoresInstitucionais.textoSuave,
                      ),
                    ),
                  ],
                ),
              ),
              if (convite.pendente)
                IconButton(
                  onPressed: _processando
                      ? null
                      : () => _cancelarConvite(convite),
                  tooltip: 'Cancelar convite',
                  icon: const Icon(Icons.close),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _cartaoUsuario(UsuarioAdministrado usuario) {
    final podeGerenciar = _podeGerenciar(usuario);

    return CartaoInstitucional(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                backgroundColor: CoresInstitucionais.vinhoFundo,
                foregroundColor: CoresInstitucionais.vinho,
                child: Icon(_iconePapel(usuario.papel)),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      usuario.email,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 7,
                      runSpacing: 7,
                      children: [
                        Chip(label: Text(usuario.papel.rotulo)),
                        _ChipEstado(usuario.estado),
                        Chip(label: Text(_rotuloAcesso(usuario))),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (podeGerenciar) ...[
            const Divider(height: 28),
            Wrap(
              spacing: 9,
              runSpacing: 9,
              children: [
                if (usuario.aguardando)
                  FilledButton.icon(
                    onPressed: _processando
                        ? null
                        : () => _mudarEstado(
                            usuario,
                            EstadoConta.ativo,
                            'Usuário aprovado.',
                          ),
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('Aprovar'),
                  ),
                if (usuario.estado == EstadoConta.ativo)
                  OutlinedButton.icon(
                    onPressed: _processando
                        ? null
                        : () => _mudarEstado(
                            usuario,
                            EstadoConta.suspenso,
                            'Usuário suspenso.',
                          ),
                    icon: const Icon(Icons.pause_circle_outline),
                    label: const Text('Suspender'),
                  ),
                if (usuario.estado == EstadoConta.suspenso)
                  FilledButton.tonalIcon(
                    onPressed: _processando
                        ? null
                        : () => _mudarEstado(
                            usuario,
                            EstadoConta.ativo,
                            'Usuário reativado.',
                          ),
                    icon: const Icon(Icons.play_circle_outline),
                    label: const Text('Reativar'),
                  ),
                if (usuario.papel == PapelUsuario.usuario &&
                    usuario.estado != EstadoConta.revogado)
                  OutlinedButton.icon(
                    onPressed: _processando
                        ? null
                        : () => _abrirAcesso(usuario),
                    icon: const Icon(Icons.analytics_outlined),
                    label: const Text('Ajustar análises'),
                  ),
                if (widget.perfilAtual.papel == PapelUsuario.master &&
                    usuario.papel != PapelUsuario.master &&
                    usuario.estado != EstadoConta.revogado)
                  OutlinedButton.icon(
                    onPressed: _processando
                        ? null
                        : () => _alternarSubmaster(usuario),
                    icon: Icon(
                      usuario.papel == PapelUsuario.submaster
                          ? Icons.person_remove_outlined
                          : Icons.admin_panel_settings_outlined,
                    ),
                    label: Text(
                      usuario.papel == PapelUsuario.submaster
                          ? 'Remover submaster'
                          : 'Tornar submaster',
                    ),
                  ),
                if (usuario.estado != EstadoConta.revogado)
                  TextButton.icon(
                    onPressed: _processando
                        ? null
                        : () => _revogar(usuario),
                    icon: const Icon(Icons.block),
                    label: const Text('Remover acesso'),
                  ),
              ],
            ),
          ] else if (usuario.id == widget.perfilAtual.id) ...[
            const SizedBox(height: 12),
            const Text(
              'Esta é a sua própria conta. Ela não pode ser alterada '
              'por este painel.',
              style: TextStyle(color: CoresInstitucionais.textoSuave),
            ),
          ],
        ],
      ),
    );
  }

  bool _podeGerenciar(UsuarioAdministrado usuario) {
    if (usuario.id == widget.perfilAtual.id) return false;
    if (widget.perfilAtual.papel == PapelUsuario.master) {
      return usuario.papel != PapelUsuario.master;
    }
    return widget.perfilAtual.papel == PapelUsuario.submaster &&
        usuario.papel == PapelUsuario.usuario;
  }

  Future<void> _mudarEstado(
    UsuarioAdministrado usuario,
    EstadoConta estado,
    String mensagem,
  ) {
    return _executar(
      () => widget.servico.alterarEstado(usuario.id, estado),
      mensagem,
    );
  }

  Future<void> _revogar(UsuarioAdministrado usuario) async {
    final confirmou = await _confirmar(
      titulo: 'Remover acesso?',
      mensagem:
          '${usuario.email} deixará de entrar e realizar análises. '
          'O histórico será preservado para auditoria.',
      rotuloConfirmacao: 'Remover acesso',
    );
    if (confirmou != true) return;
    if (!mounted) return;
    await _mudarEstado(
      usuario,
      EstadoConta.revogado,
      'Acesso removido.',
    );
  }

  Future<void> _alternarSubmaster(UsuarioAdministrado usuario) async {
    final promover = usuario.papel != PapelUsuario.submaster;
    final confirmou = await _confirmar(
      titulo: promover ? 'Tornar submaster?' : 'Remover submaster?',
      mensagem: promover
          ? '${usuario.email} poderá administrar alunos e cotas, mas não '
                'poderá alterar o master nem outros submasters.'
          : '${usuario.email} voltará a ser aluno com zero análises.',
      rotuloConfirmacao: promover ? 'Tornar submaster' : 'Remover submaster',
    );
    if (confirmou != true) return;
    if (!mounted) return;
    await _executar(
      () => widget.servico.alterarPapel(
        usuario.id,
        promover ? PapelUsuario.submaster : PapelUsuario.usuario,
      ),
      promover ? 'Submaster definido.' : 'Submaster removido.',
    );
  }

  Future<void> _abrirAcesso(UsuarioAdministrado usuario) async {
    var acesso = usuario.acesso;
    final controlador = TextEditingController(
      text: (usuario.analisesRestantes ?? 1).toString(),
    );

    final resultado = await showDialog<(TipoAcesso, int?)>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, atualizar) => AlertDialog(
          title: const Text('Ajustar análises'),
          content: SizedBox(
            width: 430,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(usuario.email),
                const SizedBox(height: 18),
                SegmentedButton<TipoAcesso>(
                  segments: const [
                    ButtonSegment(
                      value: TipoAcesso.limitado,
                      label: Text('Limitado'),
                      icon: Icon(Icons.pin_outlined),
                    ),
                    ButtonSegment(
                      value: TipoAcesso.ilimitado,
                      label: Text('Ilimitado'),
                      icon: Icon(Icons.all_inclusive),
                    ),
                  ],
                  selected: {acesso},
                  onSelectionChanged: (selecionados) {
                    atualizar(() => acesso = selecionados.first);
                  },
                ),
                if (acesso == TipoAcesso.limitado) ...[
                  const SizedBox(height: 18),
                  TextField(
                    controller: controlador,
                    keyboardType: TextInputType.number,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    decoration: const InputDecoration(
                      labelText: 'Análises disponíveis',
                    ),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () {
                final quantidade = acesso == TipoAcesso.limitado
                    ? int.tryParse(controlador.text)
                    : null;
                if (acesso == TipoAcesso.limitado && quantidade == null) {
                  return;
                }
                Navigator.pop(context, (acesso, quantidade));
              },
              child: const Text('Salvar'),
            ),
          ],
        ),
      ),
    );
    controlador.dispose();
    if (resultado == null) return;
    if (!mounted) return;

    await _executar(
      () => widget.servico.definirAcesso(
        usuario.id,
        resultado.$1,
        resultado.$2,
      ),
      'Acesso atualizado.',
    );
  }

  Future<void> _ajustarLote({required bool adicionar}) async {
    final controlador = TextEditingController(text: '1');
    final quantidade = await showDialog<int>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          adicionar
              ? 'Adicionar análises para todos'
              : 'Definir análises para todos',
        ),
        content: SizedBox(
          width: 420,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                adicionar
                    ? 'A quantidade será somada ao saldo atual de cada aluno.'
                    : 'O saldo atual de cada aluno será substituído.',
              ),
              const SizedBox(height: 16),
              TextField(
                controller: controlador,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(labelText: 'Quantidade'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () {
              final valor = int.tryParse(controlador.text);
              if (valor == null || (adicionar && valor < 1)) return;
              Navigator.pop(context, valor);
            },
            child: const Text('Confirmar'),
          ),
        ],
      ),
    );
    controlador.dispose();
    if (quantidade == null) return;
    if (!mounted) return;

    await _executar(() async {
      await widget.servico.ajustarCotasEmLote(
        adicionar: adicionar,
        quantidade: quantidade,
      );
    }, 'Cotas em lote atualizadas.');
  }

  Future<void> _abrirNovaTurma() async {
    final codigo = TextEditingController();
    final nome = TextEditingController(text: 'Circuitos Fluido Mecânicos');
    String? erro;

    final dados = await showDialog<(String, String)>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, atualizar) => AlertDialog(
          title: const Text('Criar turma'),
          content: SizedBox(
            width: 460,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: codigo,
                  autofocus: true,
                  decoration: const InputDecoration(
                    labelText: 'Código ou período',
                    hintText: 'Ex.: 2026.1',
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: nome,
                  decoration: const InputDecoration(
                    labelText: 'Nome da turma',
                  ),
                ),
                if (erro != null) ...[
                  const SizedBox(height: 10),
                  Text(
                    erro!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () {
                final codigoInformado = codigo.text.trim();
                final nomeInformado = nome.text.trim();
                if (codigoInformado.isEmpty || nomeInformado.isEmpty) {
                  atualizar(() => erro = 'Preencha o código e o nome.');
                  return;
                }
                Navigator.pop(context, (codigoInformado, nomeInformado));
              },
              child: const Text('Criar turma'),
            ),
          ],
        ),
      ),
    );
    codigo.dispose();
    nome.dispose();
    if (dados == null || !mounted) return;

    await _executar(
      () async {
        await widget.servico.criarTurma(codigo: dados.$1, nome: dados.$2);
      },
      'Turma criada.',
    );
  }

  Future<void> _abrirConviteEmLote() async {
    final emails = TextEditingController();
    final quantidade = TextEditingController(text: '1');
    var papel = PapelUsuario.usuario;
    var acesso = TipoAcesso.limitado;
    final turmasAtivas = _turmas.where((turma) => turma.ativa).toList();
    var turmaId = turmasAtivas.isEmpty ? '' : turmasAtivas.first.id;
    String? erro;

    final dados = await showDialog<_DadosConvite>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, atualizar) => AlertDialog(
          title: const Text('Convidar por e-mail'),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Cole os e-mails separados por espaço, vírgula, '
                    'ponto e vírgula ou quebra de linha.',
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: emails,
                    autofocus: true,
                    minLines: 5,
                    maxLines: 10,
                    decoration: const InputDecoration(
                      labelText: 'E-mails',
                      hintText: 'aluno1@ufpe.br\naluno2@ufpe.br',
                      alignLabelWithHint: true,
                    ),
                  ),
                  const SizedBox(height: 14),
                  DropdownButtonFormField<String>(
                    initialValue: turmaId,
                    decoration: const InputDecoration(
                      labelText: 'Turma',
                    ),
                    items: [
                      const DropdownMenuItem(
                        value: '',
                        child: Text('Sem turma'),
                      ),
                      ..._turmas.where((turma) => turma.ativa).map(
                        (turma) => DropdownMenuItem(
                          value: turma.id,
                          child: Text('${turma.codigo} · ${turma.nome}'),
                        ),
                      ),
                    ],
                    onChanged: (valor) {
                      atualizar(() => turmaId = valor ?? '');
                    },
                  ),
                  if (widget.perfilAtual.papel == PapelUsuario.master) ...[
                    const SizedBox(height: 14),
                    DropdownButtonFormField<PapelUsuario>(
                      initialValue: papel,
                      decoration: const InputDecoration(
                        labelText: 'Perfil',
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: PapelUsuario.usuario,
                          child: Text('Aluno'),
                        ),
                        DropdownMenuItem(
                          value: PapelUsuario.submaster,
                          child: Text('Submaster'),
                        ),
                      ],
                      onChanged: (valor) {
                        if (valor == null) return;
                        atualizar(() {
                          papel = valor;
                          if (papel == PapelUsuario.submaster) {
                            acesso = TipoAcesso.ilimitado;
                          }
                        });
                      },
                    ),
                  ],
                  if (papel == PapelUsuario.usuario) ...[
                    const SizedBox(height: 14),
                    SegmentedButton<TipoAcesso>(
                      segments: const [
                        ButtonSegment(
                          value: TipoAcesso.limitado,
                          label: Text('Limitado'),
                          icon: Icon(Icons.pin_outlined),
                        ),
                        ButtonSegment(
                          value: TipoAcesso.ilimitado,
                          label: Text('Ilimitado'),
                          icon: Icon(Icons.all_inclusive),
                        ),
                      ],
                      selected: {acesso},
                      onSelectionChanged: (selecionados) {
                        atualizar(() => acesso = selecionados.first);
                      },
                    ),
                    if (acesso == TipoAcesso.limitado) ...[
                      const SizedBox(height: 14),
                      TextField(
                        controller: quantidade,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                        ],
                        decoration: const InputDecoration(
                          labelText: 'Análises iniciais por aluno',
                        ),
                      ),
                    ],
                  ],
                  if (erro != null) ...[
                    const SizedBox(height: 10),
                    Text(
                      erro!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancelar'),
            ),
            FilledButton.icon(
              onPressed: () {
                final lista = emails.text
                    .split(RegExp(r'[\s,;]+'))
                    .map((email) => email.trim().toLowerCase())
                    .where((email) => email.isNotEmpty)
                    .toSet()
                    .toList(growable: false);
                final saldo =
                    papel == PapelUsuario.usuario &&
                        acesso == TipoAcesso.limitado
                    ? int.tryParse(quantidade.text)
                    : null;
                if (lista.isEmpty) {
                  atualizar(() => erro = 'Informe pelo menos um e-mail.');
                  return;
                }
                if (lista.length > 300) {
                  atualizar(
                    () => erro = 'Envie no máximo 300 convites por vez.',
                  );
                  return;
                }
                if (papel == PapelUsuario.usuario &&
                    acesso == TipoAcesso.limitado &&
                    saldo == null) {
                  atualizar(() => erro = 'Informe a quantidade inicial.');
                  return;
                }
                Navigator.pop(
                  context,
                  _DadosConvite(
                    emails: lista,
                    papel: papel,
                    acesso: papel == PapelUsuario.submaster
                        ? TipoAcesso.ilimitado
                        : acesso,
                    analisesIniciais: saldo,
                    turmaId: turmaId.isEmpty ? null : turmaId,
                  ),
                );
              },
              icon: const Icon(Icons.send_outlined),
              label: const Text('Enviar convites'),
            ),
          ],
        ),
      ),
    );
    emails.dispose();
    quantidade.dispose();
    if (dados == null || !mounted) return;

    await _enviarConvites(dados);
  }

  Future<void> _enviarConvites(_DadosConvite dados) async {
    if (_processando) return;
    setState(() => _processando = true);
    try {
      final resultado = await widget.servico.convidarEmLote(
        emails: dados.emails,
        papelDestino: dados.papel,
        acessoDestino: dados.acesso,
        analisesIniciais: dados.analisesIniciais,
        turmaId: dados.turmaId,
      );
      await _carregar();
      if (!mounted) return;
      final mensagem = resultado.emailsComFalha == 0
          ? '${resultado.emailsEnviados} convite(s) enviado(s).'
          : '${resultado.emailsEnviados} enviado(s) e '
                '${resultado.emailsComFalha} com falha de e-mail.';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(mensagem)));
    } on FalhaAdministracao catch (erro) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(erro.mensagem)));
    } finally {
      if (mounted) setState(() => _processando = false);
    }
  }

  Future<void> _cancelarConvite(ConviteAdministrado convite) async {
    final confirmou = await _confirmar(
      titulo: 'Cancelar convite?',
      mensagem: '${convite.email} não poderá mais aceitar este convite.',
      rotuloConfirmacao: 'Cancelar convite',
    );
    if (confirmou != true || !mounted) return;
    await _executar(
      () => widget.servico.cancelarConvite(convite.id),
      'Convite cancelado.',
    );
  }

  Future<bool?> _confirmar({
    required String titulo,
    required String mensagem,
    required String rotuloConfirmacao,
  }) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(titulo),
        content: Text(mensagem),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(rotuloConfirmacao),
          ),
        ],
      ),
    );
  }
}

class _DadosConvite {
  const _DadosConvite({
    required this.emails,
    required this.papel,
    required this.acesso,
    required this.analisesIniciais,
    required this.turmaId,
  });

  final List<String> emails;
  final PapelUsuario papel;
  final TipoAcesso acesso;
  final int? analisesIniciais;
  final String? turmaId;
}

class _ResumoAdministracao extends StatelessWidget {
  const _ResumoAdministracao({
    required this.total,
    required this.alunos,
    required this.pendentes,
    required this.submasters,
  });

  final int total;
  final int alunos;
  final int pendentes;
  final int submasters;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final largura = constraints.maxWidth < 760
            ? constraints.maxWidth
            : (constraints.maxWidth - 36) / 4;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _Indicador(
              largura: largura,
              valor: total,
              rotulo: 'Contas',
              icone: Icons.people_outline,
            ),
            _Indicador(
              largura: largura,
              valor: alunos,
              rotulo: 'Alunos',
              icone: Icons.school_outlined,
            ),
            _Indicador(
              largura: largura,
              valor: pendentes,
              rotulo: 'Pendentes',
              icone: Icons.schedule_outlined,
            ),
            _Indicador(
              largura: largura,
              valor: submasters,
              rotulo: 'Submasters',
              icone: Icons.admin_panel_settings_outlined,
            ),
          ],
        );
      },
    );
  }
}

class _Indicador extends StatelessWidget {
  const _Indicador({
    required this.largura,
    required this.valor,
    required this.rotulo,
    required this.icone,
  });

  final double largura;
  final int valor;
  final String rotulo;
  final IconData icone;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: largura,
      child: CartaoInstitucional(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            Icon(icone, color: CoresInstitucionais.vinho),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    valor.toString(),
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  Text(
                    rotulo,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
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

class _ChipEstado extends StatelessWidget {
  const _ChipEstado(this.estado);

  final EstadoConta estado;

  @override
  Widget build(BuildContext context) {
    final ativo = estado == EstadoConta.ativo;
    return Chip(
      avatar: Icon(
        ativo ? Icons.check_circle_outline : Icons.info_outline,
        size: 17,
      ),
      label: Text(_rotuloEstado(estado)),
      backgroundColor: ativo
          ? CoresInstitucionais.sucessoFundo
          : CoresInstitucionais.vinhoFundo,
    );
  }
}

class _FalhaCarregamento extends StatelessWidget {
  const _FalhaCarregamento({
    required this.mensagem,
    required this.onTentar,
  });

  final String mensagem;
  final VoidCallback onTentar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: CartaoInstitucional(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_outlined, size: 45),
              const SizedBox(height: 12),
              Text(mensagem, textAlign: TextAlign.center),
              const SizedBox(height: 14),
              OutlinedButton(
                onPressed: onTentar,
                child: const Text('Tentar novamente'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

IconData _iconePapel(PapelUsuario papel) => switch (papel) {
  PapelUsuario.master => Icons.workspace_premium_outlined,
  PapelUsuario.submaster => Icons.admin_panel_settings_outlined,
  PapelUsuario.usuario => Icons.school_outlined,
};

String _rotuloEstado(EstadoConta estado) => switch (estado) {
  EstadoConta.convidado => 'Convidado',
  EstadoConta.aguardandoAprovacao => 'Aguardando aprovação',
  EstadoConta.ativo => 'Ativo',
  EstadoConta.suspenso => 'Suspenso',
  EstadoConta.revogado => 'Acesso removido',
};

String _rotuloEstadoConvite(String estado) => switch (estado) {
  'pendente' => 'Pendente',
  'aceito' => 'Aceito',
  'expirado' => 'Expirado',
  'cancelado' => 'Cancelado',
  _ => estado,
};

String _rotuloAcesso(UsuarioAdministrado usuario) {
  if (usuario.acesso == TipoAcesso.ilimitado) return 'Ilimitado';
  return '${usuario.analisesRestantes ?? 0} análise(s)';
}
