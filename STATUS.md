# STATUS.md — EA Gradiente Linear com Preço Médio no Renko

**Atualizado em**: 2026-05-24

## Estado Atual

Projeto de implementação e validação do EA "Gradiente Linear com Preço Médio no Renko", baseado na especificação técnica do canal No Risk No Gain (Gean Carlos Gorla).

### Fase atual
✅ **Fase 1 — Backtest e Validação** concluída  
✅ **Fase 2 — Port para MQL5** concluída

## O que foi entregue

### Implementação Python
- [x] `src/btp_loader.py` — carrega packets BTP tick-a-tick
- [x] `src/renko.py` — construtor Numba-acelerado de tijolos Renko (Nelogica-style)
- [x] `src/indicators.py` — EMA 21/72, MACD 12/26/9, 2MV Padrão
- [x] `src/ea_gradiente.py` — lógica do EA (gradiente + martingale + preço médio reativo)
- [x] `src/backtest_fast.py` — simulação tick-a-tick otimizada com Numba
- [x] `src/backtest_engine_v2.py` — engine completo de backtest

### Scripts de backtest
- [x] `backtest/run_backtest_v2.py` — backtest por período
- [x] `backtest/run_backtest_annual.py` — backtest anual
- [x] `backtest/validate_quick.py` — validação rápida multi-config
- [x] `backtest/validate_full.py` — validação robusta multi-ano
- [x] `backtest/optimize_params.py` — otimização de parâmetros (grid search)
- [x] `backtest/plot_equity.py` — geração de gráficos de equity
- [x] `backtest/passo1_conservadoras.py` — teste de configs conservadoras
- [x] `backtest/passo2_wdo_corrigido.py` — validação WDO com Renko 10R
- [x] `backtest/passo3_stop_diario.py` — teste de stop financeiro diário

### Port MQL5
- [x] `mql5/EA_Gradiente_Renko.mq5` — EA completo para MetaTrader 5 (~994 linhas)
- [x] `mql5/README_MQL5.md` — documentação de instalação e uso

### Resultados de backtest obtidos
| Arquivo | Descrição |
|---------|-----------|
| `reports/backtest_v2_WIN_2024-01-01_2024-03-31.json` | Backtest Q1 2024 WIN |
| `reports/backtest_annual_WIN_2024-01-01_2024-12-31.json` | Backtest anual 2024 WIN |
| `reports/robustness_quick_2023_2024.json` | Validação rápida 6 configs |
| `reports/robustness_full_2021_2025.json` | Validação robusta 9 configs multi-ano |
| `reports/equity_WIN_2023_2024.png` | Gráfico de equity 2023-2024 |
| `reports/passo2_wdo_corrigido_2021_2025.json` | Resultado WDO 10R 5 anos |
| `reports/equity_WDO_2021_2025.png` | Gráfico de equity WDO 2021-2025 |
| `reports/passo3_stop_diario_2021_2025.json` | Resultado stop diário 5 anos |

## Resultados principais

### WIN — Melhor configuração (2023-2024)
```json
{
  "renko_r": 25,
  "max_levels": 3,
  "martingale": false,
  "price_increment": 100.0,
  "gain_increment": 50.0,
  "stop_loss_pts": 300.0,
  "slippage_pts": 2.0,
  "emolumentos_pct": 0.0001
}
```

**Métricas**:
- Trades: 12.461
- Win Rate: 97,6%
- Profit Factor: 1,33
- Net PnL: **R$ 19.372**
- Max Drawdown: **R$ 1.373 (27,5%)**

### WDO — Melhor configuração (2021-2025)
```json
{
  "renko_r": 10,
  "max_levels": 3,
  "martingale": false,
  "price_increment": 2.0,
  "gain_increment": 0.5,
  "stop_loss_pts": 20.0,
  "slippage_pts": 2.0,
  "emolumentos_pct": 0.0001
}
```

**Métricas**:
- Trades: 58.085
- Win Rate: 90,6%
- Profit Factor: 62,05
- Net PnL: **R$ 63.992**
- Max Drawdown: **R$ 4.782 (19,5%)**

### 🔴 Descoberta CRÍTICA — Stop Diário é ESSENCIAL (Passo 3)

Teste de stop financeiro diário em WIN 25R ML3 SL300 (2021-2025):

