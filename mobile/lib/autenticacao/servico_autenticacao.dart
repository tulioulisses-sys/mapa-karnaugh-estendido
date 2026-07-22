import 'modelos_autenticacao.dart';

abstract interface class ServicoAutenticacao {
  UsuarioSessao? get usuarioAtual;

  Stream<UsuarioSessao?> get mudancasSessao;

  Future<void> entrar({required String email, required String senha});

  Future<ResultadoCadastro> cadastrar({
    required String email,
    required String senha,
  });

  Future<PerfilUsuario> carregarPerfil(String usuarioId);

  Future<String> obterTokenAcesso();

  Future<void> sair();
}
