import 'package:flutter/material.dart';

import '../administracao/modelos_administracao.dart';
import '../administracao/servico_administracao.dart';
import '../administracao/tela_administracao.dart';
import '../analise/servico_analise.dart';
import '../analise/tela_analise.dart';
import '../metodo/tela_sobre_metodo.dart';
import '../visual/identidade_visual.dart';
import 'modelos_autenticacao.dart';
import 'servico_autenticacao.dart';

class TelaConta extends StatefulWidget {
  const TelaConta({
    super.key,
    required this.servicoAutenticacao,
    required this.servicoAnalise,
    this.servicoAdministracao,
    required this.usuario,
  });

  final ServicoAutenticacao servicoAutenticacao;
  final ServicoAnalise servicoAnalise;
  final ServicoAdministracao? servicoAdministracao;
  final UsuarioSessao usuario;

  @override
  State<TelaConta> createState() => _TelaContaState();
}

class _TelaContaState extends State<TelaConta> {
  late Future<PerfilUsuario> _perfil;
  PerfilUsuario? _perfilAtual;
  TransferenciaMaster? _transferenciaMaster;
  bool _saindo = false;
  bool _aceitandoTransferencia = false;

  @override
  void initState() {
    super.initState();
    _perfil = _buscarPerfil();
  }

  void _recarregar() {
    setState(() {
      _perfilAtual = null;
      _transferenciaMaster = null;
      _perfil = _buscarPerfil();
    });
  }

  Future<PerfilUsuario> _buscarPerfil() async {
    final perfil = await widget.servicoAutenticacao.carregarPerfil(
      widget.usuario.id,
    );
    TransferenciaMaster? transferencia;
    final administracao = widget.servicoAdministracao;
    if (administracao != null) {
      try {
        transferencia = await administracao.obterTransferenciaMaster();
      } on FalhaAdministracao {
        transferencia = null;
      }
    }
    if (mounted) {
      setState(() {
        _perfilAtual = perfil;
        _transferenciaMaster = transferencia;
      });
    }
    return perfil;
  }

  Future<void> _sair() async {
    if (_saindo) return;
    setState(() => _saindo = true);
    try {
      await widget.servicoAutenticacao.sair();
    } on FalhaAutenticacao catch (erro) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(erro.mensagem)));
      setState(() => _saindo = false);
    }
  }

  void _abrirSobreMetodo() {
    Navigator.of(
      context,
    ).push<void>(MaterialPageRoute(builder: (_) => const TelaSobreMetodo()));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mapa de Karnaugh Estendido'),
        actions: [
          IconButton(
            onPressed: _abrirSobreMetodo,
            tooltip: 'Sobre o método',
            icon: const Icon(Icons.menu_book_outlined),
          ),
          if (_podeAdministrar)
            IconButton(
              onPressed: () => _abrirAdministracao(_perfilAtual!),
              tooltip: 'Gerenciar contas',
              icon: const Icon(Icons.manage_accounts_outlined),
            ),
          TextButton.icon(
            onPressed: _saindo ? null : _sair,
            icon: const Icon(Icons.logout),
            label: const Text('Sair'),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: FutureBuilder<PerfilUsuario>(
        future: _perfil,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return _FalhaPerfil(onTentarNovamente: _recarregar);
          }
          return _ConteudoConta(
            perfil: snapshot.data!,
            transferenciaMaster: _transferenciaParaAceitar,
            aceitandoTransferencia: _aceitandoTransferencia,
            onAceitarTransferencia: _aceitarTransferenciaMaster,
            onNovaAnalise: () => _abrirAnalise(snapshot.data!),
          );
        },
      ),
    );
  }

  bool get _podeAdministrar {
    final perfil = _perfilAtual;
    return widget.servicoAdministracao != null &&
        perfil != null &&
        perfil.estado == EstadoConta.ativo &&
        perfil.papel != PapelUsuario.usuario;
  }

  TransferenciaMaster? get _transferenciaParaAceitar {
    final transferencia = _transferenciaMaster;
    if (transferencia == null ||
        !transferencia.pendente ||
        !transferencia.souDestino) {
      return null;
    }
    return transferencia;
  }

  Future<void> _aceitarTransferenciaMaster() async {
    final transferencia = _transferenciaParaAceitar;
    final administracao = widget.servicoAdministracao;
    if (transferencia == null ||
        administracao == null ||
        _aceitandoTransferencia) {
      return;
    }

    final confirmou = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Aceitar controle master?'),
        content: Text(
          'Você passará a possuir o controle superior do aplicativo. '
          '${transferencia.masterAtualEmail} continuará com acesso como '
          'submaster.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Agora não'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Aceitar controle'),
          ),
        ],
      ),
    );
    if (confirmou != true || !mounted) return;

    setState(() => _aceitandoTransferencia = true);
    try {
      await administracao.aceitarTransferenciaMaster(transferencia.id);
      if (!mounted) return;
      _recarregar();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Transferência concluída. Agora você é o master.'),
        ),
      );
    } on FalhaAdministracao catch (erro) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(erro.mensagem)));
    } finally {
      if (mounted) setState(() => _aceitandoTransferencia = false);
    }
  }

  Future<void> _abrirAnalise(PerfilUsuario perfil) async {
    if (!perfil.podeAnalisar) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => TelaAnalise(
          servico: widget.servicoAnalise,
          onAnaliseConcluida: _recarregar,
        ),
      ),
    );
  }

  Future<void> _abrirAdministracao(PerfilUsuario perfil) async {
    final servico = widget.servicoAdministracao;
    if (servico == null ||
        perfil.papel == PapelUsuario.usuario ||
        perfil.estado != EstadoConta.ativo) {
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => TelaAdministracao(
          servico: servico,
          perfilAtual: perfil,
        ),
      ),
    );
    if (!mounted) return;
    _recarregar();
  }
}

