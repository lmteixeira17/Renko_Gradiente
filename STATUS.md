# STATUS.md — EA Gradiente Linear com Preço Médio no Renko

**Atualizado em**: 2026-05-26

## Estado Atual

Projeto de implementação e validação do EA "Gradiente Linear com Preço Médio no Renko", baseado na especificação técnica do canal No Risk No Gain (Gean Carlos Gorla).

### Fase atual
✅ **Fase 1 — Backtest e Validação** concluída
✅ **Fase 2 — Port para MQL5** concluída
✅ **Fase 3 — Auditoria, fix EOD, walk-forward e otimização** concluída (2026-05-26)

---

## 🔴 SESSÃO 2026-05-26 — AUDITORIA + BUG CRÍTICO + WALK-FORWARD + OTIMIZAÇÃO

### Bug crítico de paridade Python ↔ MQL5 (CORRIGIDO)

**Sintoma**: engine Python (`src/backtest_fast.py`) **não fechava posições no EOD**, enquanto MQL5 (`InpCloseAtEndDay=true`) fecha. Posições abertas após `end_time_ms` (16:50) ficavam silenciosamente abandonadas — PnL não contabilizado.

**Impacto medido (G72/SL0,3%/DS75 em 6 anos)**:
- Antes do fix: PnL **R$ 102.587** (otimista)
- Depois do fix: PnL **R$ 89.514** (real, MQL5-parity)
- **Delta: -R$ 13.073 (-12,7%)**

**Daily-stop force-close**: testado mas não muda nada (`daily_stop_loss=R$75` nunca dispara com posição aberta — perdas só são realizadas após fechar trade).

**Fix aplicado**: novos params `force_close_eod` + `force_close_daily_stop` no engine Numba, defaults `False` para compat com scripts legados. **Novos scripts** (walk_forward, optimize_around_g72, plot_equity_g72_fixed) usam `True`.

**Validade dos testes prévios**: viés sistemático otimista de ~13%. Ranking relativo entre configs **se mantém**. Históricos em `reports/win_*` permanecem como referência mas marcados como pré-fix EOD.

### Walk-forward analysis (TRAIN 12m / TEST 6m, 8 janelas)

| Win | Train→Test | Best IS | OOS PnL | OOS PF |
|-----|------------|---------|---------|--------|
| 1 | Q2/21→Q3/22 | G72/SL0.30/DS75 | R$ 14.034 | 1,33 |
| 2 | Q4/21→Q2/23 | G72/SL0.30/DS150 | R$ 16.099 | 1,31 |
| 3 | Q2/22→Q4/23 | G72/SL0.25/DS150 | R$ 15.923 | 1,56 |
| 4 | Q4/22→Q2/24 | G72/SL0.35/DS150 | R$ 4.126 | 1,24 |
| 5 | Q2/23→Q4/24 | G72/SL0.30/DS150 | R$ 4.827 | 1,42 |
| 6 | Q4/23→Q2/25 | G72/SL0.30/DS75 | R$ 1.733 | 1,08 |
| 7 | Q2/24→Q4/25 | G72/SL0.35/DS75 | R$ 10.323 | 1,56 |
| 8 | Q4/24→Q2/26 | **G80**/SL0.35/DS100 | **-R$ 11.067** | **0,72** ⚠️ |

**Total IS R$ 194.387 → OOS R$ 55.999 | Degradação 71% | Max OOS DD R$ 11.778**

**Insights do walk-forward**:
- G72 escolhido em 7/8 janelas IS — **muito robusto**
- DS varia: DS150 em 4 janelas, DS75 em 3, DS100 em 1 — STATUS.md anterior reduzia tudo a DS75
- Window 8 (test = 2026) catastrófica: regime quebrado já documentado
- Sem window 8: OOS = R$ 67k, degradação ~65%
- **DD realista (OOS) é R$ 11.778, não R$ 9.426 (IS)** — capital mínimo precisa subir

### Otimização (grid 96 configs sobre 6 anos, engine corrigida)

**Grid**: gain ∈ {65,70,72,75,80,85} × SL_pct ∈ {0.25,0.30,0.35,0.40}% × DS ∈ {50,75,100,125} = 96 configs.

**TOP 5 por PnL absoluto:**

