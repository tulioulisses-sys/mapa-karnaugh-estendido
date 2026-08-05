import 'package:flutter/material.dart';

import '../visual/identidade_visual.dart';
import 'modelos_autenticacao.dart';
import 'servico_autenticacao.dart';

class TelaDefinirSenha extends StatefulWidget {
  const TelaDefinirSenha({
    super.key,
    required this.servico,
    required this.motivo,
    required this.aoConcluir,
  });

  final ServicoAutenticacao servico;
  final MotivoDefinicaoSenha motivo;
  final VoidCallback aoConcluir;

  @override
  State<TelaDefinirSenha> createState() => _TelaDefinirSenhaState();
}

class _TelaDefinirSenhaState extends State<TelaDefinirSenha> {
  final _formulario = GlobalKey<FormState>();
  final _senha = TextEditingController();
  final _confirmacao = TextEditingController();
  bool _ocultarSenha = true;
  bool _enviando = false;
  String? _erro;

  @override
  void dispose() {
    _senha.dispose();
    _confirmacao.dispose();
    super.dispose();
  }

  Future<void> _salvar() async {
    if (_enviando || !_formulario.currentState!.validate()) return;
    setState(() {
      _enviando = true;
      _erro = null;
    });

    try {
      await widget.servico.definirNovaSenha(_senha.text);
      if (mounted) widget.aoConcluir();
    } on FalhaAutenticacao catch (erro) {
      if (!mounted) return;
      setState(() => _erro = erro.mensagem);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final convite = widget.motivo == MotivoDefinicaoSenha.convite;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CartaoInstitucional(
                    destaque: true,
                    padding: const EdgeInsets.all(28),
                    child: Form(
                      key: _formulario,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Align(
                            child: CircleAvatar(
                              radius: 34,
                              backgroundColor: CoresInstitucionais.vinhoFundo,
                              child: Icon(
                                Icons.password_outlined,
                                size: 36,
                                color: CoresInstitucionais.vinho,
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),
                          Text(
                            convite
                                ? 'Bem-vindo ao aplicativo'
                                : 'Recuperação de acesso',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.labelMedium
                                ?.copyWith(
                                  color: CoresInstitucionais.vinho,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 1,
                                ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            convite
                                ? 'Crie sua senha'
                                : 'Defina uma nova senha',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            convite
                                ? 'Seu convite foi confirmado. Escolha uma '
                                      'senha pessoal para concluir o acesso.'
                                : 'Escolha uma nova senha para voltar a '
                                      'acessar sua conta.',
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 28),
                          TextFormField(
                            controller: _senha,
                            obscureText: _ocultarSenha,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.newPassword],
                            decoration: InputDecoration(
                              labelText: 'Nova senha',
                              prefixIcon: const Icon(Icons.lock_outline),
                              suffixIcon: IconButton(
                                tooltip: _ocultarSenha
                                    ? 'Mostrar senha'
                                    : 'Ocultar senha',
                                onPressed: () => setState(
                                  () => _ocultarSenha = !_ocultarSenha,
                                ),
                                icon: Icon(
                                  _ocultarSenha
                                      ? Icons.visibility_outlined
                                      : Icons.visibility_off_outlined,
                                ),
                              ),
                            ),
                            validator: (valor) {
                              if ((valor ?? '').length < 8) {
                                return 'Use pelo menos 8 caracteres.';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _confirmacao,
                            obscureText: _ocultarSenha,
                            textInputAction: TextInputAction.done,
                            autofillHints: const [AutofillHints.newPassword],
                            onFieldSubmitted: (_) => _salvar(),
                            decoration: const InputDecoration(
                              labelText: 'Confirmar nova senha',
                              prefixIcon: Icon(Icons.lock_reset_outlined),
                            ),
                            validator: (valor) {
                              if (valor != _senha.text) {
                                return 'As senhas não coincidem.';
                              }
                              return null;
                            },
                          ),
                          if (_erro != null) ...[
                            const SizedBox(height: 16),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Theme.of(
                                  context,
                                ).colorScheme.errorContainer,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                _erro!,
                                style: TextStyle(
                                  color: Theme.of(
                                    context,
                                  ).colorScheme.onErrorContainer,
                                ),
                              ),
                            ),
                          ],
                          const SizedBox(height: 20),
                          FilledButton.icon(
                            onPressed: _enviando ? null : _salvar,
                            icon: _enviando
                                ? const SizedBox.square(
                                    dimension: 18,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(Icons.check_circle_outline),
                            label: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              child: Text(
                                convite
                                    ? 'Concluir meu acesso'
                                    : 'Salvar nova senha',
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  const RodapeUfpe(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
