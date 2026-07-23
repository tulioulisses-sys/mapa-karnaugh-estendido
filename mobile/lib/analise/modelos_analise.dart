class ResultadoAnalise {
  const ResultadoAnalise({
    required this.atuadores,
    required this.etapas,
    required this.memorias,
    required this.equacoes,
    required this.equacoesMemorias,
    this.equacoesComandos = const {},
    this.equacoesFisicas = const {},
    this.sensoresPorAtuador = const {},
    this.sensoresIniciais = const {},
    this.atuadoresMultiposicao = const [],
    this.entradasExternas = const [],
    this.loops = const [],
    this.resolucao = const [],
    this.versaoMotor = '',
    required this.validacoes,
    required this.observacoes,
    required this.mapaSvg,
    required this.mapaLargura,
    required this.mapaAltura,
    required this.controleAcesso,
  });

  factory ResultadoAnalise.deJson(Map<String, dynamic> json) {
    return ResultadoAnalise(
      atuadores: _listaTextos(json['atuadores']),
      etapas: _listaMapas(json['etapas']),
      memorias: _listaTextos(json['memorias']),
      equacoes: _mapaTextos(json['equacoes']),
      equacoesMemorias: _mapaTextos(json['equacoes_memorias']),
      equacoesComandos: _mapaTextos(json['equacoes_comandos']),
      equacoesFisicas: _mapaTextos(json['equacoes_fisicas']),
      sensoresPorAtuador: _mapaListasTextos(json['sensores_por_atuador']),
      sensoresIniciais: _mapaTextos(json['sensores_iniciais']),
      atuadoresMultiposicao: _listaTextos(json['atuadores_multiposicao']),
      entradasExternas: _listaTextos(json['entradas_externas']),
      loops: _listaMapas(json['loops']),
      resolucao: _listaMapas(json['resolucao']),
      versaoMotor: json['versao_motor']?.toString() ?? '',
      validacoes: _listaTextos(json['validacoes']),
      observacoes: _listaTextos(json['observacoes']),
      mapaSvg: json['mapa_svg'] as String?,
      mapaLargura: (json['mapa_largura'] as num?)?.toDouble(),
      mapaAltura: (json['mapa_altura'] as num?)?.toDouble(),
      controleAcesso: ControleAcessoAnalise.deJson(
        _mapaDinamico(json['controle_acesso']),
      ),
    );
  }

  final List<String> atuadores;
  final List<Map<String, dynamic>> etapas;
  final List<String> memorias;
  final Map<String, String> equacoes;
  final Map<String, String> equacoesMemorias;
  final Map<String, String> equacoesComandos;
  final Map<String, String> equacoesFisicas;
  final Map<String, List<String>> sensoresPorAtuador;
  final Map<String, String> sensoresIniciais;
  final List<String> atuadoresMultiposicao;
  final List<String> entradasExternas;
  final List<Map<String, dynamic>> loops;
  final List<Map<String, dynamic>> resolucao;
  final String versaoMotor;
  final List<String> validacoes;
  final List<String> observacoes;
  final String? mapaSvg;
  final double? mapaLargura;
  final double? mapaAltura;
  final ControleAcessoAnalise controleAcesso;
}

class ControleAcessoAnalise {
  const ControleAcessoAnalise({
    required this.acesso,
    required this.estado,
    required this.analisesRestantes,
    required this.requisicaoRepetida,
  });

  factory ControleAcessoAnalise.deJson(Map<String, dynamic> json) {
    return ControleAcessoAnalise(
      acesso: json['acesso'] as String? ?? 'limitado',
      estado: json['estado'] as String? ?? 'consumida',
      analisesRestantes: (json['analises_restantes'] as num?)?.toInt(),
      requisicaoRepetida: json['requisicao_repetida'] as bool? ?? false,
    );
  }

  final String acesso;
  final String estado;
  final int? analisesRestantes;
  final bool requisicaoRepetida;

  String get rotuloCota => acesso == 'ilimitado'
      ? 'Análises ilimitadas'
      : '${analisesRestantes ?? 0} análise(s) restante(s)';
}

class FalhaAnalise implements Exception {
  const FalhaAnalise(this.mensagem, {this.codigo});

  final String mensagem;
  final String? codigo;

  @override
  String toString() => mensagem;
}

List<String> _listaTextos(Object? valor) => valor is List
    ? valor.map((item) => item.toString()).toList(growable: false)
    : const [];

List<Map<String, dynamic>> _listaMapas(Object? valor) => valor is List
    ? valor
          .whereType<Map>()
          .map(
            (item) => item.map(
              (chave, conteudo) => MapEntry(chave.toString(), conteudo),
            ),
          )
          .toList(growable: false)
    : const [];

Map<String, String> _mapaTextos(Object? valor) => valor is Map
    ? valor.map(
        (chave, conteudo) => MapEntry(chave.toString(), conteudo.toString()),
      )
    : const {};

Map<String, List<String>> _mapaListasTextos(Object? valor) => valor is Map
    ? valor.map(
        (chave, conteudo) => MapEntry(
          chave.toString(),
          _listaTextos(conteudo),
        ),
      )
    : const {};

Map<String, dynamic> _mapaDinamico(Object? valor) => valor is Map
    ? valor.map((chave, conteudo) => MapEntry(chave.toString(), conteudo))
    : const {};
