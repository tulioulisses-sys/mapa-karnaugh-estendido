# Bloco 02A — Piloto das estratégias de busca e estudos-sentinela (v0.1)

**Projeto:** Mapa de Karnaugh Estendido  
**Protocolo congelado:** `protocolo-revisao-v0.2-pre-busca`  
**Commit do protocolo:** `26d1345`  
**Data do piloto exploratório:** 2026-08-10  
**Status:** piloto de sensibilidade; **não é a busca formal em Scopus/Web of Science/Compendex**.

---

## 1. Objetivo

Testar se as famílias de termos definidas no protocolo conseguem recuperar
literatura que já sabemos ser relevante e detectar cegueiras terminológicas
antes da execução das buscas formais nas bases bibliográficas.

Este piloto usa um mecanismo geral de busca na Web. Portanto:

- não mede recall verdadeiro de Scopus, Web of Science, Compendex etc.;
- não substitui a execução documentada das strings em cada base;
- serve para testar vocabulário, descobrir variantes terminológicas e
  identificar estudos históricos que as strings iniciais podem perder.

---

## 2. Estudos-sentinela do protocolo

Os sentinelas congelados antes do piloto são:

| ID | Estudo | Ano | Papel |
|---|---|---:|---|
| S-A | Cheng & Foster — *Systematic Method of Designing Fluidic–Pneumatic Control Circuits* | 1972 | síntese sistemática histórica |
| S-B | Rohner — *Fluid Power Logic Circuit Design* | 1979 | Karnaugh–Veitch para circuitos sequenciais |
| S-C | Siangkok/Sim & Chua — *Symbolic pattern manipulation of Karnaugh-Veitch maps for pneumatic circuits* | 1996 | PNEUMAES / automação computacional |
| S-D | Santos & Silva — *Methodology for manipulation of Karnaugh maps designing for pneumatic sequential logic circuits* | 2017 | metodologia moderna Karnaugh |
| S-E | Silva & Santos — *A Simulation Tool Using AI Technics and Karnaugh Maps for Learning and Control Digital Pneumatics* | 2019 | ISEPCPC / Prolog / sistema especialista |
| S-F | Fawzi & Salloom — *Developing Multiple-Actuator Pneumatic Circuits Using the Karnaugh Maps Designing PLC Controlled* | 2023 | múltiplos atuadores/sequências |

---

## 3. Resultado do teste da string ampla Karnaugh + pneumática + sequencial

String testada:

```text
("Karnaugh map" OR "Karnaugh matrix")
AND (pneumatic OR electropneumatic OR fluidic)
AND (sequential OR sequence)
```

Na amostra de resultados devolvida pelo mecanismo usado no piloto foram
recuperados diretamente:

- Santos & Silva (2017);
- Cheng & Foster (1972);
- Fawzi & Salloom (2023).

Também apareceu o precursor de conferência de Santos & Silva (2015).

Não apareceram na amostra retornada:

- Rohner (1979);
- PNEUMAES (1996);
- ISEPCPC (2019).

### Interpretação

A string é útil como núcleo temático, mas não deve ser usada isoladamente.

Ela favorece estudos que usam explicitamente as palavras *Karnaugh map*,
*pneumatic* e *sequential* em metadados modernos, mas pode perder:

- livros;
- trabalhos que usam **Karnaugh–Veitch** em vez de *Karnaugh map*;
- trabalhos de CAD/sistemas especialistas cujo título enfatiza computação;
- literatura histórica de *fluid logic*.

---

## 4. Teste da família automação/CAD

String inicial:

```text
("computer-aided" OR automatic OR automated)
AND (pneumatic OR fluidic)
AND sequential
AND (control OR synthesis)
```

O piloto recuperou Cheng & Foster (1972) e descobriu diretamente literatura
adicional muito importante, incluindo:

### N1 — CAD para controle pneumático sequencial (1985)

**CAD for Pneumatic Circuit Design in Low Cost Automation**  
IFAC Proceedings Volumes, 1985.

O resumo descreve:

- uma linguagem especial para especificar a sequência;
- designação de memórias;
- geração de funções;
- minimização de funções de comutação;
- construção automática do circuito.

Esse trabalho é anterior ao PNEUMAES e deverá entrar na triagem formal.

### N2 — CAD de circuitos fluídicos sequenciais (1975)

**Computer Aided Design for Fluidic Sequential Circuits of Fundamental Mode**  
Yau-Hwang Lee, dissertação de mestrado, Portland State University, 1975.

O resumo descreve:

- síntese por diagrama de estados;
- programa computacional para circuitos de realimentação sequenciais fluídicos;
- variáveis secundárias/memórias;
- simplificação de equações;
- consideração posterior de características de transmissão para circuito
  livre de hazards.

