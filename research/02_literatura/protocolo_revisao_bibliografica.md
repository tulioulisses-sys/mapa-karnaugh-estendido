# Bloco 02 — Protocolo de revisão bibliográfica (v0.2)

**Projeto:** Mapa de Karnaugh Estendido  
**Baseline científica anterior:** Bloco 01 v0.3, commit `d3535c1`  
**Branch:** `pesquisa-formalizacao-verificacao`  
**Status:** protocolo pré-busca; deve ser congelado antes da triagem sistemática.

---

## 1. Objetivo

Executar uma revisão bibliográfica rastreável e reproduzível capaz de responder:

1. qual é a origem e evolução do método de síntese sequencial baseado em mapas/matrizes de Karnaugh para circuitos pneumáticos, eletropneumáticos, hidráulicos ou fluídicos;
2. quais propriedades e hipóteses o método original e suas extensões realmente afirmam;
3. quais recursos já aparecem na literatura: simultaneidade, memórias, multiposição, entradas externas, ciclos/loops, PLC, minimização, pontos perigosos e condições de segurança;
4. quais formas de automação/computação do método já foram publicadas;
5. quais técnicas formais já foram aplicadas à síntese ou verificação de sistemas sequenciais pneumáticos/fluídicos ou problemas equivalentes;
6. qual lacuna científica pode ser defendida para o presente trabalho.

O objetivo não é apenas “achar referências”, mas produzir uma cadeia de evidência que permita classificar as hipóteses H1–H24 do Bloco 01 como `LIT`, `DEF`, `IMP`, `EXP` ou `OOS`.

---

## 2. Tipo de revisão

Será utilizada uma estratégia em duas fases:

### Fase A — mapeamento sistemático

Objetivo: mapear terminologia, famílias de métodos, autores, períodos, veículos e linhas de pesquisa.

Justificativa: o tema cruza engenharia mecânica, automação, fluidics/pneumatics, lógica de comutação, PLC e métodos formais; a terminologia parece variar historicamente.

### Fase B — revisão sistemática focalizada

Objetivo: analisar em profundidade os estudos diretamente relacionados às perguntas de pesquisa e extrair definições, propriedades, algoritmos, hipóteses, resultados e limitações.

A Fase B será refinada a partir do vocabulário e das famílias identificadas na Fase A.

---

## 3. Referenciais metodológicos e governança da revisão

A revisão será conduzida com base em múltiplos referenciais complementares:

- **Kitchenham & Charters (2007)** — planejamento, execução e documentação de
  revisões sistemáticas em Engenharia de Software;
- **Petersen et al. (2008)** — mapeamento sistemático para classificação e
  estruturação inicial de um campo;
- **ACM SIGSOFT Empirical Standards — Systematic Reviews** — requisitos atuais
  de rastreabilidade, replicabilidade, critérios de seleção, extração,
  codificação, cadeia de evidência e materiais suplementares;
- **PRISMA 2020** — apoio ao relato transparente do fluxo de identificação,
  triagem, elegibilidade e inclusão;
- **GUEST (Kitchenham et al., 2026)** — orientações preliminares específicas
  para uso de GenAI/LLMs em tarefas de revisão sistemática.

### 3.1. Uso de IA generativa

Como ferramentas de IA poderão auxiliar esta pesquisa, o uso deverá ser
explicitamente auditável.

A IA poderá auxiliar em:

- expansão inicial de termos de busca;
- organização de metadados;
- sugestão de candidatos a duplicata;
- criação de formulários/scripts;
- apoio à leitura comparativa;
- checagens secundárias de consistência.

A IA **não poderá autonomamente**:

- decidir a inclusão/exclusão final de um estudo;
- inventar referências ausentes;
- preencher dados não presentes no texto;
- transformar ausência de evidência em evidência de ausência;
- classificar uma hipótese como `LIT` sem verificação humana da fonte;
- declarar originalidade.

Toda decisão de seleção e todo dado usado em uma claim científica deverá ser
verificado contra a fonte original por um pesquisador humano.

Será mantido um log contendo, quando relevante:

- ferramenta/modelo;
- data;
- finalidade;
- etapa da revisão;
- saída utilizada;
- validação humana realizada.

### 3.2. Revisão por mais de um avaliador

O desenho preferencial é de **dois avaliadores humanos independentes** nas
decisões de seleção.

Se recursos impedirem dupla avaliação de 100% dos registros, será adotado no
mínimo:

