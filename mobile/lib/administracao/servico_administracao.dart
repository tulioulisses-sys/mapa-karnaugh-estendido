import '../autenticacao/modelos_autenticacao.dart';
import 'modelos_administracao.dart';

abstract interface class ServicoAdministracao {
  Future<List<UsuarioAdministrado>> listarUsuarios();

  Future<void> alterarEstado(String usuarioId, EstadoConta estado);

  Future<void> definirAcesso(
    String usuarioId,
    TipoAcesso acesso,
    int? analisesRestantes,
  );

  Future<ResultadoCotasLote> ajustarCotasEmLote({
    required bool adicionar,
    required int quantidade,
    List<String>? usuarioIds,
  });

  Future<void> alterarPapel(String usuarioId, PapelUsuario papel);
}

class FalhaAdministracao implements Exception {
  const FalhaAdministracao(this.mensagem, {this.codigo});

  final String mensagem;
  final String? codigo;

  @override
  String toString() => mensagem;
}