class _ConteudoConta extends StatelessWidget {
  const _ConteudoConta({
    required this.perfil,
    required this.transferenciaMaster,
    required this.aceitandoTransferencia,
    required this.onAceitarTransferencia,
    required this.onNovaAnalise,
  });

  final PerfilUsuario perfil;
  final TransferenciaMaster? transferenciaMaster;
  final bool aceitandoTransferencia;
  final VoidCallback onAceitarTransferencia;
  final VoidCallback onNovaAnalise;

  @override
  Widget build(BuildContext context) {
    final mensagem = _mensagemEstado(perfil);

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              CabecalhoInstitucional(
                sobretitulo: 'UFPE · Engenharia Mecânica',
                titulo: 'Olá!',
                descricao: perfil.email,
              ),
              const SizedBox(height: 18),
              if (transferenciaMaster != null) ...[
                CartaoInstitucional(
                  destaque: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.workspace_premium_outlined,
                        size: 38,
                        color: CoresInstitucionais.vinho,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Convite para assumir o controle master',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${transferenciaMaster!.masterAtualEmail} indicou '
                        'você como o próximo responsável pelo aplicativo. '
                        'A troca só acontecerá quando você aceitar.',
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: aceitandoTransferencia
                            ? null
                            : onAceitarTransferencia,
                        icon: aceitandoTransferencia
                            ? const SizedBox.square(
                                dimension: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.check_circle_outline),
                        label: const Text('Aceitar controle master'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
              ],
              CartaoInstitucional(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        Chip(
                          avatar: const Icon(Icons.badge_outlined, size: 18),
                          label: Text(perfil.papel.rotulo),
                        ),
                        Chip(
                          avatar: const Icon(
                            Icons.analytics_outlined,
                            size: 18,
                          ),
                          label: Text(_rotuloAcesso(perfil)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: perfil.podeAnalisar
                            ? CoresInstitucionais.sucessoFundo
                            : CoresInstitucionais.vinhoFundo,
                        border: Border.all(
                          color: perfil.podeAnalisar
                              ? const Color(0xFFCFE8D8)
                              : const Color(0xFFEBD0D7),
                        ),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            perfil.podeAnalisar
                                ? Icons.check_circle_outline
                                : Icons.schedule_outlined,
                            color: perfil.podeAnalisar
                                ? CoresInstitucionais.sucesso
                                : CoresInstitucionais.vinhoClaro,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  perfil.podeAnalisar
                                      ? 'Acesso liberado'
                                      : 'Acesso indisponível',
                                  style: Theme.of(
                                    context,
                                  ).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 4),
                                Text(mensagem),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: perfil.podeAnalisar ? onNovaAnalise : null,
                        icon: const Icon(Icons.account_tree_outlined),
                        label: const Text('Nova análise'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              const RodapeUfpe(),
            ],
          ),
        ),
      ),
    );
  }
}

class _FalhaPerfil extends StatelessWidget {
  const _FalhaPerfil({required this.onTentarNovamente});

  final VoidCallback onTentarNovamente;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 48),
            const SizedBox(height: 12),
            const Text('Não foi possível carregar sua conta.'),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: onTentarNovamente,
              child: const Text('Tentar novamente'),
            ),
          ],
        ),
      ),
    );
  }
}

String _rotuloAcesso(PerfilUsuario perfil) {
  if (perfil.acesso == TipoAcesso.ilimitado) return 'Análises ilimitadas';
  return '${perfil.analisesRestantes ?? 0} análise(s) disponível(is)';
}

String _mensagemEstado(PerfilUsuario perfil) => switch (perfil.estado) {
  EstadoConta.ativo when perfil.podeAnalisar =>
    'Sua conta pode realizar análises.',
  EstadoConta.ativo => 'Solicite mais análises ao professor.',
  EstadoConta.convidado => 'Confirme seu e-mail para concluir o convite.',
  EstadoConta.aguardandoAprovacao =>
    'Seu cadastro está aguardando aprovação do professor.',
  EstadoConta.suspenso => 'Sua conta está suspensa. Procure o professor.',
  EstadoConta.revogado => 'O acesso desta conta foi revogado.',
};