1. piloto conjunto para calibrar critérios;
2. segunda avaliação independente de uma amostra aleatória pré-definida;
3. segunda avaliação de todos os casos limítrofes/conflitantes;
4. registro das divergências e sua resolução;
5. relato explícito dessa limitação no artigo.

O percentual da amostra e a estatística de concordância serão definidos antes
da triagem definitiva.

### 3.3. Congelamento e mudanças do protocolo

O protocolo será versionado antes da triagem definitiva.

Toda mudança posterior deverá registrar:

- versão;
- data;
- seção alterada;
- justificativa;
- impacto potencial nos resultados.

Critérios não serão alterados retroativamente para favorecer uma conclusão.

### 3.4. Registro externo

Além do histórico Git, será avaliado o registro/arquivamento do protocolo e dos
materiais de pesquisa em um repositório científico persistente (por exemplo,
OSF e/ou Zenodo), antes da submissão do artigo.

---

## 4. Questões de pesquisa da revisão

### RQ1 — origem e definição
Qual é a origem documentada do método e quais nomes foram usados para descrevê-lo?

### RQ2 — domínio
Quais classes de circuitos, atuadores, sensores e sequências são explicitamente cobertas por cada estudo?

### RQ3 — semântica
Como cada estudo representa estado, movimento, etapa, conclusão, simultaneidade, memória e transição?

### RQ4 — segurança/corretude
Quais propriedades de corretude, segurança, ausência de conflito, “pontos perigosos”, causalidade ou equivalentes são definidas ou discutidas?

### RQ5 — simultaneidade e assincronia
Como são tratados movimentos simultâneos, diferenças de velocidade e diferentes ordens de chegada aos fins de curso?

### RQ6 — memória
Como são introduzidas, minimizadas e justificadas variáveis/memórias auxiliares?

### RQ7 — extensões
Multiposição, condições externas, loops, ciclos, PLC e outras extensões aparecem em quais trabalhos e sob quais hipóteses?

### RQ8 — automação
Existem ferramentas, algoritmos computacionais ou métodos de CAD que automatizam total ou parcialmente o procedimento?

### RQ9 — formalização/verificação
Existem modelos formais, provas, model checking, redes de Petri, autômatos, SMT/SAT ou técnicas equivalentes aplicadas ao mesmo problema ou a um problema estruturalmente equivalente?

### RQ10 — otimalidade
Quando um trabalho usa termos como “optimal/optimum/minimal”, qual função-objetivo é realmente minimizada e qual evidência sustenta a afirmação?

### RQ11 — lacuna
Quais combinações de automação + formalização + verificação permanecem sem evidência publicada suficiente?

---

## 5. Estratos de busca

A busca será dividida em três estratos para evitar depender de uma única nomenclatura.

### Estrato S1 — método Karnaugh aplicado a pneumática/fluídica

Conceitos:

- Karnaugh map / Karnaugh matrix / extended Karnaugh;
- pneumatic sequential circuits;
- electro-pneumatic sequential control;
- fluidic sequential circuits;
- fluid logic control;
- ON/OFF pneumatic control.

### Estrato S2 — síntese sequencial fluídica/pneumática em geral

Conceitos:

- synthesis/design of pneumatic sequential control;
- fluid logic sequential control;
- memory logic / steering gates;
- cascade methods;
- sequential pneumatic automation;
- computer-aided design of pneumatic/fluidic control.

Esse estrato serve para localizar precursores, concorrentes e métodos alternativos que podem não mencionar Karnaugh.

### Estrato S3 — verificação formal de sistemas de automação relacionados

Conceitos:

- formal verification / model checking / reachability / safety;
- pneumatic / electro-pneumatic / fluidic / discrete-event control;
- Petri nets / automata / transition systems / SAT / SMT;
- PLC sequential control;
- asynchronous control / race conditions / hazards, quando estruturalmente relevantes.

Este estrato não será usado para fingir que trabalhos genéricos são “o mesmo método”; ele serve para estabelecer o estado da arte de verificação aplicável ao problema.

---

## 6. Strings iniciais

As strings abaixo são sementes. Elas poderão ser adaptadas à sintaxe de cada base, com todas as adaptações registradas.

### Q1
`("Karnaugh map" OR "Karnaugh matrix") AND (pneumatic OR electropneumatic OR fluidic) AND (sequential OR sequence)`

### Q2
`("extended Karnaugh" OR "extended Karnaugh map" OR "extended Karnaugh matrix") AND (pneumatic OR fluidic OR sequential)`

