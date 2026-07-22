import 'modelos_analise.dart';

abstract interface class ServicoAnalise {
  Future<ResultadoAnalise> resolver({
    required String sequencia,
    required String chaveIdempotencia,
    required bool cicloContinuo,
    required bool incluirMapa,
  });
}
