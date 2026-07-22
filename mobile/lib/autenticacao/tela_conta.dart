import 'package:flutter/material.dart';

import '../analise/servico_analise.dart';
import '../analise/tela_analise.dart';
import 'modelos_autenticacao.dart';
import 'servico_autenticacao.dart';

class TelaConta extends StatefulWidget {
  const TelaConta({
    super.key,
    required this.servicoAutenticacao,
    required this.servicoAnalise,
    required this.usuario,
  });

  final ServicoAutenticacao servicoAutenticacao;
  final ServicoAnalise servicoAnalise;
  final UsuarioSessao usuario;

  @override
  State<TelaConta> createState() => _TelaContaState();
}

class _TelaContaState extends State<TelaConta> {
  late Future<PerfilUsuario> _perfil;
  bool _saindo = false;

  @override
  void initState() {
    super.initState();
    _perfil = widget.servicoAutenticacao.carregarPerfil(widget.usuario.id);
  }

  void _recarregar() {
    setState(() {
      _perfil = widget.servicoAutenticacao.carregarPerfil(widget.usuario.id);
    });
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mapa de Karnaugh Estendido'),
        actions: [
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
            onNovaAnalise: () => _abrirAnalise(snapshot.data!),
          );
        },
      ),
    );
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
}

class _ConteudoConta extends StatelessWidget {
  const _ConteudoConta({required this.perfil, required this.onNovaAnalise});

  final PerfilUsuario perfil;
  final VoidCallback onNovaAnalise;

  @override
  Widget build(BuildContext context) {
    final cores = Theme.of(context).colorScheme;
    final mensagem = _mensagemEstado(perfil);

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Olá!', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 4),
              Text(perfil.email),
              const SizedBox(height: 24),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
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
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            perfil.podeAnalisar
                                ? Icons.check_circle_outline
                                : Icons.schedule_outlined,
                            color: perfil.podeAnalisar
                                ? cores.primary
                                : cores.tertiary,
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
              ),
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
