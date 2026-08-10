# Bloco 01 — Escopo científico e domínio formal (v0.3)

**Projeto:** Mapa de Karnaugh Estendido  
**Status:** documento de trabalho — não é ainda uma afirmação de originalidade nem uma prova de corretude.  
**Baseline de software:** `6ec56aa` (`baseline-pre-formalizacao-2026-08-10`)  
**Branch de pesquisa:** `pesquisa-formalizacao-verificacao`

---

## 1. Objetivo deste bloco

Definir, antes de qualquer nova alteração no motor, **qual problema científico será estudado**, **qual domínio será formalizado**, **quais abstrações serão assumidas** e **quais afirmações ainda não podem ser feitas**.

Este documento separa três coisas que não devem ser confundidas:

1. **domínio do método na literatura** — o que o Método do Mapa de Karnaugh Estendido efetivamente cobre segundo as fontes originais e trabalhos relacionados;
2. **domínio atualmente implementado no software** — o que parser, modelos e motor aceitam hoje;
3. **domínio científico do artigo** — o subconjunto que será formalizado, verificado e avaliado experimentalmente.

A definição final do item 1 depende da revisão bibliográfica do Bloco 02. Portanto, a versão atual é deliberadamente provisória.

---

## 2. Problema científico provisório

Investigar como representar, sintetizar e verificar automaticamente circuitos sequenciais fluídicos descritos por sequências de movimentos, preservando propriedades de causalidade, coerência lógica e segurança no modelo discreto adotado, inclusive na presença de:

- ações simultâneas;
- atuadores com duas ou múltiplas posições monitoradas;
- repetição de comandos;
- memórias auxiliares;
- condições externas;
- estruturas condicionais de repetição;
- diferentes ordens assíncronas de conclusão física.

A formulação definitiva da pergunta de pesquisa somente será fechada após o Bloco 02.

---

## 3. Regra metodológica central

O software existente **não será usado como definição do que é correto**.

A pesquisa deverá manter quatro camadas independentes:

1. **especificação formal do domínio e da semântica**;
2. **verificador independente das propriedades**;
3. **implementação do algoritmo de síntese**;
4. **testes de regressão e gabaritos externos**.

Uma propriedade não será considerada demonstrada apenas porque o motor e seus próprios testes concordam entre si.

---

## 4. Três domínios distintos

### 4.1. \(D_{\text{lit}}\) — domínio respaldado pela literatura

Será definido no Bloco 02 a partir das fontes primárias e trabalhos relacionados.

Questões que precisam ser respondidas:

- qual é a definição original do Método do Mapa de Karnaugh Estendido;
- quais tipos de circuitos e sequências são tratados;
- como são definidas simultaneidade, memórias, pontos perigosos e condições mínimas;
- quais hipóteses físicas são assumidas;
- quais extensões posteriores existem;
- se multiposição, entradas externas e loops pertencem ao método original ou são extensões do presente trabalho;
- quais resultados de corretude/otimalidade já foram demonstrados.

Nenhuma alegação de novidade será feita antes dessa revisão.

### 4.2. \(D_{\text{soft}}\) — domínio do software na baseline

A baseline atualmente declara ou implementa suporte a:

- sequências lineares;
- movimentos simultâneos;
- atuadores tradicionais;
- atuadores multiposição;
- loops condicionais;
- entradas externas;
- estados iniciais configuráveis;
- cálculo de memórias;
- equações booleanas de comando;
- SET, RESET e retenção de memórias;
- detecção/qualificação de pontos perigosos;
- resolução em ciclo contínuo quando o estado final fecha com o inicial.

Restrições atualmente conhecidas incluem:

- um mesmo atuador não pode aparecer duas vezes na mesma etapa simultânea;
- loops aninhados não são aceitos;
- loops sobrepostos não são aceitos;
- um loop válido deve retornar ao estado físico necessário para nova repetição;
- movimentos precisam respeitar a ordem física dos sensores cadastrados.

Este domínio descreve a implementação; ele **não constitui evidência de que todos esses recursos estão corretos**.

### 4.3. \(D_{\text{art}}\) — domínio científico do artigo

Provisoriamente, o artigo estudará sistemas discretos que satisfaçam todas as condições abaixo:

1. número finito de atuadores;
2. cada atuador possui um conjunto finito e ordenado de posições monitoradas;
3. cada movimento possui origem e destino discretos;
4. cada etapa contém uma ou mais ações;
5. ações da mesma etapa são comandadas simultaneamente;
6. a conclusão física das ações pode ocorrer em qualquer ordem compatível com seus trajetos;
7. a transição lógica para a etapa causal seguinte deve respeitar a conclusão requerida da etapa anterior;
8. condições externas, quando presentes, são booleanas;
9. memórias auxiliares são booleanas;
10. o modelo não depende de valores contínuos de tempo para decidir a sequência;
11. falhas físicas de componentes não fazem parte, nesta versão, da semântica nominal.