### Q3
`("pneumatic sequential circuit" OR "fluidic-pneumatic control circuit") AND (synthesis OR design OR method)`

### Q4
`("fluid logic" AND sequential AND synthesis)`

### Q5
`("computer-aided" OR automatic OR automated) AND (pneumatic OR fluidic) AND sequential AND (control OR synthesis)`

### Q6
`("formal verification" OR "model checking" OR reachability) AND (pneumatic OR electropneumatic OR "fluid logic")`

### Q7
`("Petri net" OR automata OR "transition system" OR SMT OR SAT) AND (pneumatic OR electropneumatic OR PLC) AND sequential`

### Q8 — português
`("mapa de Karnaugh" OR "matriz de Karnaugh") AND (pneumático OR pneumática OR fluídico OR sequencial)`

### Q9 — espanhol
`("mapa de Karnaugh" OR "matriz de Karnaugh") AND (neumático OR neumática OR fluídico OR secuencial)`

---

## 7. Fontes de busca planejadas

As fontes serão separadas por função para evitar confundir base bibliográfica,
plataforma de editora e mecanismo de descoberta.

### 7.1. Bases/índices principais

Sempre que houver acesso institucional:

- Scopus;
- Web of Science;
- Engineering Village / Compendex;
- IEEE Xplore;
- ACM Digital Library.

### 7.2. Plataformas técnico-científicas complementares

Especialmente importantes para a literatura mecânica/fluídica histórica:

- ASME Digital Collection;
- ScienceDirect;
- SpringerLink;
- SAGE Journals;
- Inderscience;
- IIETA, quando houver estudo candidato identificado.

Essas plataformas complementam, mas não substituem automaticamente, uma busca
em índices multidisciplinares.

### 7.3. Descoberta, citações e metadados

- Google Scholar;
- Crossref;
- OpenAlex, se útil para rastreamento;
- repositórios institucionais;
- catálogos bibliográficos para livros e literatura histórica.

Google Scholar será tratado como mecanismo complementar de descoberta e
snowballing, não como única fonte da revisão.

### 7.4. Literatura não periódica e histórica

Como parte relevante da área antecede a indexação moderna, poderão ser
considerados:

- livros técnicos;
- capítulos;
- proceedings;
- papers técnicos de sociedades profissionais;
- teses/dissertações;
- relatórios técnicos;
- documentação industrial historicamente citada por fontes acadêmicas.

A natureza da fonte será registrada e sua função na argumentação será
diferenciada. Uma fonte histórica poderá estabelecer origem/terminologia sem
receber o mesmo peso que um estudo científico para claims de desempenho.

### 7.5. Intervalo temporal

A busca inicial **não terá limite inferior de ano**.

A razão é histórica: já foram identificados trabalhos relevantes ao menos desde
1970. Um corte temporal precoce poderia eliminar a origem do método e
antecedentes de automação.

A data final da busca será registrada exatamente no dia da execução.

### 7.6. Idiomas

Serão buscados diretamente, no mínimo:

- inglês;
- português;
- espanhol.

Estudos em outros idiomas não serão excluídos apenas pelo idioma se título,
resumo, citações ou metadados indicarem relevância. Nesses casos será tentada
tradução ou obtenção de informação suficiente, com o procedimento registrado.

---

## 8. Estratégias complementares obrigatórias

Após a busca por strings:

1. **backward snowballing** — referências dos estudos centrais;
2. **forward snowballing** — trabalhos que citaram os estudos centrais;
3. busca por autores recorrentes;
4. busca por títulos exatos;
5. busca por DOI;
6. busca de versões em repositórios institucionais;
7. busca de dissertações/teses relevantes;
8. verificação de trabalhos anteriores citados como origem do método.

Cada inclusão obtida por snowballing deverá registrar qual estudo a originou.

---

## 8A. Validação da estratégia de busca por estudos-sentinela

Antes de congelar as strings definitivas, será formado um pequeno conjunto de
estudos-sentinela já conhecidos por serem altamente relevantes.

A estratégia de busca será considerada inadequada se não recuperar uma fração
satisfatória desses estudos por busca automática e/ou por um caminho de
snowballing previamente definido.

O objetivo não é usar os sentinelas como prova de completude, mas evitar strings
obviamente cegas à terminologia histórica da área.

Sentinelas iniciais:

