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

class ResultadoEncerramentoTurma {
  const ResultadoEncerramentoTurma({
    required this.usuariosAlterados,
    required this.matriculasEncerradas,
    required this.convitesCancelados,
  });

  factory ResultadoEncerramentoTurma.deJson(Map<String, dynamic> json) {
    return ResultadoEncerramentoTurma(
      usuariosAlterados:
          (json['usuarios_alterados'] as num?)?.toInt() ?? 0,
      matriculasEncerradas:
          (json['matriculas_encerradas'] as num?)?.toInt() ?? 0,
      convitesCancelados:
          (json['convites_cancelados'] as num?)?.toInt() ?? 0,
    );
  }

  final int usuariosAlterados;
  final int matriculasEncerradas;
  final int convitesCancelados;
}

class RegistroAuditoria {
  const RegistroAuditoria({
    required this.id,
    required this.atorId,
    required this.atorEmail,
    required this.acao,
    required this.entidade,
    required this.entidadeId,
    required this.valorAnterior,
    required this.valorPosterior,
    required this.criadaEm,
  });

  factory RegistroAuditoria.deJson(Map<String, dynamic> json) {
    return RegistroAuditoria(
      id: (json['id'] as num?)?.toInt() ?? 0,
      atorId: json['ator_id']?.toString(),
      atorEmail: json['ator_email']?.toString(),
      acao: json['acao']?.toString() ?? '',
      entidade: json['entidade']?.toString() ?? '',
      entidadeId: json['entidade_id']?.toString(),
      valorAnterior: _mapaOpcional(json['valor_anterior']),
      valorPosterior: _mapaOpcional(json['valor_posterior']),
      criadaEm: DateTime.tryParse(json['criada_em']?.toString() ?? ''),
    );
  }

  final int id;
  final String? atorId;
  final String? atorEmail;
  final String acao;
  final String entidade;
  final String? entidadeId;
  final Map<String, dynamic>? valorAnterior;
  final Map<String, dynamic>? valorPosterior;
  final DateTime? criadaEm;
}

Map<String, dynamic>? _mapaOpcional(Object? valor) {
  if (valor is! Map) return null;
  return Map<String, dynamic>.from(valor);
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