O \(D_{\text{art}}\) definitivo será a interseção entre o que for teoricamente justificável no \(D_{\text{lit}}\) e o que decidirmos formalizar e verificar.

---

## 5. Abstração física adotada provisoriamente

### 5.1. Atuadores

Seja o conjunto finito de atuadores:

\[
\mathcal{A} = \{A_1, A_2, \ldots, A_n\}.
\]

Cada atuador \(A_i\) possui um conjunto finito e ordenado de posições monitoradas:

\[
P_i = \{p_{i,0}, p_{i,1}, \ldots, p_{i,m_i}\}.
\]

O estado físico nominal do sistema é um vetor:

\[
q = (q_1, q_2, \ldots, q_n),
\]

com:

\[
q_i \in P_i.
\]

Para atuadores binários, \(|P_i|=2\). Atuadores multiposição possuem \(|P_i|>2\).

### 5.2. Movimento

Um movimento é provisoriamente definido por:

\[
\mu = (A_i, p_o, p_d, d),
\]

onde:

- \(A_i\) é o atuador;
- \(p_o\) é a posição de origem;
- \(p_d\) é a posição de destino;
- \(d\in\{+,-\}\) é o sentido.

O movimento é válido somente se o destino estiver no sentido indicado pela ordenação física de \(P_i\).

### 5.3. Etapa

Uma etapa é um conjunto finito de movimentos de atuadores distintos:

\[
G_k = \{\mu_{k,1},\mu_{k,2},\ldots,\mu_{k,r_k}\}.
\]

Se \(r_k=1\), a etapa é simples.

Se \(r_k>1\), a etapa é simultânea.

A ordem textual dos movimentos dentro de \(G_k\) não deve alterar sua semântica.

---

## 6. Semântica de conclusão de uma etapa

Para cada movimento \(\mu\), seja:

\[
C(\mu,q)
\]

o predicado que indica que o atuador correspondente atingiu o destino requerido no estado \(q\).

A conclusão da etapa é definida por:

\[
C(G_k,q)=\bigwedge_{\mu\in G_k} C(\mu,q).
\]

Portanto, **uma etapa simultânea somente está concluída quando todos os seus movimentos atingiram os respectivos destinos**.

Essa definição é independente:

- da ordem em que os movimentos foram escritos;
- da ordem em que os atuadores terminaram;
- da velocidade relativa dos atuadores.

Essa regra será confrontada com a literatura no Bloco 02 antes de ser tratada como definição final do artigo.

---

## 7. Estados intermediários

Uma etapa simultânea não será representada apenas por:

- estado anterior;
- estado final.

O modelo deverá considerar estados parciais em que apenas um subconjunto das ações já concluiu.

Para atuadores multiposição, também devem existir estados em que uma ação ainda está em uma posição monitorada intermediária de seu trajeto.

Se \(R(\mu)\) representa os estados discretos de progresso possíveis de um movimento, o conjunto de estados físicos da execução de uma etapa simultânea deverá ser derivado do produto:

\[
R(G_k)=\prod_{\mu\in G_k}R(\mu),
\]

restrito às combinações fisicamente consistentes.

Isso permite representar qualquer ordem assíncrona de progresso sem atribuir tempos artificiais aos cilindros.

---

## 8. Relações estruturais entre etapas consecutivas

Para uma etapa \(G_k\), seja:

\[
Act(G_k)
\]

o conjunto de atuadores que participam dela.

Para duas etapas consecutivas, a relação entre \(Act(G_k)\) e \(Act(G_{k+1})\) pertence a uma das classes estruturais:

1. igualdade;
2. subconjunto próprio;
3. superconjunto próprio;
4. interseção parcial sem inclusão;
5. conjuntos disjuntos.

Essas classes serão usadas para geração sistemática de entradas. Não serão substituídas por uma lista manual de sequências.

---

## 9. Dimensões formais para geração por classes

A cobertura experimental deverá ser construída pelo produto controlado das seguintes dimensões.

### C1 — cardinalidade da etapa

\[
|G_k| = 1,2,3,\ldots
\]

### C2 — sentidos

Para cada movimento:

\[
d\in\{+,-\}.
\]

Devem ser consideradas todas as classes de combinação de sentidos pertinentes.

### C3 — cardinalidade posicional

- binária;
- multiposição.

### C4 — relação entre conjuntos de atuadores consecutivos

- igualdade;
- subconjunto;
- superconjunto;
- interseção parcial;
- disjunção.

### C5 — posição da simultaneidade

- início;
- interior;
- final;
- fechamento cíclico.

### C6 — tipo da etapa seguinte

- ação física simples;
- ação física simultânea;
- evento de memória;
- decisão condicional;
- fechamento/retorno;
- término nominal da sequência não cíclica.

### C7 — recorrência de atuadores e comandos

- sem repetição;
- repetição do mesmo atuador;
- repetição do mesmo sentido;
- repetição do sentido oposto;
- múltiplas ocorrências da mesma saída física.

### C8 — memórias