- Cheng & Foster (1972);
- Rohner (1979);
- Siangkok & Chua (1996);
- Santos & Silva (2017);
- Da Silva & Santos (2019);
- Fawzi & Salloom (2023).

O trabalho ASME de Cheng & Foster (1970) será mantido como candidato histórico
importante e deverá ser localizado por referência/catálogo mesmo que não seja
recuperado por busca textual moderna.

---

## 9. Critérios de inclusão

Um trabalho pode ser incluído se satisfizer pelo menos uma das condições:

### I1
Propõe, descreve, modifica ou avalia método de síntese/controle sequencial pneumático, eletropneumático, hidráulico ou fluídico.

### I2
Aplica mapas/matrizes de Karnaugh à obtenção de equações de comando sequencial.

### I3
Discute memória, conflitos, estados, simultaneidade ou segurança em controle sequencial diretamente relevante.

### I4
Apresenta automação/CAD/software para síntese desse tipo de circuito.

### I5
Apresenta técnica formal de verificação diretamente aplicável a controladores sequenciais do mesmo tipo de sistema ou a uma abstração claramente equivalente.

### I6
É uma fonte primária histórica explicitamente citada por trabalhos centrais como origem ou fundamento do método.

---

## 10. Critérios de exclusão

### E1
Uso de Karnaugh apenas para lógica combinacional sem relação com controle sequencial.

### E2
Pneumática apenas como sistema físico, sem síntese/controle lógico relevante.

### E3
Trabalho sobre PLC genérico sem relação demonstrável com o problema estudado.

### E4
Material sem informação suficiente para identificar método, resultados ou fonte.

### E5
Duplicata de versão já incluída; será mantida a versão mais completa/autoritativa, preservando vínculo entre versões.

### E6
Resumo secundário que apenas repete outro trabalho sem contribuição própria, salvo quando necessário para rastrear a história da área.

### E7
Trabalho cujo conteúdo completo não possa ser obtido e cujo resumo seja insuficiente para responder às RQs; poderá permanecer como “identificado, não avaliado”.

---

## 11. Triagem

Antes da triagem definitiva será executado um **piloto de calibração** com uma
amostra de registros. Critérios ambíguos serão esclarecidos antes de continuar.

A triagem será registrada em etapas:

1. identificação;
2. deduplicação;
3. título/resumo;
4. texto completo;
5. inclusão final.

Para cada registro serão preservados:

- fonte/base;
- string;
- data da busca;
- identificador original;
- decisão;
- avaliador;
- motivo quando excluído em texto completo.

Para cada exclusão em texto completo será registrado um motivo específico.

Não será usada a qualidade do periódico/conferência como substituto da
avaliação do conteúdo do estudo.

Quando houver dois avaliadores, divergências serão resolvidas por discussão e
registradas. A concordância será reportada de forma compatível com o desenho
adotado.
---

## 12. Avaliação da qualidade/relevância

Cada estudo incluído receberá avaliação separada de:

### QL1 — clareza do problema
O objetivo e o problema estão definidos?

### QL2 — descrição do método
O procedimento é reproduzível em nível suficiente?

### QL3 — definição do domínio
As hipóteses e limites estão explícitos?

### QL4 — evidência de corretude
Há prova, argumento formal, experimento, exemplos ou apenas afirmação?

### QL5 — evidência de otimalidade
Se há alegação de “ótimo/mínimo”, o critério é definido e demonstrado?

### QL6 — avaliação
Há comparação, validação, estudo de caso, implementação ou experimento?

### QL7 — ameaça à validade
Limitações são discutidas?

A pontuação não será usada mecanicamente para excluir estudos históricos importantes; função histórica e qualidade metodológica serão registradas separadamente.

---

## 13. Formulário de extração de dados

Para cada estudo:

- ID interno;
- referência bibliográfica;
- DOI/identificador;
- ano;
- autores;
- país/instituição;
- tipo de publicação;
- acesso ao texto completo;
- estrato de origem (S1/S2/S3);
- mecanismo de descoberta (string/snowballing/autor/etc.);
- termos usados para nomear o método;
- domínio de aplicação;
- tipo de atuadores;
- representação de sensores/estado;
- representação de sequência;
- simultaneidade;
- diferenças de velocidade/ordem de chegada;
- estados intermediários;
- memória;
- multiposição;
- condições externas;
- loops/ciclos;
- PLC;
- pontos perigosos/conflitos;
- definição de segurança;
- definição de corretude;
- definição de otimalidade;
- algoritmo;
- automação/software;
- modelo formal;
- técnica de verificação;
- propriedades verificadas;
- tipo de evidência;
- limitações;
- relação com H1–H24;
- relação com P1–P31;
- citações-chave em paráfrase;
- observações;
- página/seção exata que sustenta cada dado crítico;
- grau de confiança da extração;
- nome do avaliador;
- uso de IA na extração (sim/não e finalidade);
- confirmação humana da fonte (sim/não).

