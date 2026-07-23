import 'package:flutter/material.dart';
import 'package:pdfrx/pdfrx.dart';

import '../visual/identidade_visual.dart';

class TelaSobreMetodo extends StatelessWidget {
  const TelaSobreMetodo({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Sobre o método')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1000),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    CabecalhoInstitucional(
                      sobretitulo: 'Mapa de Karnaugh Estendido',
                      titulo: 'Sobre o método',
                      descricao:
                          'Técnica utilizada no projeto de comandos para '
                          'sistemas sequenciais fluídicos, como circuitos '
                          'pneumáticos, eletropneumáticos e hidráulicos. O '
                          'método parte da sequência de movimentos desejada, '
                          'analisa os estados do sistema e determina as '
                          'condições lógicas de cada avanço, retorno ou '
                          'mudança de memória.',
                    ),
                    SizedBox(height: 18),
                    _SecaoMetodo(
                      numero: 1,
                      titulo: 'Objetivo do método',
                      descricao:
                          'Obter equações de comando que executem a sequência '
                          'desejada de maneira organizada, segura e com a '
                          'menor quantidade possível de elementos auxiliares.',
                      paragrafos: [
                        'O objetivo principal é transformar uma sequência de '
                            'movimentos, como A+ → B+ → B− → A−, em um '
                            'conjunto de equações booleanas capazes de '
                            'controlar os atuadores.',
                        'Essas equações devem permitir que cada comando seja '
                            'acionado apenas no momento correto, evitando que '
                            'um mesmo sinal permaneça ativo em regiões '
                            'inadequadas do ciclo ou provoque movimentos '
                            'diferentes ao mesmo tempo.',
                      ],
                    ),
                    SizedBox(height: 16),
                    _SecaoMetodo(
                      numero: 2,
                      titulo: 'Como o método funciona',
                      descricao:
                          'A sequência é representada por estados físicos dos '
                          'atuadores e, quando necessário, por estados '
                          'adicionais de memória.',
                      paragrafos: [
                        'Cada atuador possui sinais que representam suas '
                            'posições. Por exemplo, a0 indica que o cilindro A '
                            'está recuado e a1 indica que ele está avançado.',
                        'Em atuadores com mais de duas posições, podem existir '
                            'sensores intermediários, como b0, b1, b2 e b3. '
                            'Nesses casos, a sequência também informa até qual '
                            'sensor o atuador deve se deslocar.',
                        'A operação é percorrida passo a passo. Em cada etapa, '
                            'observa-se o estado dos sensores e identifica-se '
                            'qual sinal deve provocar o próximo movimento.',
                        'Quando os mesmos sinais físicos aparecem em momentos '
                            'diferentes do ciclo, o método acrescenta memórias '
                            'como X, Y e Z para distinguir essas regiões '
                            'lógicas e separar corretamente os comandos.',
                        'Essas memórias dividem o ciclo em regiões lógicas '
                            'diferentes e permitem separar comandos que, sem '
                            'essa diferenciação, poderiam receber a mesma '
                            'condição de acionamento.',
                      ],
                    ),
                    SizedBox(height: 16),
                    _SecaoMetodo(
                      numero: 3,
                      titulo: 'Condição mínima e qualificação dos comandos',
                      descricao:
                          'Cada comando recebe inicialmente a condição que '
                          'representa a conclusão do passo anterior.',
                      paragrafos: [
                        'A primeira condição encontrada para um movimento é '
                            'chamada de condição mínima. Ela corresponde ao '
                            'sinal produzido pela etapa anterior da sequência.',
                        'Como essa condição pode aparecer em outro momento do '
                            'ciclo, o método compara o comando com seu '
                            'contracomando e com os demais movimentos.',
                        'Quando existe possibilidade de acionamento indevido, '
                            'são acrescentados sinais qualificadores: posições '
                            'de outros atuadores, estados das memórias ou '
                            'condições externas de um loop.',
                        'A qualificação garante que a equação seja verdadeira '
                            'apenas na região correta do mapa.',
                      ],
                    ),
                    SizedBox(height: 16),
                    _SecaoMetodo(
                      numero: 4,
                      titulo: 'Pontos perigosos',
                      descricao:
                          'Estados nos quais uma equação ainda poderia acionar '
                          'um movimento fora do momento previsto.',
                      paragrafos: [
                        'Mesmo depois da diferenciação entre comando e '
                            'contracomando, uma equação pode continuar '
                            'verdadeira em algum estado no qual sua saída '
                            'deveria estar desligada.',
                        'Um ponto perigoso representa uma situação em que o '
                            'circuito poderia produzir um movimento antecipado, '
                            'repetir uma ação já executada ou acionar uma saída '
                            'indevidamente.',
                        'Para eliminar esse risco, o método acrescenta um '
                            'qualificador complementar. A equação final deve '
                            'ser falsa em todos os pontos perigosos e verdadeira '
                            'somente durante a etapa necessária.',
                      ],
                    ),
                    SizedBox(height: 16),
                    _SecaoMetodo(
                      numero: 5,
                      titulo: 'Recursos adicionais da plataforma',
                      descricao:
                          'A ferramenta também interpreta movimentos '
                          'simultâneos, atuadores multiposição e trechos '
                          'repetitivos condicionais.',
                      paragrafos: [
                        'Além das sequências tradicionais, a plataforma '
                            'permite representar:',
                      ],
                      itens: [
                        'movimentos simultâneos: (B+, C+);',
                        'atuadores multiposição: B+ até b2;',
                        'loops condicionais: [C+, D+, C−, D−] enquanto e=0;',
                        'mais de um loop independente, usando sinais externos '
                            'diferentes, como e e f.',
                      ],
                      complemento:
                          "Nos loops, a condição negada, como e', normalmente "
                          'representa a repetição. A condição direta, como e, '
                          'representa a saída do trecho repetitivo.',
                    ),
                    SizedBox(height: 16),
                    _SecaoMetodo(
                      numero: 6,
                      titulo: 'Resultado fornecido pelo método',
                      descricao:
                          'Ao final, são obtidas as equações booleanas que '
                          'comandam os atuadores e as memórias do sistema.',
                      paragrafos: [
                        'O resultado contém equações para os avanços e '
                            'retornos dos atuadores, além das equações de '
                            'acionamento e desacionamento das memórias.',
                        'Quando uma saída aparece várias vezes, cada ocorrência '
                            'lógica é apresentada separadamente, como B+(1), '
                            'B+(2) e B+(3), seguida pela saída física agregada.',
                        'As equações podem ser usadas em circuitos pneumáticos, '
                            'eletropneumáticos ou hidráulicos, bem como em '
                            'relés, lógica elétrica, controladores programáveis '
                            'e sistemas de simulação.',
                        'A ferramenta automatiza essa análise: interpreta a '
                            'sequência, identifica os estados dos atuadores, '
                            'determina a quantidade necessária de memórias, '
                            'localiza qualificações e pontos perigosos, '
                            'constrói o mapa e apresenta as equações finais.',
                      ],
                    ),
                    SizedBox(height: 18),
                    _AvisoConceitual(),
                    SizedBox(height: 28),
                    _MateriaisReferencia(),
                    SizedBox(height: 28),
                    RodapeUfpe(),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SecaoMetodo extends StatelessWidget {
  const _SecaoMetodo({
    required this.numero,
    required this.titulo,
    required this.descricao,
    required this.paragrafos,
    this.itens = const [],
    this.complemento,
  });

  final int numero;
  final String titulo;
  final String descricao;
  final List<String> paragrafos;
  final List<String> itens;
  final String? complemento;

  @override
  Widget build(BuildContext context) {
    return CartaoInstitucional(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CabecalhoEtapa(
            numero: numero,
            titulo: titulo,
            descricao: descricao,
          ),
          const SizedBox(height: 18),
          for (final paragrafo in paragrafos) ...[
            Text(paragrafo, style: const TextStyle(height: 1.55)),
            const SizedBox(height: 12),
          ],
          for (final item in itens)
            Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.only(top: 7),
                    child: Icon(
                      Icons.circle,
                      size: 6,
                      color: CoresInstitucionais.vinho,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(child: Text(item)),
                ],
              ),
            ),
          if (complemento != null) ...[
            const SizedBox(height: 4),
            Text(complemento!, style: const TextStyle(height: 1.55)),
          ],
        ],
      ),
    );
  }
}