- nenhuma;
- uma;
- múltiplas;
- SET;
- RESET;
- retenção;
- transições entre regiões de memória.

### C9 — condições externas

- ausentes;
- presentes e verdadeiras;
- presentes e falsas;
- alteração da condição antes da conclusão física;
- alteração após a conclusão física.

### C10 — topologia de controle

- sequência linear;
- ciclo contínuo;
- loop condicional válido.

### C11 — estado inicial

- posição mínima;
- posição máxima;
- posição intermediária, quando suportada e válida.

### C12 — representação sintática

Será testada separadamente da semântica:

- formas textuais equivalentes;
- espaçamento;
- separadores;
- destinos explícitos;
- normalização de nomes.

A equivalência sintática não deve mudar o comportamento formal.

---

## 10. Propriedades que deverão ser definidas formalmente

Este bloco apenas registra o catálogo. As fórmulas definitivas serão produzidas no Bloco 04.

### P1 — causalidade de avanço

Uma etapa causalmente posterior não pode ser habilitada antes da satisfação das condições necessárias da etapa anterior.

### P2 — barreira de simultaneidade

Se uma etapa possui múltiplas ações, nenhum subconjunto próprio de ações concluídas pode ser confundido com a conclusão total da etapa.

### P3 — vivacidade nominal

Quando todas as precondições formais da etapa seguinte forem satisfeitas, a modelagem não deve impedir indefinidamente seu avanço nominal.

### P4 — independência da ordem de conclusão

A segurança lógica não pode depender de qual atuador fisicamente termina primeiro.

### P5 — invariância por permutação interna

Permutar a ordem textual dos movimentos de uma mesma etapa simultânea deve produzir comportamento semanticamente equivalente.

### P6 — coerência de direção e destino

Todo comando deve corresponder ao destino físico declarado e ao sentido válido.

### P7 — segurança nos estados intermediários

Todos os estados intermediários alcançáveis devem ser considerados na análise de propriedades.

### P8 — exclusão de comandos incompatíveis

Comando e contracomando incompatíveis de um mesmo dispositivo não podem permanecer simultaneamente ativos em um estado no qual isso seja proibido pela semântica.

### P9 — coerência de memória

Eventos de memória não podem antecipar uma causa física que deveriam representar.

### P10 — exclusão SET/RESET

SET e RESET da mesma memória não podem ser simultaneamente verdadeiros em estados em que isso represente contradição lógica.

### P11 — preservação por agregação

A agregação de múltiplas ocorrências de uma mesma saída física não pode introduzir habilitações inexistentes nas ocorrências individuais.

### P12 — fechamento cíclico seguro

A passagem da última etapa à primeira deve respeitar as mesmas relações causais exigidas entre etapas internas.

### P13 — composição com condições externas

Uma condição externa necessária deve ser combinada com as condições físicas e lógicas pertinentes; ela não deve apagar uma precondição física necessária.

### P14 — coerência de loops

Repetição e saída de um loop devem preservar estado físico e condições de transição exigidas pela semântica adotada.

### P15 — invariância por renomeação

Uma bijeção de nomes de atuadores/sensores que preserve a estrutura do problema deve preservar sua solução semântica, salvo pela própria renomeação.

### P16 — determinismo do sintetizador

Para uma mesma entrada formal e mesmos parâmetros, a implementação deve produzir a mesma solução.

**Observação:** determinismo sozinho não implica corretude.

---


## 10A. Revisão crítica: hipóteses que não podem ficar implícitas

A versão v0.1 ainda deixava hipóteses importantes escondidas. Para uma publicação
científica, elas devem ser definidas ou explicitamente deixadas como questões
abertas até a revisão bibliográfica.

### H1 — posição física e sinal de sensor não são a mesma coisa

Não se deve assumir automaticamente que um atuador binário está sempre em
`a0` ou `a1`.

Durante o deslocamento físico, é possível que nenhum fim de curso esteja ativo.
Portanto, uma modelagem mais geral deverá distinguir:

- posição monitorada;
- estado de trânsito;
- sinal lógico produzido por cada sensor.

A literatura deverá determinar quais dessas distinções são necessárias para o
Método do Mapa de Karnaugh Estendido. Até lá, não será assumida uma codificação
one-hot permanente durante todo o movimento.

### H2 — início, progresso e conclusão são eventos distintos

Em uma etapa simultânea, "os comandos foram emitidos simultaneamente" não
implica necessariamente:

- início mecânico exatamente simultâneo;
- velocidades iguais;
- conclusão simultânea.

O modelo formal deverá permitir atrasos relativos sem depender de tempos
numéricos, usando interleavings/ordens parciais quando adequado.

### H3 — conclusões simultâneas reais

O modelo não pode obrigar que apenas uma ação termine por transição.

Duas ou mais ações podem atingir seus sensores no mesmo instante lógico.
A semântica deverá definir se isso é:

- uma transição conjunta; ou
- um conjunto de interleavings equivalentes.

A escolha deverá preservar as propriedades de segurança.

