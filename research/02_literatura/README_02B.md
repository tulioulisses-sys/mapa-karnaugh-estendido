# Bloco 02B — Infraestrutura da revisão bibliográfica

- `log_buscas.csv`: uma linha por execução de busca.
- `estudos_mestre.csv`: cadastro canônico dos estudos.
- `triagem.csv`: decisões de seleção.
- `controle_revisao_bibliografica.xlsx`: espelho operacional dos CSVs.

Regras:
1. CSVs são a fonte versionável principal.
2. Não excluir registros apagando linhas; use os campos de status/decisão.
3. Toda exclusão em texto completo precisa de motivo.
4. Não renumerar IDs existentes.
5. `P02A-WEB-001` registra apenas o piloto Web e não conta como busca formal em base bibliográfica.