Esse trabalho é particularmente relevante para a história de automação,
corretude e hazards.

### Consequência

A literatura de automação do problema é **substancialmente mais antiga** que
1996 e não está restrita a Karnaugh.

Qualquer claim de novidade deverá distinguir:

- automatização genérica de controle sequencial pneumático;
- automatização específica de Karnaugh/Karnaugh–Veitch;
- formalização;
- verificação;
- classes adicionais de entrada;
- geração de contraexemplos;
- propriedades demonstradas.

---

## 5. Teste da terminologia Karnaugh–Veitch

String refinada:

```text
("Karnaugh" OR "Karnaugh-Veitch")
AND (pneumatic OR fluidic OR electropneumatic)
AND (computer OR automatic OR automated OR "expert system" OR CAD OR software)
```

O piloto recuperou diretamente:

- PNEUMAES (1996);
- trabalhos modernos de Karnaugh;
- literatura CAD relacionada.

O PNEUMAES é descrito pelo artigo de 1996 como um sistema especialista
prototípico cujo núcleo é a manipulação simbólica computacional do mapa
Karnaugh–Veitch. O artigo declara geração automática de equações minimizadas
para circuitos pneumáticos puros e menciona explosão combinatória, limitando o
sistema descrito a até quatro cilindros com válvulas auxiliares.

### Decisão

**Karnaugh–Veitch** precisa permanecer como termo de busca explícito. Não pode
ser tratado apenas como sinônimo implícito de *Karnaugh map*.

---

## 6. Teste da terminologia sistema especialista / Prolog

String refinada:

```text
(Karnaugh AND pneumatic)
AND ("expert system" OR Prolog OR PNEUMAES OR ISEPCPC)
```

O piloto recuperou diretamente:

- PNEUMAES (1996);
- ISEPCPC (2019).

O registro institucional do ISEPCPC descreve software em PROLOG, técnicas de
IA/sistema especialista e metodologia de Karnaugh para obtenção automática de
equações lógicas otimizadas.

### Decisão

A busca formal precisa conter uma família voltada a:

- expert system;
- knowledge-based system;
- Prolog;
- symbolic manipulation;
- computer-aided;
- automatic/automated design.

Os nomes `PNEUMAES` e `ISEPCPC` serão usados em busca de validação/snowballing,
não como únicos termos da busca sistemática.

---

## 7. Terminologia histórica detectada

O piloto mostrou pelo menos as seguintes famílias terminológicas:

### T1 — Karnaugh
- Karnaugh map;
- Karnaugh mapping method;
- Karnaugh matrix.

### T2 — Karnaugh–Veitch
- Karnaugh-Veitch map;
- Karnaugh–Veitch mapping method;
- KV map.

### T3 — lógica fluídica/pneumática
- fluid logic;
- fluidic–pneumatic control;
- pneumatic sequential control;
- pneumatic sequential circuits;
- fluidic sequential circuits.

### T4 — automação computacional
- computer-aided design;
- CAD;
- automatic design;
- expert system;
- symbolic manipulation;
- web-based computer-aided design.

### T5 — formalismos/variáveis históricas
- switching algebra;
- switching function;
- state diagram synthesis;
- secondary variables;
- auxiliary memory;
- fundamental mode;
- hazard-free circuit.

---

## 8. Problema com o termo “extended Karnaugh”

No piloto, a expressão literal **extended Karnaugh** não apareceu como
terminologia dominante da literatura central recuperada.

As fontes históricas e modernas encontradas usam mais frequentemente:

- Karnaugh;
- Karnaugh map;
- Karnaugh–Veitch;
- Karnaugh mapping method.

### Implicação metodológica

A busca formal **não pode depender do nome atual do nosso software/método**.

“Extended Karnaugh” continuará sendo buscado, mas como uma variante, e não como
o eixo principal de recuperação.

Isso também significa que o artigo deverá investigar de onde vem exatamente a
expressão “Mapa de Karnaugh Estendido” usada no contexto do projeto.

---

## 9. Novos candidatos descobertos no piloto

Estes trabalhos não alteram retroativamente o conjunto de sentinelas congelado;
eles entram como registros descobertos durante o piloto e deverão passar pela
triagem normal.

### P02A-N01
**CAD for Pneumatic Circuit Design in Low Cost Automation**  
1985.  
Tema: CAD para controle pneumático sequencial, memória, minimização e geração
de circuito.

### P02A-N02
**Computer Aided Design for Fluidic Sequential Circuits of Fundamental Mode**  
Lee, 1975.  
Tema: síntese por estados, programa computacional, variáveis secundárias e
hazards.

### P02A-N03
**A web-based computer-aided pneumatic circuit design software**  
2003.  
Tema: CAD/simulação pneumática colaborativa baseada na Web.

