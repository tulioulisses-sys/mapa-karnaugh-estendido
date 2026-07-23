import '../autenticacao/modelos_autenticacao.dart';

class UsuarioAdministrado {
  const UsuarioAdministrado({
    required this.id,
    required this.email,
    required this.papel,
    required this.estado,
    required this.acesso,
    required this.analisesRestantes,
  });

  factory UsuarioAdministrado.deJson(Map<String, dynamic> json) {
    return UsuarioAdministrado(
      id: json['id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      papel: PapelUsuario.deTexto(json['papel']?.toString()),
      estado: EstadoConta.deTexto(json['estado']?.toString()),
      acesso: TipoAcesso.deTexto(json['acesso']?.toString()),
      analisesRestantes: (json['analises_restantes'] as num?)?.toInt(),
    );
  }

  final String id;
  final String email;
  final PapelUsuario papel;
  final EstadoConta estado;
  final TipoAcesso acesso;
  final int? analisesRestantes;

  bool get aguardando =>
      estado == EstadoConta.aguardandoAprovacao ||
      estado == EstadoConta.convidado;
}

class ResultadoCotasLote {
  const ResultadoCotasLote({
    required this.usuariosAlterados,
    required this.usuariosIgnorados,
  });

  factory ResultadoCotasLote.deJson(Map<String, dynamic> json) {
    return ResultadoCotasLote(
      usuariosAlterados: (json['usuarios_alterados'] as num?)?.toInt() ?? 0,
      usuariosIgnorados: (json['usuarios_ignorados'] as num?)?.toInt() ?? 0,
    );
  }

  final int usuariosAlterados;
  final int usuariosIgnorados;
}