### H4 — semântica das saídas e das válvulas

É necessário distinguir:

- comando lógico calculado;
- energização física de uma bobina;
- estado de uma válvula;
- retenção mecânica/pneumática/elétrica da válvula;
- término do movimento do atuador.

Uma equação booleana não pode ser interpretada automaticamente como "posição
física da válvula" sem que a tecnologia de atuação correspondente esteja
declarada.

### H5 — desligamento de um comando dentro de uma etapa simultânea

Quando uma das ações de uma etapa simultânea termina antes das demais, deve ser
formalizado se o seu comando:

- permanece ativo até o fim da etapa;
- pode ser removido ao atingir o próprio destino;
- é retido fisicamente mesmo após a expressão lógica deixar de ser verdadeira.

Essa escolha afeta comando/contracomando e será tratada explicitamente.

### H6 — semântica temporal das memórias

Memórias introduzem microeventos lógicos.

Deve ser definido:

- quando SET/RESET é avaliado;
- se a mudança é atômica;
- se uma mudança de memória pode habilitar outra mudança no mesmo macroestado;
- se existe prioridade entre evento físico, memória e comando;
- como impedir cascatas lógicas ambíguas.

### H7 — sinal de partida e reinicialização

O sinal de partida `S` precisa de semântica própria:

- nível ou borda;
- duração mínima;
- comportamento se permanecer ativo;
- comportamento ao final da sequência;
- relação com ciclo contínuo;
- inicialização das memórias;
- reinício após parada.

### H8 — ambiente e entradas externas

Uma entrada externa não será tratada como constante por conveniência.

O ambiente deverá possuir uma semântica declarada. Entre as possibilidades a
serem avaliadas:

- entrada pode mudar em qualquer transição;
- entrada só é amostrada em pontos definidos;
- entrada deve permanecer estável durante determinada decisão.

Propriedades de segurança devem resistir às variações permitidas pelo modelo.

### H9 — justiça para propriedades de vivacidade

Sem uma hipótese de justiça (fairness), não é possível afirmar genericamente
que um movimento "eventualmente" termina: um ambiente nondeterminístico poderia
simplesmente nunca produzir sua conclusão.

Logo:

- propriedades de segurança deverão ser independentes de fairness quando
  possível;
- propriedades de vivacidade deverão declarar explicitamente suas hipóteses de
  progresso físico/ambiental.

### H10 — percurso de atuadores multiposição

Para um movimento entre posições não adjacentes, deverá ser definido se:

- sensores intermediários são necessariamente atravessados;
- o sinal de cada sensor intermediário pode ficar verdadeiro durante a passagem;
- a passagem é tratada como evento observável;
- uma etapa futura pode usar esses sinais.

O verificador deve modelar o caminho físico permitido, e não somente origem e
destino.

### H11 — equivalência em todos os estados versus estados alcançáveis

Duas expressões booleanas podem diferir em combinações fisicamente
inalcançáveis e ainda produzir o mesmo comportamento do sistema.

Serão distinguidas:

1. equivalência booleana global;
2. equivalência restrita aos estados alcançáveis;
3. equivalência comportamental das transições.

O artigo deverá dizer explicitamente qual noção é usada em cada comparação.

### H12 — atomicidade da transição de etapa

Deve ser definido se a passagem de uma etapa para outra é instantânea no modelo
ou se existem microestados em que:

- a etapa anterior já terminou;
- uma memória ainda não mudou;
- a próxima saída ainda não foi comandada.

Isso é especialmente importante para provas de causalidade.

### H13 — conflitos físicos não representados pela lógica sequencial

Mesmo que duas ações sejam logicamente permitidas, elas podem ser fisicamente
incompatíveis por colisão, carga, pressão ou geometria.

A menos que tais restrições sejam fornecidas como parte da especificação, o
artigo não deverá afirmar ausência de conflitos mecânicos.

### H14 — limite teórico versus limite da implementação

O domínio matemático poderá ser definido para qualquer sistema finito, enquanto
a implementação pode possuir limites práticos de:

- número de atuadores;
- número de posições;
- número de memórias;
- tamanho da sequência;
- tempo de busca;
- memória computacional.

Esses limites devem ser reportados separadamente.

### H15 — identidade de ocorrência versus identidade de saída física

Movimentos repetidos como ocorrências distintas de `E+` devem permanecer
distinguíveis durante a síntese e verificação, ainda que sejam agregados depois
na mesma saída física.

A agregação somente é válida se preservar o comportamento das ocorrências.

### H16 — estados inválidos e estados impossíveis

O espaço de estados booleanos bruto pode conter combinações que não representam
nenhum estado físico admissível.

O verificador deverá distinguir:

- estados sintaticamente representáveis;
- estados fisicamente admissíveis no modelo;
- estados alcançáveis a partir da condição inicial.

As propriedades principais serão verificadas sobre o conjunto apropriado, que
deve ser declarado em cada caso.

---

## 10B. Novas dimensões de geração por classes

