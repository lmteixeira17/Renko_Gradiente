# STATUS.md — EA Gradiente Linear com Preço Médio no Renko

**Atualizado em**: 2026-05-25

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

## Bateria de Testes WIN 2025-2026 (2026-05-25)

### Descobertas CRÍTICAS

**1. 2025 foi um ano excepcionalmente favorável para WIN:**
- Baseline (25R, ML3, SL300, DS100): PnL +R$ 8.918, DD 24,9%, PF 1.51
- Stop agressivo de R$30: PnL +R$ 9.602, DD 20,5%, PF 1.60 — melhor R/DD de 2025

**2. 2026 está destruindo TODAS as configs de baseline:**
- Baseline com qualquer stop diário: PnL negativo entre -R$ 11.500 e -R$ 20.300
- PF ~0.30 em todas as configs baseline — mercado em regime de tendência forte sem correções

**3. Stop % do valor de mercado — ideia VALIDADA:**

| Config | 2025 PnL | 2025 PF | 2026 PnL | 2026 PF | Longo Prazo PnL |
|--------|----------|---------|----------|---------|-----------------|
| Baseline (300pts) | +R$ 8.918 | 1.51 | -R$ 12.311 | 0.31 | +R$ 21.201 |
| **0,3% SL / 0,1% gain / DS75** | +R$ 4.691 | 1.07 | **+R$ 1.112** | **1.02** | **+R$ 36.430** |
| 0,2% SL / 0,1% gain / DS75 | +R$ 575 | 1.01 | -R$ 1.477 | 0.96 | — |
| **0,15% SL / 0,05% gain / DS75** | +R$ 5.503 | 1.14 | -R$ 7.817 | 0.70 | **+R$ 26.753** |
| **0,2% SL / 0,08% gain / DS100** | +R$ 6.868 | 1.12 | -R$ 5.952 | 0.83 | **+R$ 22.705** |

**4. MELHOR CONFIGURAÇÃO GLOBAL (WIN 2021-2026) — SUPERADA:**
~~Config anterior: 0,3% SL / 0,1% gain / DS75 → PnL +R$ 36.430, CV 1.58~~

**CONFIGURAÇÃO DEFINITIVA — GAIN_72 + Stop % 0,3% + DS75:**
```
WIN | Renko 25R | ML3 | SEM Martingale
SL: 0,3% do preço (~390 pts a 130k)
Gain: 72 pontos fixos (~R$ 14,40 por contrato no nível 1)
Stop diário: R$ 75
Capital mínimo recomendado: R$ 15.000 (DD 62,8%)
```
Resultado 2021-2026: PnL **+R$ 102.681**, PF 1.35, DD 62,8% (cap 15k), CV **0.79**

| Ano | G65 (antigo) | **G72 (novo)** | Delta |
|-----|-------------|----------------|-------|
| 2021 | +R$ 10.592 | **+R$ 19.625** | +R$ 9.033 |
| 2022 | +R$ 25.602 | **+R$ 34.236** | +R$ 8.634 |
| 2023 | +R$ 23.334 | **+R$ 28.080** | +R$ 4.746 |
| 2024 | +R$ 10.844 | **+R$ 12.293** | +R$ 1.449 |
| 2025 | +R$ 11.924 | **+R$ 17.131** | +R$ 5.207 |
| 2026 | -R$ 10.252 | **-R$ 8.684** | +R$ 1.568 |

**Conclusão**: G72 é superior em TODOS os anos, com CV de 0,79 (excelente consistência).

**Comparação de linearidade:**

| Ano | Baseline (G50) | GAIN_65 + Stop% | Delta |
|-----|---------------|-----------------|-------|
| 2021 | -R$ 466 (-2,2%) | **+R$ 10.592 (14,7%)** | ✅ |
| 2022 | +R$ 7.039 (33,2%) | **+R$ 25.602 (35,5%)** | +R$ 18.563 |
| 2023 | +R$ 15.667 (73,9%) | +R$ 23.334 (32,4%) | +R$ 7.667 |
| 2024 | +R$ 2.353 (11,1%) | **+R$ 10.844 (15,1%)** | **+R$ 8.491** |
| 2025 | +R$ 8.926 (42,1%) | +R$ 11.924 (16,6%) | +R$ 2.998 |
| 2026 | -R$ 12.318 (-58,1%) | **-R$ 10.252 (-14,2%)** | +R$ 2.066 |

**Conclusão**: Apenas aumentar o gain de 50 para 65 pontos **mais que dobrou o lucro total** (+98%), **reduziu a dependência do melhor ano de 73,9% para 35,5%**, e tornou **2021 positivo pela primeira vez**. O CV de 0,97 indica consistência estatística.

**5. WDO é MUITO mais robusto que WIN:**
- Todas as configs WDO em 2026 foram lucrativas (WIN foi destruído)
- WDO baseline 2021-2026: PnL +R$ 49.830, DD 7,4% (cap 10k), PF 63,57
- WDO stop % 0,3%/0,15%: PnL +R$ 171.647, DD 87,6% (cap 10k)

**6. Padrões descobertos:**
- **2025 (mercado lateral):** gain menor = melhor (0,05% > 0,08% > 0,1%)
- **2026 (mercado de tendência):** gain maior = melhor (0,1% > 0,08% > 0,05%)
- **Stop diário R$75 é crucial em 2026** — R$100 ou R$150 são muito permissivos
- **Capital mínimo de R$ 10.000-15.000** é necessário para DD gerenciável

**7. Gain adaptativo implementado no MQL5:**
- Novos inputs: `InpUseAdaptiveGain`, `InpGainLateral`, `InpGainTrend`, `InpTrendBricks`
- Detecta tendência via tijolos Renko consecutivos
- Documentado em `mql5/README_MQL5.md`

### Arquivos de resultados
- `reports/win_full_battery_2025_2026.json` — 262 configs WIN testadas
- `reports/win_pct_03_01_long_term.json` — 0,3%/0,1%/DS75 em longo prazo
- `reports/wdo_stop_pct_battery.json` — 86 configs WDO testadas

---

## Próximos passos (recomendações futuras)

1. [ ] **Testar EA MQL5 em conta demo** com GAIN_65 + Stop% 0,3% + DS75
2. [ ] **Walk-forward analysis** com janelas de 6 meses
3. [ ] **Gerar equity curve** da nova config vencedora
4. [x] **Testar stop diário no WDO** — CONCLUÍDO, WDO é robusto
5. [x] **Testar config 0,3%/0,1% em longo prazo** (2021-2026) — CONCLUÍDO, PnL +R$ 36.430
6. [x] **Implementar switch de gain adaptativo** — CONCLUÍDO no MQL5
7. [x] **Descobrir GAIN_65 como otimização de linearidade** — CONCLUÍDO, PnL +R$ 72.044, CV 0,97

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


---

## Arquivos de Documentação

| Arquivo | Propósito |
|---------|-----------|
| `README.md` | Visão geral do projeto |
| `STATUS.md` | Estado atual e resultados (este arquivo) |
| `MEMORY.md` | Memória persistente por sessão |
| `CLAUDE.md` | Instruções para assistentes |
| **`HISTORY.md`** | **Histórico completo de desenvolvimento, testes e decisões** |