| Config | PnL | DD | R/DD | PF | CV |
|--------|-----|-----|------|-----|-----|
| 🥇 **G72/SL0.30%/DS100** | **R$ 91.316** | R$ 10.501 | 8,70 | 1,29 | 0,91 |
| G72/SL0.40%/DS125 | R$ 91.293 | R$ 14.517 | 6,29 | 1,28 | 1,02 |
| G72/SL0.40%/DS100 | R$ 90.988 | R$ 13.849 | 6,57 | 1,28 | 1,00 |
| G72/SL0.40%/DS75 | R$ 90.537 | R$ 13.533 | 6,69 | 1,28 | 1,01 |
| G72/SL0.30%/DS75 (baseline) | R$ 89.514 | R$ 10.106 | **8,86** | 1,29 | 0,89 |

**TOP 5 por R/DD (eficiência ajustada):**

| Config | PnL | DD | R/DD | CV |
|--------|-----|-----|------|-----|
| G85/SL0.25%/DS50 (conservador) | R$ 67.488 | R$ 7.073 | **9,54** | 0,88 |
| **G72/SL0.30%/DS75 (baseline)** | **R$ 89.514** | R$ 10.106 | **8,86** | **0,89** |
| G85/SL0.30%/DS100 | R$ 77.741 | R$ 8.857 | 8,78 | 0,87 |
| G72/SL0.30%/DS100 | R$ 91.316 | R$ 10.501 | 8,70 | 0,91 |
| G80/SL0.25%/DS50 | R$ 74.493 | R$ 8.640 | 8,62 | 0,87 |

### 🏆 CONFIGURAÇÃO RECOMENDADA — REVISADA

**Para max PnL** (perfil agressivo, capital R$ 20k+):
```
WIN | Renko 25R | ML3 | SEM Martingale
SL: 0,30% do preço | Gain: 72 pts fixos | Stop diário: R$ 100
```
6 anos: PnL R$ 91.316, DD R$ 10.501, R/DD 8.70, PF 1.29, CV 0.91

**Para max eficiência** (perfil moderado, capital R$ 18k+) — **MANTÉM BASELINE**:
```
WIN | Renko 25R | ML3 | SEM Martingale
SL: 0,30% do preço | Gain: 72 pts fixos | Stop diário: R$ 75
```
6 anos: PnL R$ 89.514, DD R$ 10.106, R/DD 8.86, PF 1.29, CV 0.89

**Para perfil conservador** (capital R$ 12k):
```
WIN | Renko 25R | ML3 | SEM Martingale
SL: 0,25% do preço | Gain: 85 pts fixos | Stop diário: R$ 50
```
6 anos: PnL R$ 67.488, DD R$ 7.073, R/DD 9.54, PF 1.19, CV 0.88

### Expectativa realista pro deploy MQL5

- **PnL ano**: ~R$ 10k–18k (6 anos / 6 = R$ 9-15k/ano, com variação ±50%)
- **DD esperado**: R$ 10-12k (não R$ 5-7k como sugeria backtest pré-fix)
- **Capital mínimo**: **R$ 20.000** (não R$ 15k) para DD gerenciável
- **Anos negativos**: esperar 1-2 anos negativos a cada 6 (regime adverso como 2026)
- **Degradação OOS vs IS**: ~65-70% — otimização promete muito mais do que entrega

### Arquivos novos gerados (2026-05-26)

- `reports/validate_eod_fix.json` — A/B EOD/daily-stop fix
- `reports/walk_forward_win_g72.json` — 8 janelas walk-forward
- `reports/optimize_around_g72.json` — 96 configs otimização
- `reports/compare_real_vs_syn_2026.json` — comparação real vs sintético 2026 (mesmo OHLC)
- `backtest/validate_eod_fix.py` — script A/B
- `backtest/walk_forward.py` — script walk-forward
- `backtest/optimize_around_g72.py` — script otimização
- `backtest/plot_equity_g72_fixed.py` — gera equity curve corrigida
- `backtest/regime_filter_2026.py` — teste de filtros de regime
- `backtest/compare_real_vs_syn_2026.py` — comparação real vs sintético
- `src/backtest_fast.py` — engine com fix EOD (defaults preservam compat)
- `src/backtest_engine_v2.py` — passa params de force_close

---

## 🛑 LIMITAÇÃO CRÍTICA — BIAS DO DATASET SINTÉTICO (2026-05-26)

### Contexto

O dataset BTP em `C:/HIST_B3/generator_v3` (v3.2) usa **dados reais somente para 2026** (86 dias coletados via ProfitDLL). Para 2021-2025, os ticks são **sintéticos**: o gerador `D:/HIST_B3/generator_v3/tools/generate_synthetic_v3_2.py` toma o OHLC M1 real (do MT5) e gera ticks intra-minuto via random walk com microestrutura condicional (calibrada nos 86 dias reais de 2026, 540 classes por hour × range × vol × direction × close_pos).