---

## 14. Cadeia de evidência para as hipóteses H1–H24

Será criada uma matriz:

| Hipótese | Estudos que sustentam | Estudos que contradizem/limitam | Classificação provisória | Decisão |
|---|---|---|---|---|
| H1 | ... | ... | LIT/DEF/IMP/EXP/OOS | ... |

Uma hipótese só será classificada como `LIT` se a literatura realmente a sustentar.

Ausência de discussão na literatura não será interpretada como confirmação.

---

## 15. Cadeia de evidência para originalidade

Cada contribuição potencial será registrada em uma tabela de reivindicações:

| Claim candidato | Evidência anterior encontrada | Diferença do nosso trabalho | Status |
|---|---|---|---|
| Formalização explícita de ... | ... | ... | aberta/possível/refutada |
| Verificação automática de ... | ... | ... | aberta/possível/refutada |
| ... | ... | ... | ... |

A palavra “inédito”, “primeiro”, “novo” ou equivalente não será usada até o fechamento dessa tabela.

---

## 16. Estudos-semente identificados no scoping inicial

Os itens abaixo **não estão automaticamente incluídos**. São candidatos e
sentinelas para testar a estratégia de busca e iniciar snowballing.

### Seed A — síntese sistemática histórica
R. M. H. Cheng; K. Foster.  
**Systematic Method of Designing Fluidic–Pneumatic Control Circuits.**  
Proceedings of the Institution of Mechanical Engineers, 1972, 186(1), 401–408.  
DOI: `10.1177/002034837218600125`.

Importância preliminar: descreve síntese sistemática de controle lógico fluídico
para circuitos pneumáticos sequenciais e afirma produzir um circuito
“optimum”. O significado exato de “optimum” deverá ser analisado, não assumido.

### Seed B — antecedente de CAD
R. M. H. Cheng; K. Foster.  
**A computer-aided design method specially applicable to fluidic–pneumatic
sequential control circuits.**  
ASME Winter Annual Meeting, 1970, paper `70-WA/FLCS-17`.

Importância preliminar: antecedente explícito de CAD citado pelo artigo de 1972.
A fonte primária ainda deverá ser obtida.

### Seed C — referência estruturante
Peter Rohner.  
**Fluid Power Logic Circuit Design: Analysis, Design Methods and Worked
Examples.**  
1979.

Importância preliminar: contém capítulo específico sobre projeto de circuitos
lógicos sequenciais pelo método Karnaugh–Veitch e capítulos sobre circuitos
compostos e controle pneumático de sistemas hidráulicos sequenciais.

### Seed D — automação computacional por Karnaugh–Veitch
S. I. M. Siangkok; P. S. K. Chua.  
**Symbolic pattern manipulation of Karnaugh-Veitch maps for pneumatic
circuits.**  
Artificial Intelligence in Engineering, 1996, 10(1), 71–83.  
DOI: `10.1016/0954-1810(95)00017-8`.

Importância preliminar: descreve manipulação simbólica computacional dos mapas
KV no sistema especialista protótipo **PNEUMAES**, com geração automática de
equações minimizadas para circuitos pneumáticos e limitação declarada de escala.

### Seed E — metodologia moderna de Karnaugh
Adriano A. Santos; António Ferreira da Silva.  
**Methodology for manipulation of Karnaugh maps designing for pneumatic
sequential logic circuits.**  
International Journal of Mechatronics and Automation, 2017, 6(1), 46–54.  
DOI: `10.1504/IJMA.2017.093307`.

Importância preliminar: metodologia de mapas de Karnaugh para circuitos
pneumáticos/eletropneumáticos ON/OFF, uso de memória, minimização e conversão
para PLC. O próprio artigo restringe sua explicação a cilindros com dois
sensores de fim de curso.

