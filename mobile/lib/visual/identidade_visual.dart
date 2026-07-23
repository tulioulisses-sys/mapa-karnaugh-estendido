import 'package:flutter/material.dart';

abstract final class CoresInstitucionais {
  static const vinho = Color(0xFF7A1024);
  static const vinhoEscuro = Color(0xFF590B1A);
  static const vinhoClaro = Color(0xFFA43B4F);
  static const creme = Color(0xFFF7F5F0);
  static const branco = Color(0xFFFFFFFF);
  static const texto = Color(0xFF2E292B);
  static const textoSuave = Color(0xFF6F676A);
  static const borda = Color(0xFFE7E0DC);
  static const sucesso = Color(0xFF267449);
  static const sucessoFundo = Color(0xFFEDF8F1);
  static const erro = Color(0xFFA22B38);
  static const vinhoFundo = Color(0xFFF7EDF0);
}

ThemeData criarTemaInstitucional() {
  final textoBase = ThemeData.light(useMaterial3: true).textTheme;
  final esquema =
      ColorScheme.fromSeed(
        seedColor: CoresInstitucionais.vinho,
        brightness: Brightness.light,
        surface: CoresInstitucionais.branco,
      ).copyWith(
        primary: CoresInstitucionais.vinho,
        onPrimary: CoresInstitucionais.branco,
        primaryContainer: CoresInstitucionais.vinhoFundo,
        onPrimaryContainer: CoresInstitucionais.vinhoEscuro,
        secondary: CoresInstitucionais.vinhoClaro,
        onSecondary: CoresInstitucionais.branco,
        error: CoresInstitucionais.erro,
        outline: CoresInstitucionais.borda,
        surfaceContainerHighest: const Color(0xFFF3EFEC),
      );

  return ThemeData(
    colorScheme: esquema,
    useMaterial3: true,
    scaffoldBackgroundColor: Colors.transparent,
    canvasColor: CoresInstitucionais.creme,
    textTheme: textoBase.copyWith(
      headlineLarge: textoBase.headlineLarge?.copyWith(
        color: CoresInstitucionais.texto,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.8,
      ),
      headlineMedium: textoBase.headlineMedium?.copyWith(
        color: CoresInstitucionais.texto,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.4,
      ),
      headlineSmall: textoBase.headlineSmall?.copyWith(
        color: CoresInstitucionais.texto,
        fontWeight: FontWeight.w700,
      ),
      titleLarge: textoBase.titleLarge?.copyWith(
        color: CoresInstitucionais.texto,
        fontWeight: FontWeight.w700,
      ),
      titleMedium: textoBase.titleMedium?.copyWith(
        color: CoresInstitucionais.texto,
        fontWeight: FontWeight.w700,
      ),
      bodyLarge: textoBase.bodyLarge?.copyWith(
        color: CoresInstitucionais.texto,
      ),
      bodyMedium: textoBase.bodyMedium?.copyWith(
        color: CoresInstitucionais.textoSuave,
      ),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: CoresInstitucionais.creme,
      foregroundColor: CoresInstitucionais.texto,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(
        color: CoresInstitucionais.texto,
        fontSize: 20,
        fontWeight: FontWeight.w700,
      ),
    ),
    cardTheme: CardThemeData(
      color: CoresInstitucionais.branco,
      surfaceTintColor: Colors.transparent,
      elevation: 1,
      shadowColor: const Color(0x1448262E),
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(17),
        side: const BorderSide(color: CoresInstitucionais.borda),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: CoresInstitucionais.borda),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: CoresInstitucionais.borda),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(
          color: CoresInstitucionais.vinho,
          width: 1.6,
        ),
      ),
      filled: true,
      fillColor: CoresInstitucionais.branco,
      labelStyle: const TextStyle(color: CoresInstitucionais.textoSuave),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(0, 52),
        backgroundColor: CoresInstitucionais.vinho,
        foregroundColor: CoresInstitucionais.branco,
        disabledBackgroundColor: CoresInstitucionais.borda,
        disabledForegroundColor: CoresInstitucionais.textoSuave,
        textStyle: const TextStyle(fontWeight: FontWeight.w700),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(0, 48),
        foregroundColor: CoresInstitucionais.vinho,
        side: const BorderSide(color: CoresInstitucionais.borda),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11)),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: CoresInstitucionais.vinho,
        textStyle: const TextStyle(fontWeight: FontWeight.w700),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: CoresInstitucionais.vinhoFundo,
      side: const BorderSide(color: Color(0xFFEBD0D7)),
      labelStyle: const TextStyle(
        color: CoresInstitucionais.vinho,
        fontWeight: FontWeight.w600,
      ),
      iconTheme: const IconThemeData(color: CoresInstitucionais.vinho),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
    ),
    dividerTheme: const DividerThemeData(color: CoresInstitucionais.borda),
  );
}