### Teste decisivo (2026-05-26)

Para medir o viés DESTE EA específico, gerou-se uma versão sintética de cada um dos 79 dias reais de 2026 (mesmo OHLC, ticks sintéticos via v3.2). Rodou-se o EA G72/SL0,30%/DS75 nas duas versões dos mesmos dias.

| Métrica | **Real 2026 (79d)** | **Sintético 2026 (mesmos 79d, mesmo OHLC)** | Delta |
|---------|--------------------|---------------------------------------------|-------|
| PnL total | **-R$ 8.789** | **+R$ 3.968** | **+R$ 12.758** |
| Sinal | LOSS | GAIN | MUDA DE SINAL |
| Trades | 1.559 | **3.095** | **+98,5%** |
| Bricks (alguns dias) | 443 | 769 | **+74%** |
| Delta médio/dia | — | — | +R$ 161 ± R$ 401 |
| Dias com syn > real | — | — | 51/79 (65%) |

### Causa raiz

O gerador respeita o OHLC por minuto (open/high/low/close exatos) **mas o path intra-minuto sintético é mais oscilatório** que o real. Para essa estratégia, isso cria ~2× mais Renko bricks (R=25, brick 120pts) do que existiriam com ticks reais — porque pequenas oscilações sintéticas atravessam o limiar repetidamente onde o tick real cruzaria uma vez só.

Mais bricks → mais sinais → mais trades → mais oportunidade de lucro inflado. Estratégias **path-dependent com Renko grosso + limit orders + martingale** são o pior caso de todos pra esse tipo de microestrutura sintética.

### Implicação BRUTAL pros resultados acumulados

Extrapolando o bias medido (~R$ 161/dia ou ~R$ 40k/ano):

| Período | Reportado (sintético) | Estimativa real | Sinal |
|---------|----------------------|-----------------|-------|
| 2021-2025 (5y × 250 dias) | +R$ 99.524 | ~-R$ 100k (bias estimado -R$ 200k) | NEGATIVO |
| 2026 (real) | -R$ 10.010 | -R$ 10.010 (fato) | NEGATIVO |
| **6 anos total** | **+R$ 89.514** | **~-R$ 110k a +R$ 30k** (faixa ampla) | **PROVAVELMENTE NEGATIVO** |

**Caveat**: o bias foi medido em regime adverso (2026 com tendência forte). Em regimes laterais lucrativos (2022, 2023) o bias pode ser menor — não temos como saber sem ticks reais desses anos.

### Validade do que foi feito até agora

- ✅ **Engine corrigido (EOD fix)**: continua válido — afeta paridade Python↔MQL5 independente de dados
- ✅ **Comparação RELATIVA entre configs**: ainda informativa (G72 > G75 > G80 deve preservar)
- ⚠️ **Níveis absolutos de PnL**: **provavelmente sobre-estimados em ordem de magnitude** para 2021-2025
- ⚠️ **Walk-forward OOS degradation 71%**: já era sinal de alerta — agora explicado em parte pelo bias
- ❌ **Recomendação anterior "deploy com R$ 20k"**: **ANULADA**. Strategy não comprovou viabilidade

### Recomendações concretas (REVISADAS — 2026-05-26)

1. **🛑 NÃO fazer deploy com capital real** baseado nesses backtests
2. **Demo trading MT5 6+ meses** é o ÚNICO teste agora confiável
3. **Acompanhar ratio bricks-MQL5/bricks-Python por dia em demo** — se for ~1.0 (esperado em real), confirma viés do backtest
4. **Considerar abandonar a estratégia** se demo confirmar que não funciona em real
5. **Alternativas**: estratégias menos path-dependent (close-of-bar entry, position trading swing) seriam menos vulneráveis ao viés do gerador
6. **Re-rodar todos os backtests** se um dia houver ticks reais para 2021-2025

### Limitação para futuras sessões

**Qualquer backtest novo usando `C:/HIST_B3/generator_v3` para WIN 2021-2025 está sujeito ao mesmo viés sistemático.** A interpretação correta dos números:

- "PnL R$ X em 6 anos" = `(PnL real 2026) + ~estimado(0.4 × PnL sintético 2021-2025)` (ponto médio)
- Ranking entre configs preserva (G72 > G80)
- Confiar apenas em 2026 real para magnitudes absolutas

---

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
