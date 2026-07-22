import 'dart:async';

import 'package:flutter/material.dart';

import 'modelos_autenticacao.dart';
import 'servico_autenticacao.dart';
import 'tela_conta.dart';
import 'tela_login.dart';

class PortaoAutenticacao extends StatefulWidget {
  const PortaoAutenticacao({super.key, required this.servico});

  final ServicoAutenticacao servico;

  @override
  State<PortaoAutenticacao> createState() => _PortaoAutenticacaoState();
}

class _PortaoAutenticacaoState extends State<PortaoAutenticacao> {
  StreamSubscription<UsuarioSessao?>? _assinatura;
  UsuarioSessao? _usuario;
  String? _avisoSessao;

  @override
  void initState() {
    super.initState();
    _usuario = widget.servico.usuarioAtual;
    _assinatura = widget.servico.mudancasSessao.listen(
      (usuario) {
        if (!mounted) return;
        setState(() {
          _usuario = usuario;
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
  }

  @override
  void dispose() {
    _assinatura?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final usuario = _usuario;
    if (usuario == null) {
      return TelaLogin(servico: widget.servico, avisoSessao: _avisoSessao);
    }
    return TelaConta(
      key: ValueKey(usuario.id),
      servico: widget.servico,
      usuario: usuario,
    );
  }
}
