import 'dart:async';

import 'package:flutter/material.dart';

import '../administracao/servico_administracao.dart';
import '../analise/servico_analise.dart';
import 'modelos_autenticacao.dart';
import 'servico_autenticacao.dart';
import 'tela_conta.dart';
import 'tela_definir_senha.dart';
import 'tela_login.dart';

class PortaoAutenticacao extends StatefulWidget {
  const PortaoAutenticacao({
    super.key,
    required this.servicoAutenticacao,
    required this.servicoAnalise,
    this.servicoAdministracao,
  });

  final ServicoAutenticacao servicoAutenticacao;
  final ServicoAnalise servicoAnalise;
  final ServicoAdministracao? servicoAdministracao;

  @override
  State<PortaoAutenticacao> createState() => _PortaoAutenticacaoState();
}

class _PortaoAutenticacaoState extends State<PortaoAutenticacao> {
  StreamSubscription<UsuarioSessao?>? _assinatura;
  StreamSubscription<MotivoDefinicaoSenha>? _assinaturaSenha;
  UsuarioSessao? _usuario;
  MotivoDefinicaoSenha? _motivoSenha;
  String? _avisoSessao;

  @override
  void initState() {
    super.initState();
    _usuario = widget.servicoAutenticacao.usuarioAtual;
    _motivoSenha = widget.servicoAutenticacao.definicaoSenhaPendente;
    _assinatura = widget.servicoAutenticacao.mudancasSessao.listen(
      (usuario) {
        if (!mounted) return;
        setState(() {
          _usuario = usuario;
          if (usuario == null) _motivoSenha = null;
          _avisoSessao = null;
        });
      },
      onError: (_, _) {
        if (!mounted) return;
        setState(() {
          _avisoSessao = 'A conexão com o login foi interrompida.';
        });
      },
    );
    _assinaturaSenha = widget
        .servicoAutenticacao
        .solicitacoesDefinicaoSenha
        .listen(
          (motivo) {
            if (!mounted) return;
            setState(() => _motivoSenha = motivo);
          },
          onError: (_, _) {
            if (!mounted) return;
            setState(() {
              _avisoSessao =
                  'Não foi possível abrir a definição de senha.';
            });
          },
        );
  }

  @override
  void dispose() {
    _assinatura?.cancel();
    _assinaturaSenha?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final usuario = _usuario;
    if (usuario == null) {
      return TelaLogin(
        servico: widget.servicoAutenticacao,
        avisoSessao: _avisoSessao,
      );
    }
    final motivoSenha = _motivoSenha;
    if (motivoSenha != null) {
      return TelaDefinirSenha(
        servico: widget.servicoAutenticacao,
        motivo: motivoSenha,
        aoConcluir: () {
          if (mounted) setState(() => _motivoSenha = null);
        },
      );
    }
    return TelaConta(
      key: ValueKey(usuario.id),
      servicoAutenticacao: widget.servicoAutenticacao,
      servicoAnalise: widget.servicoAnalise,
      servicoAdministracao: widget.servicoAdministracao,
      usuario: usuario,
    );
  }
}
