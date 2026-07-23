import 'modelos_autenticacao.dart';

abstract interface class ServicoAutenticacao {
  UsuarioSessao? get usuarioAtual;

  MotivoDefinicaoSenha? get definicaoSenhaPendente;

  Stream<UsuarioSessao?> get mudancasSessao;

  Stream<MotivoDefinicaoSenha> get solicitacoesDefinicaoSenha;

  Future<void> entrar({required String email, required String senha});

  Future<ResultadoCadastro> cadastrar({
    required String email,
    required String senha,
  });

  Future<PerfilUsuario> carregarPerfil(String usuarioId);

  Future<String> obterTokenAcesso();

  Future<void> solicitarRedefinicaoSenha(String email);

  Future<void> definirNovaSenha(String senha);

  Future<void> sair();
}
