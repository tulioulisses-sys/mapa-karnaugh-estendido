import 'package:supabase_flutter/supabase_flutter.dart';

import 'modelos_autenticacao.dart';
import 'servico_autenticacao.dart';

class ServicoAutenticacaoSupabase implements ServicoAutenticacao {
  ServicoAutenticacaoSupabase(this._cliente);

  final SupabaseClient _cliente;

  @override
  UsuarioSessao? get usuarioAtual =>
      _converterUsuario(_cliente.auth.currentUser);

  @override
  Stream<UsuarioSessao?> get mudancasSessao => _cliente.auth.onAuthStateChange
      .map((evento) => _converterUsuario(evento.session?.user));

  @override
  Future<void> entrar({required String email, required String senha}) async {
    try {
      final resposta = await _cliente.auth.signInWithPassword(
        email: email.trim(),
        password: senha,
      );
      if (resposta.user == null) {
        throw const FalhaAutenticacao(
          'Não foi possível identificar o usuário autenticado.',
        );
      }
    } on AuthException catch (erro) {
      throw FalhaAutenticacao(_traduzirErroAuth(erro.message));
    }
  }

  @override
  Future<ResultadoCadastro> cadastrar({
    required String email,
    required String senha,
  }) async {
    try {
      final resposta = await _cliente.auth.signUp(
        email: email.trim(),
        password: senha,
      );
      return ResultadoCadastro(
        requerConfirmacaoEmail: resposta.session == null,
      );
    } on AuthException catch (erro) {
      throw FalhaAutenticacao(_traduzirErroAuth(erro.message));
    }
  }

  @override
  Future<PerfilUsuario> carregarPerfil(String usuarioId) async {
    try {
      final dados = await _cliente
          .from('usuarios')
          .select('id,email,papel,estado,acesso,analises_restantes')
          .eq('id', usuarioId)
          .single();

      return PerfilUsuario(
        id: dados['id'] as String,
        email: dados['email'] as String,
        papel: PapelUsuario.deTexto(dados['papel'] as String?),
        estado: EstadoConta.deTexto(dados['estado'] as String?),
        acesso: TipoAcesso.deTexto(dados['acesso'] as String?),
        analisesRestantes: (dados['analises_restantes'] as num?)?.toInt(),
      );
    } on PostgrestException {
      throw const FalhaAutenticacao(
        'Não foi possível carregar as permissões da conta.',
      );
    }
  }

  @override
  Future<void> sair() async {
    try {
      await _cliente.auth.signOut();
    } on AuthException {
      throw const FalhaAutenticacao(
        'Não foi possível sair da conta neste momento.',
      );
    }
  }
}

UsuarioSessao? _converterUsuario(User? usuario) {
  if (usuario == null) return null;
  return UsuarioSessao(id: usuario.id, email: usuario.email);
}

String _traduzirErroAuth(String mensagem) {
  final normalizada = mensagem.toLowerCase();
  if (normalizada.contains('invalid login credentials')) {
    return 'E-mail ou senha incorretos.';
  }
  if (normalizada.contains('email not confirmed')) {
    return 'Confirme seu e-mail antes de entrar.';
  }
  if (normalizada.contains('already registered')) {
    return 'Este e-mail já possui cadastro.';
  }
  if (normalizada.contains('password')) {
    return 'A senha não atende aos requisitos de segurança.';
  }
  return 'Não foi possível concluir a autenticação.';
}