class FundoInstitucional extends StatelessWidget {
  const FundoInstitucional({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: CoresInstitucionais.creme,
      child: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(1.15, -1.15),
            radius: 1.15,
            colors: [Color(0x147A1024), Color(0x007A1024)],
            stops: [0, 1],
          ),
        ),
        child: child,
      ),
    );
  }
}

class CartaoInstitucional extends StatelessWidget {
  const CartaoInstitucional({
    super.key,
    required this.child,
    this.destaque = false,
    this.padding = const EdgeInsets.all(24),
  });

  final Widget child;
  final bool destaque;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: CoresInstitucionais.branco,
      elevation: 1,
      shadowColor: const Color(0x2448262E),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: CoresInstitucionais.borda),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          if (destaque)
            const Positioned(
              left: 0,
              top: 0,
              bottom: 0,
              child: ColoredBox(
                color: CoresInstitucionais.vinho,
                child: SizedBox(width: 5),
              ),
            ),
          Padding(
            padding: destaque
                ? padding.add(const EdgeInsets.only(left: 5))
                : padding,
            child: child,
          ),
        ],
      ),
    );
  }
}

class CabecalhoInstitucional extends StatelessWidget {
  const CabecalhoInstitucional({
    super.key,
    required this.titulo,
    this.sobretitulo,
    this.descricao,
  });

  final String titulo;
  final String? sobretitulo;
  final String? descricao;

  @override
  Widget build(BuildContext context) {
    return CartaoInstitucional(
      destaque: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (sobretitulo != null) ...[
            Text(
              sobretitulo!.toUpperCase(),
              style: const TextStyle(
                color: CoresInstitucionais.vinho,
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 8),
          ],
          Text(titulo, style: Theme.of(context).textTheme.headlineMedium),
          if (descricao != null) ...[
            const SizedBox(height: 12),
            Text(
              descricao!,
              style: const TextStyle(
                color: CoresInstitucionais.textoSuave,
                height: 1.55,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class CabecalhoEtapa extends StatelessWidget {
  const CabecalhoEtapa({
    super.key,
    required this.numero,
    required this.titulo,
    required this.descricao,
  });

  final int numero;
  final String titulo;
  final String descricao;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 34,
          height: 34,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: CoresInstitucionais.vinho,
            borderRadius: BorderRadius.circular(9),
          ),
          child: Text(
            numero.toString(),
            style: const TextStyle(
              color: CoresInstitucionais.branco,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: 13),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(titulo, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 4),
              Text(
                descricao,
                style: const TextStyle(
                  color: CoresInstitucionais.textoSuave,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class RodapeUfpe extends StatelessWidget {
  const RodapeUfpe({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: CoresInstitucionais.branco,
        border: Border.all(color: CoresInstitucionais.borda),
        borderRadius: BorderRadius.circular(14),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          const SizedBox(
            width: double.infinity,
            height: 3,
            child: ColoredBox(color: CoresInstitucionais.vinho),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 18),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final compacto = constraints.maxWidth < 620;
                final marca = Text(
                  'UFPE',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: CoresInstitucionais.vinho,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.6,
                  ),
                );
                const descricao = Text(
                  'Universidade Federal de Pernambuco\n'
                  'Engenharia Mecânica · Circuitos Fluídicos Mecânicos\n'
                  'Professor: Antonio Marques da Costa Soares Junior',
                  style: TextStyle(
                    color: CoresInstitucionais.textoSuave,
                    height: 1.5,
                    fontSize: 13,
                  ),
                );

                if (compacto) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [marca, const Divider(height: 20), descricao],
                  );
                }
                return Row(
                  children: [
                    marca,
                    const SizedBox(width: 20),
                    const SizedBox(
                      height: 42,
                      child: VerticalDivider(width: 1),
                    ),
                    const SizedBox(width: 20),
                    const Expanded(child: descricao),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