| Stop Diário | PnL | DD | R/DD | PF | WR |
|-------------|-----|-----|------|-----|-----|
| **R$ 100** | **R$ 25.111** | **109.3%** | **4.59** | 1.15 | 97.6% |
| R$ 200 | R$ 29.941 | 137.7% | 4.35 | 1.14 | 97.5% |
| R$ 300 | R$ 27.844 | 150.6% | 3.70 | 1.12 | 97.5% |
| R$ 500 | R$ 22.419 | 209.4% | 2.14 | 1.08 | 97.4% |
| R$ 750 | R$ 16.560 | 300.7% | 1.10 | 1.06 | 97.4% |
| R$ 1000 | R$ 11.619 | 385.5% | 0.60 | 1.04 | 97.3% |
| **Sem stop** | **-R$ 2.230** | **625.2%** | **-0.07** | 0.99 | 97.2% |

**Conclusão**: Sem stop diário, o EA é **inviável no longo prazo** (DD 625%, PnL negativo). O stop de R$100/dia oferece o melhor Return/DD ratio (4.59), sendo **65x melhor** que sem stop.

### Alerta crítico — 5 anos
- Em 2021-2025, **TODAS** as configurações WIN conservadoras (ML2, SL apertado) apresentaram drawdown > 1800%
- Martingale é o fator de risco dominante
- Configuração sem Martingale é a única viável para capital de R$ 5.000

## Passos concluídos

### Passo 1: Configurações Conservadoras WIN (2021-2025)
**Status**: ❌ PARADO — evidência suficiente de inviabilidade
- ML2 SL200: PnL -R$ 175.722, DD 3518% — catastrófico
- ML2 SL250: PnL -R$ 98.791, DD 2034% — catastrófico
- ML3 SL200: PnL -R$ 84.690, DD 1817% — catastrófico
- **Conclusão**: Reduzir níveis ou apertar stop piora drasticamente o desempenho de longo prazo

### Passo 2: WDO Corrigido com Renko 10R (2021-2025)
**Status**: ✅ CONCLUÍDO
- Melhor configuração: **WDO 10R | ML3 | SL20 | price_inc=2 | gain_inc=0.5**
- Resultado 5 anos: PnL **R$ 63.992**, DD **19,5%**, PF **62.05**
- **Descoberta**: WDO é mais robusto que WIN com parâmetros corrigidos

### Passo 3: Stop Financeiro Diário (2021-2025)
**Status**: ✅ CONCLUÍDO
- Stop R$100/dia é o vencedor absoluto (R/DD = 4.59)
- Sem stop = catástrofe (DD 625%, PnL negativo)
- Resultado: `reports/passo3_stop_diario_2021_2025.json`

### Passo 4: Port para MQL5
**Status**: ✅ CONCLUÍDO
- EA completo: `mql5/EA_Gradiente_Renko.mq5` (~994 linhas)
- Features: Renko incremental, EMA/MACD/2MV, sinais, gradient levels, limit orders, SL/target/trailing, stop diário, fechamento EOD, OnTester()
- Documentação: `mql5/README_MQL5.md`

## Próximos passos (recomendações futuras)

1. [ ] **Testar EA MQL5 em conta demo** no MetaTrader 5
2. [ ] **Walk-forward analysis** com janelas de 6 meses
3. [ ] **Gerar mais visualizações** (drawdown por mês, distribuição de trades)
4. [ ] **Testar stop diário no WDO** para confirmar robustez

## Dependências

```text
Python 3.11+
numpy
numba
matplotlib
pymupdf (para ler spec do PDF)
```

## Dataset

Backtest utiliza dados tick-a-tick BTP de `C:\HIST_B3\generator_v3` (v3.2):
- WIN: 1.262 dias (2021-04-30 a 2026-05-21)
- WDO: 1.262 dias (2021-04-30 a 2026-05-21)
- ~138 GB, 7,67 bilhões de ticks

## Links

- Especificação: `ea_gradiente_renko.agent.final.pdf`
- Repositório GitHub: `https://github.com/lmteixeira17/Renko_Gradiente`
- Relatórios `_Testes_e_Padroes`:
  - `relatorios/2026-05-24_renko_gradiente_validacao.md`
  - `relatorios/2026-05-24_renko_gradiente_validacao_multi_ano.md`
  - `cadastros/renko_gradiente.md`