Além de C1–C12, a geração sistemática deverá considerar:

### C13 — estado sensorial durante movimento

- sensor de origem ativo;
- nenhum sensor de posição ativo;
- sensor intermediário ativo;
- sensor de destino ativo.

Somente combinações permitidas pela semântica física serão geradas.

### C14 — ordem parcial de eventos

- conclusões estritamente ordenadas;
- duas ou mais conclusões no mesmo passo lógico;
- diferentes interleavings equivalentes.

### C15 — semântica de saída

- comando momentâneo;
- comando mantido;
- retenção por memória/estado de válvula, quando fizer parte do modelo adotado.

### C16 — evolução do ambiente

- entrada externa estável;
- alteração antes da conclusão;
- alteração coincidente com a conclusão;
- alteração depois da conclusão.

### C17 — microeventos lógicos

- sem memória;
- memória entre duas etapas físicas;
- mais de um microevento lógico;
- fechamento lógico antes de nova ação física.

### C18 — partida e reinício

- partida por nível/borda conforme a semântica adotada;
- partida mantida;
- novo pulso;
- reinício após término;
- ciclo contínuo.

### C19 — caminho multiposição

- movimento adjacente;
- movimento que atravessa uma posição intermediária;
- movimento que atravessa múltiplas posições;
- retorno equivalente.

### C20 — classe do estado analisado

- admissível mas inalcançável;
- alcançável;
- inválido segundo invariantes físicos.

---

## 10C. Propriedades adicionais

As seguintes propriedades devem ser acrescentadas ao catálogo:

### P17 — coerência sensor–posição

Os sinais de sensores usados pelas equações devem ser compatíveis com o estado
físico/sensorial permitido pela semântica.

### P18 — segurança sob todas as ordens parciais permitidas

A propriedade de segurança deve valer para toda ordem de início/progresso/
conclusão permitida pelo modelo, inclusive empates.

### P19 — ausência de antecipação por microevento

Nenhum evento de memória ou condição lógica intermediária pode fazer uma etapa
física futura ultrapassar sua barreira causal.

### P20 — robustez às entradas externas permitidas

Nenhuma evolução do ambiente permitida pela especificação pode remover uma
precondição física necessária de segurança.

### P21 — coerência de partida/reinício

O sinal de partida não pode causar reentrada ou repetição não especificada.

### P22 — preservação da semântica de ocorrências

A transformação de ocorrências lógicas em equações agregadas por saída física
deve preservar o comportamento sobre os estados relevantes.

### P23 — fechamento de microeventos

Se a semântica permitir cascatas lógicas instantâneas, seu fechamento deve ser
determinístico ou formalmente confluente, e não produzir ciclo lógico
instantâneo indefinido.

### P24 — propriedade de progresso sob hipótese explícita

Sob as hipóteses de fairness/progresso declaradas, uma etapa habilitada e sem
falha física não deve permanecer indefinidamente sem progresso por uma
deficiência puramente lógica do sintetizador.

---

## 10D. Estrutura mínima do futuro modelo de transição

A especificação formal deverá, no mínimo, separar o estado global em componentes
como:

\[
s = (q,\sigma,u,m,c,\ell),
\]

onde, provisoriamente:

- \(q\): estado/progresso físico dos atuadores;
- \(\sigma\): sinais dos sensores;
- \(u\): entradas externas e partida;
- \(m\): estado das memórias auxiliares;
- \(c\): estado lógico/físico dos comandos, conforme a semântica adotada;
- \(\ell\): localização/estado de controle da sequência.

Essa decomposição é provisória e será revisada após a literatura. O objetivo é
evitar que posição física, sensor, comando, memória e etapa sejam comprimidos
em uma única variável conceitual.

---

## 10E. Regra de rastreabilidade científica

Toda hipótese usada no artigo deverá receber uma classificação:

- **LIT** — sustentada diretamente pela literatura;
- **DEF** — definição introduzida explicitamente no trabalho;
- **IMP** — limitação/decisão da implementação;
- **EXP** — hipótese utilizada apenas em determinado experimento;
- **OOS** — fora do escopo.

Nenhuma hipótese poderá permanecer apenas implícita no código.



## 10F. Segunda auditoria crítica: hipóteses adicionais

A auditoria final do escopo identificou outras hipóteses que também não podem
permanecer implícitas.

### H17 — exclusividade e sobreposição de sensores

Não se deve assumir, sem justificativa, que exatamente um sensor de posição de
um atuador esteja ativo em todo instante.

Dependendo da tecnologia e geometria de detecção, podem existir:

- regiões em que nenhum sensor esteja ativo;
- regiões de sobreposição em que dois sensores estejam ativos;
- histerese;
- sinais transitórios na passagem.

O domínio do artigo deverá declarar explicitamente quais combinações são
fisicamente admissíveis. Se o modelo assumir sensores mutuamente exclusivos,
isso será uma hipótese formal, não uma consequência automática da notação.

### H18 — semântica assíncrona versus ciclo de varredura

