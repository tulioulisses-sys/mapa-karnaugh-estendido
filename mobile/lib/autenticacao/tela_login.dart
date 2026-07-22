import 'package:flutter/material.dart';

import '../visual/identidade_visual.dart';
import 'modelos_autenticacao.dart';
import 'servico_autenticacao.dart';

class TelaLogin extends StatefulWidget {
  const TelaLogin({super.key, required this.servico, this.avisoSessao});

  final ServicoAutenticacao servico;
  final String? avisoSessao;

  @override
  State<TelaLogin> createState() => _TelaLoginState();
}

class _TelaLoginState extends State<TelaLogin> {
  final _formulario = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _senha = TextEditingController();
  bool _cadastro = false;
  bool _ocultarSenha = true;
  bool _enviando = false;
  String? _mensagem;
  bool _mensagemErro = false;

  @override
  void dispose() {
    _email.dispose();
    _senha.dispose();
    super.dispose();
  }

  Future<void> _enviar() async {
    if (!_formulario.currentState!.validate() || _enviando) return;
    setState(() {
      _enviando = true;
      _mensagem = null;
    });

    try {
      if (_cadastro) {
        final resultado = await widget.servico.cadastrar(
          email: _email.text,
          senha: _senha.text,
        );
        if (!mounted) return;
        setState(() {
          _mensagemErro = false;
          _mensagem = resultado.requerConfirmacaoEmail
              ? 'Cadastro criado. Confira seu e-mail para confirmar a conta.'
              : 'Cadastro criado com sucesso.';
          _senha.clear();
        });
      } else {
        await widget.servico.entrar(email: _email.text, senha: _senha.text);
      }
    } on FalhaAutenticacao catch (erro) {
      if (!mounted) return;
      setState(() {
        _mensagemErro = true;
        _mensagem = erro.mensagem;
      });
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  void _alternarModo() {
    setState(() {
      _cadastro = !_cadastro;
      _mensagem = null;
      _mensagemErro = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final aviso = widget.avisoSessao;

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
                                Icons.account_tree_outlined,
                                size: 36,
                                color: CoresInstitucionais.vinho,
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),
                          Text(
                            'UFPE · ENGENHARIA MECÂNICA',
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
                            'Mapa de Karnaugh Estendido',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            _cadastro
                                ? 'Crie sua conta para solicitar acesso.'
                                : 'Entre para realizar suas análises.',
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 28),
                          TextFormField(
                            controller: _email,
                            keyboardType: TextInputType.emailAddress,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.email],
                            decoration: const InputDecoration(
                              labelText: 'E-mail',
                              prefixIcon: Icon(Icons.email_outlined),
                            ),
                            validator: (valor) {
                              final texto = valor?.trim() ?? '';
                              if (!texto.contains('@') || texto.endsWith('@')) {
                                return 'Informe um e-mail válido.';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _senha,
                            obscureText: _ocultarSenha,
                            textInputAction: TextInputAction.done,
                            autofillHints: const [AutofillHints.password],
                            onFieldSubmitted: (_) => _enviar(),
                            decoration: InputDecoration(
                              labelText: 'Senha',
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
                              if ((valor ?? '').length < 6) {
                                return 'A senha precisa ter pelo menos 6 caracteres.';
                              }
                              return null;
                            },
                          ),
                          if (aviso != null) ...[
                            const SizedBox(height: 16),
                            _Aviso(mensagem: aviso, erro: true),
                          ],
                          if (_mensagem != null) ...[
                            const SizedBox(height: 16),
                            _Aviso(mensagem: _mensagem!, erro: _mensagemErro),
                          ],
                          const SizedBox(height: 20),
                          FilledButton(
                            onPressed: _enviando ? null : _enviar,
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              child: _enviando
                                  ? const SizedBox.square(
                                      dimension: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : Text(_cadastro ? 'Criar conta' : 'Entrar'),
                            ),
                          ),
                          const SizedBox(height: 8),
                          TextButton(
                            onPressed: _enviando ? null : _alternarModo,
                            child: Text(
                              _cadastro
                                  ? 'Já tenho uma conta'
                                  : 'Criar uma conta',
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

class _Aviso extends StatelessWidget {
  const _Aviso({required this.mensagem, required this.erro});

  final String mensagem;
  final bool erro;

  @override
  Widget build(BuildContext context) {
    final cores = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: erro ? cores.errorContainer : CoresInstitucionais.sucessoFundo,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        mensagem,
        style: TextStyle(
          color: erro ? cores.onErrorContainer : CoresInstitucionais.sucesso,
        ),
      ),
    );
  }
}
