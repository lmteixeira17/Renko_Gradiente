# MEMORY.md — EA Gradiente Linear com Preço Médio no Renko

> Memória persistente do projeto. Atualizar após cada sessão de trabalho significativa.

---

## Sessão 2026-05-24

### O que foi feito
- Criada estrutura completa do projeto em Python
- Implementado backtest engine otimizado com Numba
- Rodados backtests multi-ano (2021-2025) para WIN e WDO
- Gerados relatórios e gráficos de equity
- Criados STATUS.md, CLAUDE.md, MEMORY.md
- Inicializado repositório git

### Decisões tomadas
1. **Sem Martingale para deploy**: apesar de Martingale gerar lucros maiores, o drawdown em 5 anos é catastrófico (>200%). A configuração sem Martingale (ML3, SL300) é a única viável.
2. **WIN prioridade sobre WDO**: WDO apresentou queda de volatilidade em 2024+, exigindo Renko menor (10R). WIN é mais estável para backtest.
3. **Engine Numba**: processa ~6M ticks/dia em ~0.1s após warmup. Performance aceitável para validação.

### Resultados chave
| Config | Período | PnL | DD | PF |
|--------|---------|-----|-----|-----|
| WIN 25R nomart ML3 SL300 | 2023-2024 | R$ 19.372 | 27,5% | 1,33 |
| WIN 25R nomart ML3 SL300 | 2021-2025 | R$ 15.106 | 241% | 1,06 |
| WIN 25R mart ML3 SL300 | 2021-2025 | R$ 94.844 | 237% | 1,32 |

### Problemas em aberto
- WDO com Renko 15R tem viés de seleção (apenas dias voláteis geram sinais)
- Profit factor marginal (1,06 em 5 anos) — pouca margem para custos reais
- Em 5 anos, drawdown explode para >200% em todas as configurações testadas

### Próximos passos pendentes
1. Testar ML2 + SL200 em 5 anos
2. Corrigir WDO com Renko 10R
3. Implementar stop financeiro diário rigoroso
4. Port para MQL5 ou NTSL
5. Walk-forward analysis

### Arquivos importantes gerados
- `reports/robustness_full_2021_2025.json` — resultado completo multi-ano
- `reports/equity_WIN_2023_2024.png` — curva de equity da melhor config
- `reports/backtest_annual_WIN_2024-01-01_2024-12-31.json` — backtest anual

### Padrões de nomeação
- Relatórios: `reports/YYYY-MM-DD_nome-do-ea_validacao.md`
- Backtests: `reports/backtest_ano_ativo_inicio_fim.json`
- Gráficos: `reports/equity_ATIVO_ANO.png`

### Contatos e dependências
- Dataset BTP: `C:\HIST_B3\generator_v3` (não modificar)
- Especificação: `ea_gradiente_renko.agent.final.pdf`
- Central de acompanhamento: `_Testes_e_Padroes`