O comportamento lógico depende da tecnologia de implementação.

Deve ser explicitado se as equações são interpretadas como:

- lógica combinacional/assíncrona continuamente avaliada;
- circuito de relés;
- lógica pneumática;
- PLC com ciclo de varredura;
- outro mecanismo discreto.

Resultados demonstrados para uma semântica não serão automaticamente
generalizados para outra.

### H19 — atrasos de propagação, corridas e hazards lógicos

A avaliação booleana em regime estável não representa automaticamente atrasos
de propagação dos elementos lógicos.

O artigo deverá declarar se:

- hazards estáticos/dinâmicos são modelados;
- corridas decorrentes de atrasos lógicos são modeladas;
- o modelo assume transições atômicas/idealizadas;
- ou tais fenômenos ficam fora do escopo.

Essa questão é distinta de diferenças de velocidade dos atuadores.

### H20 — separação entre planta, controlador e ambiente

O sistema formal deverá distinguir pelo menos:

- **planta**: evolução física/sensorial dos atuadores;
- **controlador**: equações, memórias e lógica de sequência;
- **ambiente**: partida e entradas externas.

A segurança será analisada sobre a composição fechada dessas partes, sob as
hipóteses declaradas para cada uma.

### H21 — nondeterminismo adversarial para segurança

Quando várias evoluções físicas/ambientais forem permitidas, propriedades de
segurança deverão ser verificadas para **todas** as escolhas permitidas.

Não será permitido validar segurança selecionando apenas uma ordem favorável de
eventos.

### H22 — estado inicial único versus conjunto de estados iniciais

A baseline permite informar um estado inicial concreto, mas o artigo deverá
distinguir:

- verificação a partir de um estado inicial conhecido;
- verificação a partir de um conjunto de estados iniciais admissíveis;
- inicialização de memórias e controlador.

Se incerteza inicial não for tratada, isso deverá ser declarado como limite.

### H23 — estado terminal de sequências não cíclicas

Para sequências não contínuas, deve ser formalizado o que ocorre após a última
etapa:

- quais comandos permanecem ativos;
- quais são removidos;
- como ficam as memórias;
- se uma nova partida é aceita;
- se existe estado terminal absorvente.

Sem isso, propriedades de reinício podem ficar ambíguas.

### H24 — ausência de explosão lógica instantânea/Zeno discreto

Se o modelo admitir microeventos lógicos sem avanço físico, deve ser excluída ou
detectada a possibilidade de uma sequência infinita de mudanças internas em
tempo lógico zero.

Ciclos instantâneos de memória/comando deverão ser:

- impossíveis por construção;
- detectados pelo verificador; ou
- formalmente resolvidos por uma semântica de ponto fixo bem definida.

---

## 10G. Dimensões adicionais de geração por classes

### C21 — padrão de ativação dos sensores

Conforme a semântica adotada:

- exatamente um sensor ativo;
- nenhum sensor ativo em trânsito;
- sobreposição permitida;
- combinações explicitamente proibidas.

### C22 — semântica de execução lógica

- assíncrona/contínua idealizada;
- síncrona por passo lógico;
- ciclo de varredura, caso seja incluído no domínio.

Classes não pertencentes ao domínio final serão registradas como fora do escopo,
e não silenciosamente ignoradas.

### C23 — conjunto de estados iniciais

- um estado inicial único;
- múltiplos estados iniciais admissíveis, se suportados;
- diferentes inicializações de memória.

### C24 — terminalidade

- sequência linear terminada;
- reinício;
- ciclo contínuo;
- retorno por loop.

### C25 — nível de abstração temporal

- somente ordem de eventos;
- coincidência lógica de eventos;
- atrasos discretizados, somente se incorporados formalmente.

---

## 10H. Propriedades adicionais

### P25 — ausência de deadlock lógico indevido

Sob as hipóteses de progresso declaradas, o controlador não deve introduzir um
estado alcançável não terminal no qual nenhuma transição permitida possa
prosseguir apesar de as condições físicas necessárias poderem ser satisfeitas.

### P26 — ausência de livelock lógico indevido

O controlador não deve permanecer indefinidamente em uma sequência de
microeventos internos sem progresso físico quando tal comportamento não fizer
parte da especificação.

### P27 — segurança universal sob nondeterminismo

Toda propriedade de segurança deverá valer para cada trajetória permitida pela
planta e pelo ambiente, não apenas para uma trajetória selecionada.

### P28 — conformidade de representação

A transformação:

\[
\text{entrada textual} \rightarrow \text{modelo interno formal}
\]

deve preservar a semântica da entrada válida.

Formas textuais semanticamente equivalentes deverão resultar em modelos
equivalentes segundo o critério adotado.

### P29 — conformidade implementação–especificação

As equações e eventos produzidos pelo sintetizador deverão ser verificáveis
contra a especificação independente. A concordância com testes históricos não
substitui essa propriedade.

### P30 — terminalidade coerente

