enum PapelUsuario {
  master,
  submaster,
  usuario;

  String get rotulo => switch (this) {
    PapelUsuario.master => 'Master',
    PapelUsuario.submaster => 'Submaster',
    PapelUsuario.usuario => 'Aluno',
  };

  static PapelUsuario deTexto(String? valor) => switch (valor) {
    'master' => PapelUsuario.master,
    'submaster' => PapelUsuario.submaster,
    _ => PapelUsuario.usuario,
  };
}

enum EstadoConta {
  convidado,
  aguardandoAprovacao,
  ativo,
  suspenso,
  revogado;

  static EstadoConta deTexto(String? valor) => switch (valor) {
    'convidado' => EstadoConta.convidado,
    'ativo' => EstadoConta.ativo,
    'suspenso' => EstadoConta.suspenso,
    'revogado' => EstadoConta.revogado,
    _ => EstadoConta.aguardandoAprovacao,
  };
}

enum TipoAcesso {
  ilimitado,
  limitado;

  static TipoAcesso deTexto(String? valor) =>
      valor == 'ilimitado' ? TipoAcesso.ilimitado : TipoAcesso.limitado;
}

class UsuarioSessao {
  const UsuarioSessao({required this.id, required this.email});

  final String id;
  final String? email;
}

class PerfilUsuario {
  const PerfilUsuario({
    required this.id,
    required this.email,
    required this.papel,
    required this.estado,
    required this.acesso,
    required this.analisesRestantes,
  });

  final String id;
  final String email;
  final PapelUsuario papel;
  final EstadoConta estado;
  final TipoAcesso acesso;
  final int? analisesRestantes;

  bool get podeAnalisar =>
      estado == EstadoConta.ativo &&
      (acesso == TipoAcesso.ilimitado || (analisesRestantes ?? 0) > 0);
}

class ResultadoCadastro {
  const ResultadoCadastro({required this.requerConfirmacaoEmail});

  final bool requerConfirmacaoEmail;
}

class FalhaAutenticacao implements Exception {
  const FalhaAutenticacao(this.mensagem);

  final String mensagem;

  @override
  String toString() => mensagem;
}