### P02A-N04
**Evolutionary Algorithms for Programming Pneumatic Sequential Circuit
Controllers**  
2017.  
Tema: geração automática de lógica/PLC por algoritmos genéticos e programação
genética.

### P02A-N05
**Adaptability of Karnaugh Maps to Implement and Solve Complex Control Problems
of Pneumatic and Electropneumatic Systems**  
2021.  
Tema: múltiplas sequências e Karnaugh.

### P02A-N06
**Symbolic Manipulation for Optimization of Boolean Functions for Control of
Pneumatic and Electropneumatic Circuits**  
2021/2022.  
Tema: manipulação simbólica computacional de Karnaugh em Prolog.

### P02A-N07
**Aplicación de los diagramas de Karnaugh–Veitch, en el diseño de circuitos
neumáticos con señales blocantes**  
2018.  
Tema: Karnaugh–Veitch e sinais blocantes; importante para o estrato em espanhol.

---

## 10. Avaliação provisória dos sentinelas

Este quadro registra apenas o comportamento do **piloto Web**, e não recall de
bases bibliográficas.

| Sentinela | Busca temática ampla | Busca refinada/específica | Situação |
|---|---|---|---|
| Cheng & Foster 1972 | recuperado | recuperado | OK |
| Rohner 1979 | não surgiu na amostra ampla | recuperável por Karnaugh–Veitch/título | exige cobertura de livros/snowballing |
| PNEUMAES 1996 | não surgiu na amostra ampla | recuperado | ampliar termos computacionais/KV |
| Santos & Silva 2017 | recuperado | recuperado | OK |
| ISEPCPC 2019 | não surgiu na amostra ampla | recuperado | ampliar expert system/Prolog |
| Fawzi & Salloom 2023 | recuperado | recuperado | OK |

---

## 11. Strings candidatas após o piloto

Essas strings são **candidatas para adaptação por base**, conforme permitido
pelo protocolo. A versão literalmente executada em cada base deverá ser
registrada.

### Q10 — Karnaugh/KV + automação

```text
("Karnaugh map" OR "Karnaugh matrix" OR "Karnaugh-Veitch" OR "KV map")
AND
(pneumatic OR electropneumatic OR "electro-pneumatic" OR fluidic OR "fluid logic")
AND
("computer-aided" OR CAD OR automatic OR automated OR software
 OR "expert system" OR "knowledge-based" OR "symbolic manipulation")
```

### Q11 — CAD/síntese pneumática sem exigir Karnaugh

```text
(pneumatic OR fluidic OR "fluid logic")
AND
("sequential control" OR "sequential circuit" OR "sequential circuits")
AND
("computer-aided" OR CAD OR automatic OR automated OR synthesis)
AND
(memory OR "secondary variable" OR Boolean OR "switching function"
 OR "state diagram")
```

### Q12 — terminologia histórica de síntese

```text
(pneumatic OR fluidic OR "fluid logic")
AND sequential
AND
("state diagram synthesis" OR "switching algebra" OR "switching function"
 OR "secondary variable" OR "fundamental mode")
```

### Q13 — sistemas especialistas

```text
(pneumatic OR electropneumatic OR fluidic)
AND
(Karnaugh OR "Karnaugh-Veitch" OR sequential)
AND
("expert system" OR "knowledge-based system" OR Prolog
 OR "symbolic manipulation")
```

### Q14 — espanhol

```text
("Karnaugh-Veitch" OR "mapa de Karnaugh" OR "diagramas de Karnaugh")
AND
(neumático OR neumática OR electroneumático OR secuencial)
```

---

## 12. Critério para avançar

Ainda **não executar a busca formal como se as strings estivessem validadas**.

Próxima etapa:

1. preservar este relatório do piloto;
2. criar a planilha/CSV de log de buscas;
3. criar a tabela mestre de registros;
4. adaptar Q1–Q14 para cada base;
5. executar a validação dos sentinelas dentro das bases disponíveis;
6. só então executar as buscas formais com data, string, filtros e total de
   resultados registrados.

---

## 13. Conclusão do piloto

O piloto cumpriu sua função: revelou que uma estratégia centrada apenas em
`Karnaugh map + pneumatic + sequential` seria estreita demais.

A literatura relevante usa vocabulários diferentes ao longo do tempo e inclui
linhas de:

- síntese algébrica;
- Karnaugh–Veitch;
- state-diagram synthesis;
- CAD;
- sistemas especialistas;
- Prolog;
- manipulação simbólica;
- PLC;
- algoritmos evolutivos.

O protocolo congelado permanece válido porque já previa busca em estratos,
adaptação de strings, snowballing e literatura histórica. O que muda após o
piloto é a **execução concreta das strings**, que deverá incorporar as variantes
terminológicas documentadas aqui.