Uma sequência não cíclica deve atingir um comportamento terminal definido, sem
reativação espontânea de etapas anteriores.

### P31 — ausência de ciclo lógico instantâneo não especificado

Não deve existir trajetória infinita composta apenas por microeventos lógicos
instantâneos, salvo se tal semântica tiver sido explicitamente especificada e
demonstrada consistente.

---

## 10I. Níveis de evidência e limites das alegações

Para evitar conclusões excessivas, toda afirmação do artigo deverá ser associada
ao tipo de evidência que realmente a sustenta.

### E1 — definição

Uma propriedade pode decorrer diretamente de uma definição adotada, mas isso
não demonstra que a implementação a respeita.

### E2 — prova matemática paramétrica

Uma demonstração válida para uma classe parametrizada pode sustentar uma
afirmação não limitada a tamanhos específicos, desde que todas as hipóteses
estejam declaradas.

### E3 — model checking exaustivo finito

Demonstra a propriedade para o modelo e limites explorados.

### E4 — bounded model checking / SMT limitado

`UNSAT` significa ausência de contraexemplo **dentro da codificação e dos
limites informados**. Não será apresentado como prova irrestrita.

### E5 — teste por propriedades / geração combinatória

Fornece evidência sobre as instâncias geradas, mas não equivale automaticamente
a uma prova universal.

### E6 — testes de mutação

Demonstram poder de detecção de determinadas classes de defeitos, mas não
provam ausência de defeitos não mutados.

### E7 — gabaritos externos

Demonstram concordância com referências selecionadas, não corretude universal.

### E8 — experimento físico

Se realizado, demonstra comportamento nas condições experimentais especificadas
e não substitui a prova sobre todo o domínio formal.

O artigo deverá evitar converter evidência limitada em alegação universal.

---

## 10J. Regra para alegações de cobertura

A frase "cobre todas as classes" somente poderá ser usada se:

1. a partição de classes estiver formalmente definida;
2. cada classe pertencente ao domínio tiver critério de inclusão/exclusão;
3. as combinações entre dimensões tiverem estratégia de cobertura documentada;
4. o limite de cardinalidade, quando houver, estiver explícito;
5. propriedades universais não forem inferidas apenas de amostragem aleatória.

Quando a exploração for limitada, a redação deverá indicar os limites, por
exemplo:

> "A propriedade foi verificada exaustivamente para todas as instâncias do
> domínio parametrizado até os limites \(n\), \(m\) e \(k\) definidos no
> experimento."

Quando houver prova paramétrica, a afirmação poderá ser mais geral, de acordo
com as hipóteses demonstradas.

---

## 10K. Critério mínimo para o futuro verificador

O verificador independente deverá possuir uma especificação própria e testes
próprios. Seu resultado não será tratado como infalível apenas por ser
"independente".

Sempre que viável, sua confiabilidade será sustentada por uma combinação de:

- construção simples e auditável;
- propriedades locais demonstráveis;
- comparação com pequenos modelos enumerados manualmente ou por outro
  formalismo;
- mutation testing;
- cross-check com solver/model checker distinto em subconjuntos;
- contraexemplos reproduzíveis.

A cadeia científica desejada é:

\[
\text{especificação}
\rightarrow
\text{modelo de referência}
\rightarrow
\text{verificador}
\rightarrow
\text{sintetizador}
\rightarrow
\text{clientes/API/app}.
\]

Cada seta deverá ter um mecanismo explícito de validação.


## 11. Segurança lógica não é segurança funcional industrial completa

O artigo deverá evitar a afirmação genérica de que o software "garante a segurança de uma máquina real".

O modelo formal nominal, nesta versão, não inclui automaticamente:

- sensor travado;
- sensor ausente;
- válvula emperrada;
- vazamento;
- queda de pressão;
- ruptura mecânica;
- atraso contínuo com valor temporal;
- bouncing/ruído de contato;
- falha elétrica;
- perda de alimentação;
- falhas simultâneas;
- requisitos de SIL/PL ou certificação funcional.

As propriedades demonstradas deverão sempre ser qualificadas como propriedades **dentro do modelo discreto formal definido no artigo**.

Uma extensão futura poderá estudar modelos explícitos de falha.

---

## 12. Corretude, segurança, completude e otimalidade são afirmações diferentes

O artigo deverá separar pelo menos quatro questões:

### 12.1. Corretude semântica

A solução produzida representa a sequência especificada?

### 12.2. Segurança lógica no modelo

Existem estados alcançáveis que violam os invariantes definidos?

### 12.3. Completude do algoritmo

Para toda entrada pertencente ao domínio declarado para a qual existe solução, o algoritmo encontra uma solução?

Essa afirmação somente poderá ser feita se for demonstrada.

### 12.4. Otimalidade

A solução possui número mínimo de memórias, número mínimo de contatos, forma booleana mínima ou outro critério?

Cada tipo de otimalidade exige definição e demonstração próprias.

O uso da palavra "ótimo" no artigo dependerá estritamente do que a literatura e os resultados permitirem provar.

