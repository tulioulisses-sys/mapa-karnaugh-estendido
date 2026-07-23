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

class TurmaAdministrada {
  const TurmaAdministrada({
    required this.id,
    required this.codigo,
    required this.nome,
    required this.ativa,
    required this.quantidadeAlunos,
  });

  factory TurmaAdministrada.deJson(Map<String, dynamic> json) {
    return TurmaAdministrada(
      id: json['id']?.toString() ?? '',
      codigo: json['codigo']?.toString() ?? '',
      nome: json['nome']?.toString() ?? '',
      ativa: json['ativa'] == true,
      quantidadeAlunos: (json['quantidade_alunos'] as num?)?.toInt() ?? 0,
    );
  }

  final String id;
  final String codigo;
  final String nome;
  final bool ativa;
  final int quantidadeAlunos;
}

class ConviteAdministrado {
  const ConviteAdministrado({
    required this.id,
    required this.email,
    required this.papelDestino,
    required this.acessoDestino,
    required this.analisesIniciais,
    required this.turmaId,
    required this.turmaCodigo,
    required this.estado,
    required this.expiraEm,
  });

  factory ConviteAdministrado.deJson(Map<String, dynamic> json) {
    return ConviteAdministrado(
      id: json['id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      papelDestino: PapelUsuario.deTexto(json['papel_destino']?.toString()),
      acessoDestino: TipoAcesso.deTexto(json['acesso_destino']?.toString()),
      analisesIniciais: (json['analises_iniciais'] as num?)?.toInt(),
      turmaId: json['turma_id']?.toString(),
      turmaCodigo: json['turma_codigo']?.toString(),
      estado: json['estado']?.toString() ?? '',
      expiraEm: DateTime.tryParse(json['expira_em']?.toString() ?? ''),
    );
  }

  final String id;
  final String email;
  final PapelUsuario papelDestino;
  final TipoAcesso acessoDestino;
  final int? analisesIniciais;
  final String? turmaId;
  final String? turmaCodigo;
  final String estado;
  final DateTime? expiraEm;

  bool get pendente => estado == 'pendente';
}

class ResultadoConvitesLote {
  const ResultadoConvitesLote({
    required this.total,
    required this.emailsEnviados,
    required this.emailsComFalha,
  });

  factory ResultadoConvitesLote.deJson(Map<String, dynamic> json) {
    return ResultadoConvitesLote(
      total: (json['total'] as num?)?.toInt() ?? 0,
      emailsEnviados: (json['emails_enviados'] as num?)?.toInt() ?? 0,
      emailsComFalha: (json['emails_com_falha'] as num?)?.toInt() ?? 0,
    );
  }

  final int total;
  final int emailsEnviados;
  final int emailsComFalha;
}

class TransferenciaMaster {
  const TransferenciaMaster({
    required this.id,
    required this.masterAtualId,
    required this.masterAtualEmail,
    required this.emailDestino,
    required this.usuarioDestinoId,
    required this.estado,
    required this.expiraEm,
    required this.souOrigem,
    required this.souDestino,
    required this.envioEmail,
  });

  factory TransferenciaMaster.deJson(Map<String, dynamic> json) {
    return TransferenciaMaster(
      id: json['id']?.toString() ?? '',
      masterAtualId: json['master_atual_id']?.toString() ?? '',
      masterAtualEmail: json['master_atual_email']?.toString() ?? '',
      emailDestino: json['email_destino']?.toString() ?? '',
      usuarioDestinoId: json['usuario_destino_id']?.toString(),
      estado: json['estado']?.toString() ?? '',
      expiraEm: DateTime.tryParse(json['expira_em']?.toString() ?? ''),
      souOrigem: json['sou_origem'] == true,
      souDestino: json['sou_destino'] == true,
      envioEmail: json['envio_email']?.toString(),
    );
  }

  final String id;
  final String masterAtualId;
  final String masterAtualEmail;
  final String emailDestino;
  final String? usuarioDestinoId;
  final String estado;
  final DateTime? expiraEm;
  final bool souOrigem;
  final bool souDestino;
  final String? envioEmail;

  bool get pendente => estado == 'pendente';
  bool get emailEnviado => envioEmail == 'enviado';
}
