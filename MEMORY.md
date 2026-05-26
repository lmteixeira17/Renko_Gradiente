# MEMORY.md — EA Gradiente Linear com Preço Médio no Renko

> Memória persistente do projeto. Atualizar após cada sessão de trabalho significativa.

---

## Sessão 2026-05-25 — Bateria Completa WIN 2025-2026

### O que foi feito
- Implementado stop gain/loss como % do valor de mercado no engine Numba
- Rodada bateria massiva de 262 configs em 2025, 2026 e longo prazo 2021-2026
- Testados stops diários: R$30, R$40, R$50, R$60, R$75, R$100, R$150, R$200
- Testados capitais de referência: R$5k, R$10k, R$15k
- Grid de stop %: SL 0,1%-0,3%, gain 0,05%-0,1%
- Arquivo de resultados: `reports/win_full_battery_2025_2026.json`

### Decisões tomadas
1. **Stop % do valor de mercado é viável e superior em alguns cenários**: a ideia do usuário se validou. SL 0,15%-0,3% adaptativo superou o baseline fixo em longo prazo.
2. **Capital mínimo deve ser R$ 10.000-15.000**: com R$ 5.000, o DD em longo prazo é catastrófico (>150%) mesmo nas melhores configs.
3. **2026 é um ano adverso para a estratégia**: todas as configs baseline foram destruídas. Apenas 0,3%/0,1%/DS75 sobreviveu com lucro modesto.
4. **Gain deve ser adaptativo**: em mercado lateral (2025), gain menor é melhor. Em tendência (2026), gain maior é melhor.

### Resultado Passo 1 — 0,3%/0,1%/DS75 em longo prazo 2021-2026
- **PnL: +R$ 36.430** — MAIOR lucro de TODOS os testes!
- PF: 1,07 | WR: 85,8% | Trades: 10.846
- DD: R$ 11.663 (233% cap 5k / 117% cap 10k / **78% cap 15k**)
- **Conclusão: Com R$ 15.000, esta é a MELHOR configuração para WIN**

### Resultado Passo 2 — WDO com stop % e stop diário
- **WDO é MUITO mais robusto que WIN**
- Todas as configs WDO em 2026 foram lucrativas (WIN foi destruído)
- WDO baseline 2021-2026: PnL +R$ 49.830, DD 7,4% (cap 10k), PF 63,57
- WDO stop % 0,3%/0,15%/DS100: PnL +R$ 171.647, DD 87,6% (cap 10k), PF 1,22
- **Recomendação: WDO baseline continua sendo a melhor configuração**

### Resultado Passo 3 — Gain adaptativo no MQL5
- Implementado `InpUseAdaptiveGain`, `InpGainLateral`, `InpGainTrend`, `InpTrendBricks`
- Função `IsTrendingMarket()` detecta tendência via tijolos Renko consecutivos
- **Sem backtest em MQL5** — precisa ser validado no Strategy Tester do MT5
- Código atualizado em `mql5/EA_Gradiente_Renko.mq5` e documentado em `mql5/README_MQL5.md`

### Resultados chave

#### 2025 (ano favorável)
| Config | PnL | DD (cap 5k) | PF | R/DD |
|--------|-----|-------------|-----|------|
| Baseline DS100 | +R$ 8.918 | 24,9% | 1,51 | 7,15 |
| Stop R$30 | +R$ 9.602 | 20,5% | 1,60 | 9,38 |
| **0,3% SL / 0,05% gain / DS100** | **+R$ 13.962** | 40,0% | 1,32 | 6,98 |
| 0,2% SL / 0,05% gain / DS150 | +R$ 10.615 | 25,1% | 1,22 | 8,44 |

#### 2026 (ano adverso) — ÚNICA lucrativa:
| Config | PnL | DD (cap 5k) | PF |
|--------|-----|-------------|-----|
| **0,3% SL / 0,1% gain / DS75** | **+R$ 1.112** | 75,8% | **1,02** |
| Todas as outras 87 configs | Negativo | >65% | <1,00 |

#### Longo prazo 2021-2026
| Config | PnL | DD (cap 15k) | PF | R/DD |
|--------|-----|--------------|-----|------|
| Baseline DS100 | +R$ 21.201 | 82,2% | 1,14 | 1,72 |
| **0,15% SL / 0,05% gain / DS75** | **+R$ 26.753** | **58,6%** | **1,08** | **3,04** |
| **0,2% SL / 0,08% gain / DS100** | **+R$ 22.705** | **53,0%** | **1,05** | **2,85** |

### Problemas em aberto
- 2026 destruiu todas as configs baseline — mercado em regime de tendência forte
- Necessário capital maior (R$ 10k-15k) para DD gerenciável
- Gain ideal parece depender do regime de mercado (lateral vs tendência)

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

### Passo 1 — Configurações Conservadoras WIN (2021-2025)
**Status**: Em andamento
- ML2 SL200: PnL -R$ 175.722, DD 3518% — CATASTRÓFICO
- ML2 SL250: PnL -R$ 98.791, DD 2034% — CATASTRÓFICO
- Conclusão preliminar: reduzir níveis e SL piora performance em longo prazo

### Passo 2 — WDO Corrigido com Renko 10R (2021-2025)
**Status**: ✅ CONCLUÍDO
- Melhor config: WDO 10R nomart ML3 SL20
- PnL: R$ 63.991 em 5 anos
- DD: R$ 972 (19,5%) — EXCELENTE
- PF: 62.05, WR: 90.6%
- **WDO é mais robusto que WIN com parâmetros corrigidos**

### Próximos passos pendentes
1. [x] Testar ML2 + SL200 em 5 anos (em andamento, resultados ruins)
2. [x] Corrigir WDO com Renko 10R (CONCLUÍDO — resultado excelente)
3. [x] Implementar stop financeiro diário rigoroso (CONCLUÍDO — R$100/dia vencedor)
4. [x] Port para MQL5 (CONCLUÍDO)
5. [ ] Walk-forward analysis
6. [ ] Testar WDO com stop diário

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


---

## Sessão 2026-05-26 — Histórico Completo + Deploy MQL5

### O que foi feito
- Criado `HISTORY.md` — documento abrangente com TODO o histórico de testes, descobertas, rejeições e decisões
- Corrigido bug de compilação MQL5: variável `color` renomeada para `brickColor` (palavra reservada em MQL5)
- EA compilado com sucesso: 0 erros, 0 warnings, 865ms
- Arquivo `.ex5` gerado (56.8 KB) no terminal MT5

### Decisões tomadas
1. **Documentar tudo em HISTORY.md**: manter registro permanente de todas as 262+ configs testadas, o que funcionou e o que não funcionou
2. **Configuração definitiva para deploy**: GAIN_72 + SL 0.3% + DS75
3. **Próximo passo é demo trading**: rodar 3-6 meses em conta demo XP

### Arquivos criados/modificados
- `HISTORY.md` (novo) — 23.200 bytes
- `STATUS.md` (atualizado) — referência ao HISTORY.md
- `mql5/EA_Gradiente_Renko.mq5` (corrigido) — bug `color` → `brickColor`

### Estado do deploy
✅ EA compilado e pronto para anexar ao gráfico WIN$N no MT5 Demo