---

## 13. Critério de equivalência

Comparações científicas não deverão depender da ordem textual dos fatores de uma expressão.

Quando aplicável, duas equações serão consideradas equivalentes se representarem a mesma função booleana sobre o domínio de variáveis relevante.

Analogamente, duas sequências obtidas por renomeação estrutural ou permutação interna de uma etapa simultânea poderão ser comparadas por equivalência semântica, e não apenas por igualdade de strings.

---

## 14. Princípio do verificador independente

O verificador a ser construído não poderá usar a função de síntese do motor para determinar o resultado esperado.

Ele deverá receber uma representação formal do projeto e:

1. construir estados físicos possíveis;
2. construir transições permitidas pela semântica;
3. identificar estados alcançáveis;
4. avaliar propriedades sobre esses estados e transições;
5. produzir um contraexemplo quando uma propriedade for violada.

O motor será então avaliado contra essa referência independente.

---

## 15. Classes versus exemplos

Exemplos concretos terão somente três funções:

1. ilustração didática;
2. regressão de defeitos conhecidos;
3. comparação com gabaritos externos.

Eles **não serão a definição da cobertura**.

A cobertura principal será especificada em termos das classes C1–C25, suas combinações relevantes e propriedades P1–P31.

---

## 16. Evidência experimental planejada

A avaliação deverá registrar, no mínimo:

- versão exata do código;
- versão do ambiente;
- classes geradas;
- quantidade de instâncias;
- quantidade de estados alcançáveis;
- quantidade de transições;
- propriedades avaliadas;
- contraexemplos encontrados;
- tempo e memória de execução;
- cobertura de mutações;
- resultados dos gabaritos externos;
- limites em que a explosão de estados se torna relevante.

Os scripts usados para gerar os resultados deverão ser versionados.

---

## 17. Testes de mutação planejados

A validação deverá introduzir deliberadamente defeitos representativos de classes de falha, como:

- remover um fator necessário de conclusão;
- substituir conjunção por disjunção;
- ignorar estados intermediários;
- usar sensor de destino incorreto;
- antecipar SET/RESET;
- remover condição externa necessária;
- introduzir ativação simultânea de comando e contracomando;
- quebrar o fechamento de ciclo;
- agregar incorretamente ocorrências repetidas.

Um verificador que não detecte uma mutação relevante não será considerado suficiente para aquela propriedade.

---

## 18. Perguntas que o Bloco 02 precisa responder

Antes de transformar este documento em especificação científica definitiva, a revisão bibliográfica deverá responder:

1. Qual é a fonte primária do Método do Mapa de Karnaugh Estendido?
2. Quais definições formais já existem?
3. O termo "ponto perigoso" possui definição formal publicada?
4. Há prova conhecida de corretude, completude ou otimalidade?
5. Como a literatura trata movimentos simultâneos?
6. Como trata diferenças de velocidade/ordem de chegada?
7. Como trata memória?
8. Multiposição faz parte do método original ou é extensão?
9. Loops condicionais fazem parte do método original ou são extensão?
10. Entradas externas fazem parte do método original ou são extensão?
11. Existem implementações automatizadas publicadas?
12. Existem trabalhos usando redes de Petri, autômatos, model checking, SMT ou outros métodos formais para problema equivalente?
13. Qual nomenclatura internacional é usada para essa classe de circuitos?
14. Quais métricas são usadas para comparar métodos de síntese?
15. Quais afirmações de novidade seriam defensáveis?
16. Qual semântica temporal/lógica (assíncrona, relés, PLC, pneumática) é assumida pelas fontes primárias e pelos trabalhos relacionados?
17. A literatura trata hazards de propagação, corridas lógicas, sobreposição de sensores ou apenas estados estáveis?

---

## 19. Afirmações proibidas neste estágio

Até os blocos correspondentes serem concluídos, não escrever no artigo que:

- o algoritmo é "formalmente correto";
- o algoritmo é "completo";
- o algoritmo é "ótimo";
- o algoritmo cobre "qualquer circuito";
- o método desenvolvido é "inédito";
- é a "primeira implementação";
- o sistema "garante segurança industrial";
- todos os estados físicos reais foram modelados.

Essas frases somente poderão aparecer se houver sustentação explícita.

---

## 20. Critério de conclusão do Bloco 01

O Bloco 01 estará encerrado quando:

- este documento estiver versionado no repositório;
- o domínio provisório estiver aceito como ponto de partida;
- estiver clara a separação entre literatura, software e artigo;
- nenhuma correção do motor tiver sido feita antes da definição das propriedades;
- as questões abertas para a revisão bibliográfica estiverem registradas;
- as hipóteses H1–H24 estiverem classificadas como questões a confirmar, definições explícitas ou fora do escopo;
- nenhuma hipótese física importante depender apenas do comportamento atual do código.

O próximo bloco será:

**Bloco 02 — revisão bibliográfica sistematizada e delimitação da contribuição científica.**