class _AvisoConceitual extends StatelessWidget {
  const _AvisoConceitual();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: CoresInstitucionais.vinhoFundo,
        border: Border.all(color: const Color(0xFFEBD0D7)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, color: CoresInstitucionais.vinho),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'O mapa de Karnaugh Estendido não é apenas uma simplificação '
              'algébrica. Ele também representa a evolução sequencial do '
              'sistema e utiliza memórias para diferenciar estados físicos '
              'que se repetem durante o ciclo.',
              style: TextStyle(height: 1.5),
            ),
          ),
        ],
      ),
    );
  }
}

class _MateriaisReferencia extends StatelessWidget {
  const _MateriaisReferencia();

  static const materiais = [
    _MaterialPdf(
      titulo: 'Guia rápido da plataforma',
      descricao:
          'Instruções para escrever sequências, representar movimentos '
          'simultâneos, usar sensores intermediários, configurar loops e '
          'interpretar os símbolos das equações.',
      caminho: 'assets/documentos/guia_rapido.pdf',
    ),
    _MaterialPdf(
      titulo: 'Artigo sobre o método',
      descricao:
          'Apresenta o método de projeto ótimo para circuitos sequenciais '
          'fluídicos, o uso de memórias e a obtenção das equações de comando.',
      caminho: 'assets/documentos/metodo_projeto_otimo.pdf',
    ),
    _MaterialPdf(
      titulo: 'Sistemas Automáticos',
      descricao:
          'Material didático sobre o mapa de Karnaugh Estendido, condições '
          'mínimas, qualificadores e pontos perigosos.',
      caminho: 'assets/documentos/sistemas_automaticos.pdf',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Materiais de referência e apoio',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 8),
        const Text(
          'Os três documentos do site estão incluídos no aplicativo e podem '
          'ser consultados mesmo sem conexão com a internet.',
        ),
        const SizedBox(height: 18),
        LayoutBuilder(
          builder: (context, constraints) {
            final largura = constraints.maxWidth < 760
                ? constraints.maxWidth
                : (constraints.maxWidth - 32) / 3;
            return Wrap(
              spacing: 16,
              runSpacing: 16,
              children: [
                for (final material in materiais)
                  SizedBox(
                    width: largura,
                    child: _CartaoMaterial(material: material),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _MaterialPdf {
  const _MaterialPdf({
    required this.titulo,
    required this.descricao,
    required this.caminho,
  });

  final String titulo;
  final String descricao;
  final String caminho;
}

class _CartaoMaterial extends StatelessWidget {
  const _CartaoMaterial({required this.material});

  final _MaterialPdf material;

  @override
  Widget build(BuildContext context) {
    return CartaoInstitucional(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Icon(
            Icons.picture_as_pdf_outlined,
            color: CoresInstitucionais.vinho,
            size: 34,
          ),
          const SizedBox(height: 14),
          Text(material.titulo, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          Text(material.descricao, style: const TextStyle(height: 1.45)),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: () => Navigator.of(context).push<void>(
              MaterialPageRoute(
                builder: (_) => _TelaDocumentoPdf(material: material),
              ),
            ),
            icon: const Icon(Icons.menu_book_outlined),
            label: const Text('Abrir PDF'),
          ),
        ],
      ),
    );
  }
}

class _TelaDocumentoPdf extends StatelessWidget {
  const _TelaDocumentoPdf({required this.material});

  final _MaterialPdf material;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(material.titulo)),
      body: PdfViewer.asset(material.caminho),
    );
  }
}