### Seed F — automação por sistema especialista/Prolog
António Ferreira da Silva; Adriano A. Santos.  
**A Simulation Tool Using AI Technics and Karnaugh Maps for Learning and
Control Digital Pneumatics.**  
2019 5th Experiment International Conference (exp.at'19).  
DOI: `10.1109/EXPAT.2019.8876488`.

Importância preliminar: descreve o software **ISEPCPC**, desenvolvido em
PROLOG, com técnicas de sistema especialista e metodologia de Karnaugh para
obtenção automática de equações lógicas otimizadas.

### Seed G — método alternativo de automação
Sajaysurya Ganesh; Saravana Kumar Gurunathan.  
**Evolutionary Algorithms for Programming Pneumatic Sequential Circuit
Controllers.**  
Procedia Manufacturing, 2017, 11, 1726–1734.  
DOI: `10.1016/j.promfg.2017.07.299`.

Importância preliminar: programação automática de PLC para sequências
pneumáticas usando algoritmo genético/genetic programming. Não é o mesmo método,
mas é estado da arte relevante para automação da síntese.

### Seed H — múltiplos atuadores / múltiplas sequências
AlZahraa N. Fawzi; Maher Y. Salloom.  
**Developing Multiple-Actuator Pneumatic Circuits Using the Karnaugh Maps
Designing PLC Controlled.**  
Journal Européen des Systèmes Automatisés, 2023, 56(2), 245–252.  
DOI: `10.18280/jesa.560209`.

Importância preliminar: aplica Karnaugh a controle pneumático de múltiplos
atuadores e combina múltiplas sequências, com implementação/simulação orientada
a PLC.

### Seed I — método alternativo com sinais opcionais
**Synthesis of Fluid Logic Networks with Optional Input Signals.**  
ASME paper, 1970.

Importância preliminar: candidato histórico de síntese sequencial com memória e
sinais opcionais, aparentemente eliminando a necessidade de mapas de Karnaugh.
Autoria/metadados deverão ser confirmados na fonte primária antes do uso
bibliográfico.

### Consequência imediata para a originalidade

O scoping já mostra que **“primeira automação computacional do método” não pode
ser usada como claim provisória**, pois há pelo menos um sistema computacional
baseado em Karnaugh–Veitch publicado em 1996 e outro sistema especialista
publicado em 2019.

A possível novidade deverá ser buscada em uma combinação mais específica, como
formalização explícita, tratamento de determinadas classes, verificação de
propriedades, geração de contraexemplos, cobertura sistemática ou outra lacuna
que a revisão completa sustente.

---

## 17. Reprodutibilidade

Serão versionados em `research/02_literatura/`:

- este protocolo;
- strings por base;
- datas de busca;
- arquivos exportados de resultados quando disponíveis;
- tabela mestre de triagem;
- motivos de exclusão;
- formulário de extração;
- matriz H1–H24;
- matriz de claims de originalidade;
- log de snowballing;
- síntese final;
- arquivo de deduplicação;
- conjunto de estudos-sentinela;
- log de decisões de triagem;
- log de uso de IA;
- changelog do protocolo;
- scripts de análise e geração de tabelas.

---

## 17A. Registro obrigatório de cada busca

Cada execução em uma base deverá gerar uma linha no log de buscas contendo:

- base/plataforma;
- data e hora;
- string exatamente executada;
- campos pesquisados (título/resumo/palavras-chave/todos);
- filtros aplicados;
- quantidade de resultados;
- formato exportado;
- nome do arquivo exportado;
- observações/limitações da interface.

Se uma string for adaptada por restrições da base, a adaptação será preservada
literalmente.

---

## 18. Congelamento do protocolo

Antes de iniciar a triagem sistemática:

1. revisar o protocolo;
2. versioná-lo;
3. registrar eventuais mudanças posteriores em um changelog;
4. não alterar critérios retroativamente para favorecer uma conclusão desejada.

Mudanças justificadas são permitidas, desde que registradas com data, motivo e impacto.

---

## 19. Critério de conclusão do Bloco 02

O Bloco 02 estará concluído somente quando houver:

- protocolo versionado;
- strings pilotadas contra os estudos-sentinela;
- buscas executadas e documentadas;
- triagem completa e procedimento de concordância/validação reportado;
- snowballing executado;
- matriz de estudos incluídos;
- matriz H1–H24;
- respostas RQ1–RQ11;
- mapa de trabalhos relacionados;
- tabela de claims de originalidade;
- decisão explícita sobre o escopo científico que seguirá para o Bloco 03;
- registro explícito de como ferramentas de IA foram usadas e validadas.

O Bloco 03 somente começará depois disso.
