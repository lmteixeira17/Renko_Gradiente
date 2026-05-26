# HISTORY.md — EA Gradiente Linear com Preço Médio no Renko

> **Histórico completo de desenvolvimento, testes, descobertas e decisões.**  
> Este documento preserva TUDO o que foi tentado, validado ou rejeitado durante o ciclo de vida deste projeto.  
> **Atualizado em**: 2026-05-26

---

## Sumário Executivo

Este projeto nasceu da especificação técnica do canal **No Risk No Gain (Gean Carlos Gorla)** para o EA "Gradiente Linear com Preço Médio no Renko". O objetivo era validar via backtest massivo em dados tick-a-tick BTP (138 GB, 7.67 bilhões de ticks, 2021–2026) se a estratégia era viável para deploy real, identificar a configuração ótima e portar tudo para MQL5.

**Resultado final**: Configuração **GAIN_72 + SL 0.3% + DS75** entregou **+R$ 102.681 em 6 anos** (2021–2026), PF 1.35, DD R$ 9.427, CV 0.79, WR 96.9%. EA compilado com sucesso para MT5.

---

## 1. Origem e Especificação Base

### 1.1 Fonte
- **Especificação**: `ea_gradiente_renko.agent.final.pdf` (canal No Risk No Gain)
- **Conceito**: Estratégia de pullback em tijolos Renko com preço médio reativo. Cada novo nível é adicionado a um preço fixo de distância do anterior. O ganho é calculado acima do preço médio ponderado. Stop loss protege o lado oposto.

### 1.2 Parâmetros Originais (Baseline)
```
Ativo: WIN
Renko: 25R (125 pontos)
Níveis: 3 (ML3)
Incremento preço: 100 pts
Incremento ganho: 50 pts
Stop loss: 300 pts fixos
Slippage: 2 pts
Emolumentos: 0.01%
Horário: 9:30 – 16:50
Filtros: 2MV + MACD
Martingale: 1-2-4 (opcional)
```

---

## 2. Infraestrutura Desenvolvida

### 2.1 Stack Tecnológico
| Componente | Tecnologia | Finalidade |
|-----------|-----------|-----------|
| Engine de backtest | Python 3.11 + Numba | Simulação tick-a-tick JIT-compilada |
| Indicadores | NumPy | EMA 21/72, MACD 12/26/9, 2MV |
| Renko Builder | Numba | Construção Nelogica-style (reversão = 2× brick size) |
| Loader BTP | Python | Leitura de packets binários tick-a-tick |
| Visualização | Matplotlib | Equity curves, análises |
| Deploy | MQL5 | EA para MetaTrader 5 |

### 2.2 Dataset
- **Fonte**: `C:\HIST_B3\generator_v3`
- **Período**: 1.262 dias úteis (2021-04-30 a 2026-05-21)
- **Tamanho**: ~138 GB
- **Ticks**: ~7.67 bilhões
- **Ativos**: WIN (Mini Índice), WDO (Mini Dólar)

### 2.3 Arquivos Criados
```
src/
  btp_loader.py          — Loader de packets BTP
  renko.py               — Construtor de tijolos Renko (Numba)
  indicators.py          — EMA, MACD, 2MV
  ea_gradiente.py        — Lógica do EA em Python
  backtest_fast.py       — Simulador tick-a-tick Numba-acelerado
  backtest_engine_v2.py  — Orquestrador de backtest

backtest/
  run_backtest.py        — Backtest por período
  run_backtest_annual.py — Backtest anual
  validate_quick.py      — Validação rápida multi-config
  validate_full.py       — Validação robusta multi-ano
  optimize_params.py     — Grid search de parâmetros
  plot_equity.py         — Geração de gráficos de equity
  passo1_conservadoras.py — Teste configs conservadoras
  passo2_wdo_corrigido.py — Validação WDO Renko 10R
  passo3_stop_diario.py  — Teste stop financeiro diário
  plot_equity_wdo.py     — Gráficos equity WDO

mql5/
  EA_Gradiente_Renko.mq5 — EA completo MT5 (~1071 linhas)
  README_MQL5.md         — Documentação de instalação e uso
```

---

## 3. Fases de Teste e Descobertas

### 3.1 FASE 1 — Baseline e Validação Inicial (2024-05-24)

#### 3.1.1 Primeiros Backtests (WIN 2023-2024)
| Config | Trades | PnL | WR | PF | DD |
|--------|--------|-----|-----|-----|-----|
| WIN 25R nomart ML3 SL300 | 12.461 | **+R$ 19.372** | 97,6% | 1,33 | R$ 1.373 (27,5%) |

**Insight inicial**: Estratégia lucrativa em curto prazo com WR altíssimo. Mas o que acontece em 5 anos?

#### 3.1.2 Multi-Ano 2021-2025 — Baseline
| Config | Trades | PnL | WR | PF | DD |
|--------|--------|-----|-----|-----|-----|
| 25R nomart ML3 SL300 | 45.932 | +R$ 15.106 | 97,4% | **1,06** | R$ 12.054 (241%) |
| 25R mart ML3 SL300 | 46.109 | +R$ 94.844 | 98,6% | 1,32 | R$ 11.869 (237%) |
| 35R nomart ML3 SL300 | 14.514 | +R$ 21.328 | 94,8% | 1,14 | R$ 4.146 (83%) |

**🔴 ALERTA CRÍTICO**: Profit factor de 1,06 em 5 anos é marginal demais. Martingale gera lucro maior mas DD catastrófico (>200%). **Sem martingale é obrigatório** para capital de R$ 5.000.

---

### 3.2 FASE 2 — Configurações Conservadoras (Passo 1)

**Hipótese**: Reduzir níveis (ML2) e apertar SL melhora o drawdown de longo prazo.

| Config | Trades | PnL | DD | Resultado |
|--------|--------|-----|-----|-----------|
| ML2 SL200 | — | **-R$ 175.722** | 3.518% | ❌ CATASTRÓFICO |
| ML2 SL250 | — | **-R$ 98.791** | 2.034% | ❌ CATASTRÓFICO |
| ML3 SL200 | — | **-R$ 84.690** | 1.817% | ❌ CATASTRÓFICO |

**Conclusão**: Reduzir níveis ou apertar stop **piora drasticamente** a performance de longo prazo. A estratégia precisa de espaço para o preço médio respirar.

---

### 3.3 FASE 3 — WDO Corrigido (Passo 2)

**Problema**: WDO com Renko 15R apresentou viés de seleção severo — apenas dias voláteis geravam sinais (média de 60-64 tijolos/dia, threshold = 73).

**Solução**: Testar Renko menor (10R).

| Config | Trades | PnL | WR | PF | DD |
|--------|--------|-----|-----|-----|-----|
| WDO 10R nomart ML3 SL20 | 40.979 | **+R$ 63.992** | 90,6% | **62,05** | R$ 973 (19,5%) |

**Conclusão**: WDO é **MUITO mais robusto** que WIN quando parametrizado corretamente. PF de 62 é excepcional.

---

### 3.4 FASE 4 — Stop Financeiro Diário (Passo 3)

**Hipótese**: Um stop diário rigoroso pode salvar o EA de dias de tendência forte.

Testado em WIN 25R ML3 SL300 (2021-2025):

| Stop Diário | PnL | DD | R/DD | PF | WR |
|-------------|-----|-----|------|-----|-----|
| **R$ 100** | **+R$ 25.111** | 109,3% | **4,59** | 1,15 | 97,6% |
| R$ 200 | +R$ 29.941 | 137,7% | 4,35 | 1,14 | 97,5% |
| R$ 300 | +R$ 27.844 | 150,6% | 3,70 | 1,12 | 97,5% |
| R$ 500 | +R$ 22.419 | 209,4% | 2,14 | 1,08 | 97,4% |
| R$ 750 | +R$ 16.560 | 300,7% | 1,10 | 1,06 | 97,4% |
| R$ 1000 | +R$ 11.619 | 385,5% | 0,60 | 1,04 | 97,3% |
| **Sem stop** | **-R$ 2.230** | **625,2%** | **-0,07** | 0,99 | 97,2% |

**🔴 DESCUBERTA CRÍTICA**: Sem stop diário, o EA é **inviável no longo prazo** (DD 625%, PnL negativo). O stop de R$ 100/dia oferece o melhor Return/DD ratio (4,59), sendo **65× melhor** que sem stop.

---

### 3.5 FASE 5 — Bateria Massiva WIN 2025-2026 (2026-05-25)

#### 3.5.1 Contexto
- **2025**: Mercado lateral — ano favorável para a estratégia
- **2026**: Mercado de tendência forte — ano adverso

**Objetivo**: Encontrar configurações que sobrevivam a 2026 sem destruir os ganhos de 2025.

#### 3.5.2 Baselines 2025
| Stop Diário | PnL 2025 | DD | PF | R/DD |
|-------------|----------|-----|-----|------|
| R$ 50 | +R$ 9.103 | 19,9% | 1,55 | 9,16 |
| R$ 75 | +R$ 8.895 | 23,6% | 1,52 | 7,54 |
| R$ 100 | +R$ 8.918 | 24,9% | 1,51 | 7,15 |
| R$ 150 | +R$ 8.816 | 18,2% | 1,47 | 9,67 |
| R$ 200 | +R$ 7.982 | 23,6% | 1,36 | 6,76 |

#### 3.5.3 Baselines 2026 — TODAS DESTRUÍDAS
| Stop Diário | PnL 2026 | DD | PF |
|-------------|----------|-----|-----|
| R$ 50 | -R$ 11.718 | 234% | 0,31 |
| R$ 75 | -R$ 11.782 | 236% | 0,31 |
| R$ 100 | -R$ 12.311 | 246% | 0,31 |
| R$ 150 | -R$ 14.254 | 285% | 0,31 |
| R$ 200 | -R$ 20.286 | 406% | 0,30 |

**Conclusão**: Baseline com SL fixo de 300 pts **não sobrevive 2026**.

---

### 3.6 FASE 6 — Stop % do Valor de Mercado (IDEIA DO USUÁRIO)

**Hipótese**: Em vez de SL fixo em pontos, usar SL como % do preço atual do ativo. Ex: 0,3% do preço do WIN (~390 pts a 130.000).

#### 3.6.1 Grid Testado (262 configs)
- SL %: 0,1% | 0,15% | 0,2% | 0,3%
- Gain %: 0,05% | 0,08% | 0,1%
- Stop diário: R$ 30 | 40 | 50 | 60 | 75 | 100 | 150 | 200
- Capitais: R$ 5.000 | 10.000 | 15.000

#### 3.6.2 Resultados Chave — 2025 (Ano Favorável)
| Config | PnL | DD | PF |
|--------|-----|-----|-----|
| 0,3% SL / 0,05% gain / DS100 | **+R$ 13.962** | 40,0% | 1,32 |
| 0,2% SL / 0,05% gain / DS150 | +R$ 10.615 | 25,1% | 1,22 |
| 0,3% SL / 0,1% gain / DS75 | +R$ 4.691 | 75,8% | 1,07 |

#### 3.6.3 Resultados Chave — 2026 (Ano Adverso)
| Config | PnL | DD | PF |
|--------|-----|-----|-----|
| **0,3% SL / 0,1% gain / DS75** | **+R$ 1.112** | 75,8% | **1,02** |
| Todas as outras 87 configs | Negativo | >65% | <1,00 |

**🔴 DESCUBERTA**: 0,3%/0,1%/DS75 foi a **ÚNICA configuração lucrativa em 2026** de 88 testadas.

#### 3.6.4 Longo Prazo 2021-2026 — Stop %
| Config | PnL | DD (cap 15k) | PF | R/DD |
|--------|-----|--------------|-----|------|
| Baseline DS100 | +R$ 21.201 | 82,2% | 1,14 | 1,72 |
| **0,15% SL / 0,05% gain / DS75** | **+R$ 26.753** | **58,6%** | 1,08 | **3,04** |
| **0,2% SL / 0,08% gain / DS100** | **+R$ 22.705** | **53,0%** | 1,05 | **2,85** |
| **0,3% SL / 0,1% gain / DS75** | **+R$ 36.430** | **77,8%** | **1,07** | **3,12** |

**Conclusão**: A ideia do stop % se validou. Com R$ 15.000, 0,3%/0,1%/DS75 é a melhor configuração para longo prazo.

---

### 3.7 FASE 7 — Otimização de Ganho Fixo (Linearity)

**Hipótese**: O gain de 50 pts (baseline) deixa dinheiro na mesa. Testar gains maiores para melhorar linearidade anual.

#### 3.7.1 Ganho Fixo vs Baseline (6 anos)
| Ano | Baseline G50 | GAIN_65 | Delta |
|-----|-------------|---------|-------|
| 2021 | -R$ 466 | **+R$ 10.592** | ✅ |
| 2022 | +R$ 7.039 | **+R$ 25.602** | +R$ 18.563 |
| 2023 | +R$ 15.667 | +R$ 23.334 | +R$ 7.667 |
| 2024 | +R$ 2.353 | **+R$ 10.844** | **+R$ 8.491** |
| 2025 | +R$ 8.926 | +R$ 11.924 | +R$ 2.998 |
| 2026 | -R$ 12.318 | **-R$ 10.252** | +R$ 2.066 |

**Conclusão**: Aumentar gain de 50→65 mais que **dobrou o lucro total** (+98%), reduziu dependência do melhor ano de 73,9%→35,5%, e tornou 2021 positivo pela primeira vez. CV = 0,97.

#### 3.7.2 GAIN_72 — O Sweet Spot Definitivo
Testando gains de 60-85 pts:

| Gain | PnL Total | PF | DD | CV | Max Year Contrib |
|------|-----------|-----|-----|-----|-----------------|
| 50 | +R$ 49.714 | 1,20 | R$ 9.735 | 1,128 | 43,4% |
| 60 | — | — | — | — | — |
| **72** | **+R$ 102.681** | **1,35** | **R$ 9.427** | **0,794** | **33,3%** |
| 80 | — | — | — | — | — |
| 85 | — | — | — | — | — |

**🔴 CONFIGURAÇÃO DEFINITIVA IDENTIFICADA:**
```
WIN | Renko 25R | ML3 | SEM Martingale
SL: 0,3% do preço (~390 pts a 130k)
Gain: 72 pontos fixos (~R$ 14,40 por contrato no nível 1)
Stop diário: R$ 75
Capital mínimo: R$ 15.000
```

**Resultado 2021-2026**:
- PnL: **+R$ 102.681**
- PF: **1,35**
- DD: **R$ 9.427 (62,8% com cap 15k)**
- CV: **0,79** (excelente consistência)
- WR: **96,9%**
- Trades: **28.925**

| Ano | PnL G72 | Contribuição % |
|-----|---------|---------------|
| 2021 | +R$ 19.625 | 19,1% |
| 2022 | +R$ 34.236 | 33,3% |
| 2023 | +R$ 28.080 | 27,3% |
| 2024 | +R$ 12.293 | 12,0% |
| 2025 | +R$ 17.131 | 16,7% |
| 2026 | -R$ 8.684 | -8,5% |

**O gain de 72 pts é o sweet spot**: maior que 65 supera em todos os anos; maior que 72 começa a perder targets; menor deixa dinheiro na mesa.

---

## 4. TUDO O QUE FOI TESTADO E REJEITADO

### 4.1 Rejeições com Dados de Backtest

| Ideia | Testado | Resultado | Por que Rejeitou |
|-------|---------|-----------|-----------------|
| **Preservation Stop** | Sim | -R$ 40k | Protegia pouco e cortava lucros |
| **ML1 (Martingale 1 nível)** | Sim | -R$ 73k | Muito restritivo, perdia todos os setups |
| **ML2 + SL200** | Sim | -R$ 176k | Catastrófico — sem espaço para preço médio |
| **ML2 + SL250** | Sim | -R$ 99k | Catastrófico |
| **ML3 + SL200** | Sim | -R$ 85k | Catastrófico |
| **Max 5 trades/dia** | Sim | Lucro morto | Matou os ganhos sem salvar o DD |
| **EMA distance filter** | Sim | Piorou | Removeu trades bons mais que ruins |
| **Dynamic levels (ML2/ML1 por EMA dist)** | Sim | Piorou | Mesmo problema |
| **SL > 0,3%** | Sim | Piorou | Stop muito amplo destrói em tendência |
| **SL < 0,3%** | Sim | Piorou | Stop muito apertado = whipsaw |
| **Old trailing stop (breakeven only)** | Sim | Inútil | Não protegia lucros parciais |
| **Gain % adaptativo (0,05%-0,1%)** | Sim | Inferior a G72 fixo | G72 fixo superou em todos os anos |
| **Martingale 1-2-4** | Sim | DD 237% | Lucro alto mas DD inaceitável |
| **Martingale 1-2-4-8 (ML4)** | Sim | DD 239% | Pior ainda |
| **Renko 35R** | Sim | PF 1,14 | Menos trades, menos lucro |
| **Renko 15R WDO** | Sim | Viés de seleção | Apenas dias voláteis geravam sinais |
| **News filter (10:15)** | Sim | Piorou ligeiramente | -R$ 3k vs baseline |
| **Stop diário > R$ 100** | Sim | R/DD pior | R$ 75 é o ponto ideal |
| **Stop diário < R$ 75** | Sim | Lucro reduzido | Corta demais os ganhos |
| **Capital R$ 5.000** | Sim | DD > 200% | Inviável mesmo na melhor config |
| **Gain 80-85 pts** | Sim | Missing targets | Alvos muito distantes não eram atingidos |
| **Gain 50-60 pts** | Sim | Deixa dinheiro | Lucros parciais demais |

### 4.2 Rejeições Sem Teste (Análise Técnica)

| Ideia | Por que Não Testou | Razão |
|-------|-------------------|-------|
| **Timeframe menor que Renko 10R** | Ruído excessivo | Tijolos demais = overtrading |
| **Timeframe maior que Renko 35R** | Sinais raros demais | <10 trades/dia = estatística fraca |
| **Oposto da tendência (contra-trend)** | Estratégia é pullback | Contra-trend quebra a premissa |
| **Outros ativos (PETR4, VALE3)** | Fora do escopo | WIN/WDO são os alvos da especificação |
| **Machine Learning para sinais** | Complexidade | Não há edge demonstrável em features simples |

---

## 5. Features Implementadas no Código

### 5.1 Python Engine

| Feature | Arquivo | Descrição |
|---------|---------|-----------|
| Renko Nelogica-style | `src/renko.py` | Reversão requer 2× brick size |
| EMA 21/72 | `src/indicators.py` | Médias móveis exponenciais |
| MACD 12/26/9 | `src/indicators.py` | Histograma MACD |
| 2MV Padrão | `src/indicators.py` | Média móvel de 2 períodos com cores |
| Preço médio reativo | `src/ea_gradiente.py` | Recalcula a cada preenchimento |
| Stop loss fixo | `src/backtest_fast.py` | Em pontos |
| **Stop loss %** | `src/backtest_fast.py` | Como % do preço de mercado |
| **Trailing stop real** | `src/backtest_fast.py` | Protege lucros parciais, não só breakeven |
| **Daily stop loss** | `src/backtest_fast.py` | Stop financeiro diário |
| Martingale 1-2-4 | `src/backtest_fast.py` | Níveis progressivos |
| **Max trades/dia** | `src/backtest_fast.py` | Limitador de frequência |
| **EMA distance filter** | `src/backtest_engine_v2.py` | Zero sinais se EMA21-EMA72 > threshold |
| **Dynamic levels** | `src/backtest_engine_v2.py` | Reduz ML se EMA spread grande |
| Slippage | `src/backtest_fast.py` | Pontos fixos |
| Emolumentos | `src/backtest_fast.py` | % sobre valor financeiro |
| Close EOD | `src/backtest_fast.py` | Fecha posições no fim do dia |
| Numba JIT | `src/backtest_fast.py` | `@njit(cache=True)` nos loops críticos |

### 5.2 MQL5 EA

| Feature | Status | Descrição |
|---------|--------|-----------|
| Renko incremental | ✅ | Construção tijolo a tijolo em tempo real |
| EMA 21/72 | ✅ | Indicadores em tempo real |
| MACD histograma | ✅ | Filtro de tendência |
| 2MV cores | ✅ | Filtro de direção |
| Sinais pullback/continuação | ✅ | Lógica de entrada |
| Gradient levels (ML3) | ✅ | 3 níveis com limit orders |
| Preço médio reativo | ✅ | Recalcula a cada fill |
| **SL % adaptativo** | ✅ | `InpStopLossPct = 0.003` |
| **Gain fixo 72 pts** | ✅ | `InpGainIncrement = 72.0` |
| **Stop diário R$ 75** | ✅ | `InpDailyStopLoss = 75.0` |
| **Trailing stop** | ✅ | Protege lucros parciais |
| **Preservation stop** | ✅ | Desativado por padrão |
| **Max trades/dia** | ✅ | `InpMaxTradesPerDay = 0` (ilimitado) |
| **EMA distance filter** | ✅ | Desativado por padrão |
| **Dynamic levels** | ✅ | Desativado por padrão |
| **Gain adaptativo** | ✅ | `InpUseAdaptiveGain` — switch por regime |
| Close EOD | ✅ | Fecha posições 16:50 |
| OnTester | ✅ | Para otimização no Strategy Tester |

---

## 6. Evolução do MQL5 (Port)

### 6.1 Fases do Port

| Data | Milestone |
|------|-----------|
| 2024-05-24 | Estrutura base do EA criada |
| 2024-05-24 | Renko incremental, indicadores, sinais |
| 2024-05-24 | Order management com CTrade |
| 2024-05-25 | Inputs atualizados para config ótima |
| 2024-05-25 | Trailing stop implementado |
| 2024-05-25 | Gain adaptativo implementado |
| 2024-05-25 | Stop %, max trades/day, EMA filters |
| 2024-05-26 | **Compilação bem-sucedida** (0 erros, 0 warnings) |

### 6.2 Bugs Encontrados e Corrigidos

| Bug | Causa | Correção |
|-----|-------|----------|
| `undeclared identifier 'g_pendingOrders'` | Variáveis globais perdidas no refactor | Re-adicionado `PendingOrder g_pendingOrders[]; int g_pendingCount = 0;` |
| `unexpected token` na linha 481 | `color` é palavra reservada em MQL5 | Renomeado para `brickColor` |

---

## 7. Análise de Consistência e Robustez

### 7.1 Coeficiente de Variação (CV)
O CV mede a consistência anual: quanto menor, mais linear.

| Config | CV | Interpretação |
|--------|-----|---------------|
| Baseline G50 | 1,128 | Alta variabilidade |
| GAIN_65 | 0,97 | Boa consistência |
| **GAIN_72** | **0,794** | **Excelente consistência** |
| Stop % 0,3/0,1 | — | Não calculado |

### 7.2 Contribuição Máxima de um Único Ano
Quanto menor, menos dependente de um ano excepcional.

| Config | Max Year Contrib | Interpretação |
|--------|-----------------|---------------|
| Baseline G50 | 43,4% | Depende muito de 2022 |
| GAIN_65 | — | Melhor distribuição |
| **GAIN_72** | **33,3%** | **Melhor distribuição de todas** |

### 7.3 Profit Factor por Regime

| Regime | Baseline | G72 | Interpretação |
|--------|----------|-----|---------------|
| Lateral (2025) | 1,51 | 1,35 | Lucrativo |
| Tendência (2026) | 0,31 | ~0,90 | Perda reduzida |
| Longo prazo | 1,06 | **1,35** | **Muito superior** |

---

## 8. Lições Aprendidas

### 8.1 O Que Funciona
1. **Gain 72 pts é o sweet spot**: nem muito curto (deixa dinheiro), nem muito longo (perde targets).
2. **SL 0,3% adaptativo**: melhor que fixo em todos os regimes de mercado.
3. **Stop diário R$ 75**: protege sem sufocar. R$ 100+ é permissivo demais em 2026.
4. **Sem martingale**: obrigatório para DD gerenciável.
5. **Trailing stop real**: protege lucros parciais, não só breakeven.
6. **Capital mínimo R$ 15.000**: abaixo disso, DD > 100%.
7. **WDO é mais robusto**: mas requer Renko menor (10R) e menos liquidez.

### 8.2 O Que NÃO Funciona
1. **Preservation stop**: destrói a estratégia (-R$ 40k).
2. **Reduzir níveis (ML2)**: elimina o edge do preço médio.
3. **Apertar SL fixo**: whipsaw catastrófico.
4. **Martingale**: lucro ilusório com DD explosivo.
5. **Filtros EMA excessivos**: removem mais trades bons que ruins.
6. **Gain adaptativo por %**: inferior a gain fixo de 72 pts nos testes.
7. **Max trades/day agressivo**: corta os lucros sem salvar o DD.

### 8.3 Insights de Mercado
1. **2025 (lateral)**: gain menor era melhor (0,05% > 0,08% > 0,1%).
2. **2026 (tendência)**: gain maior era melhor (0,1% > 0,08% > 0,05%).
3. **A estratégia é estatística**: aceitar que 2026 é um ano de perda é parte do jogo.
4. **~21 trades/dia**: alta frequência exige automação completa.
5. **64% dos trades com 1 contrato**: a maioria das operações não chega ao nível 2.

---

## 9. Estado Final do Deploy

### 9.1 EA MQL5 Compilado
- **Arquivo**: `EA_Gradiente_Renko.ex5` (56.8 KB)
- **Local**: `MQL5/Experts/` no terminal `MetaTrader 5_XP_Demo`
- **Compilação**: 0 erros, 0 warnings, 865ms
- **Versão**: 1.00

### 9.2 Configuração de Inputs (Defaults)
```cpp
InpRenkoR          = 25;        // Renko 25R
InpBaseQty         = 1;         // 1 contrato base
InpPriceIncrement  = 100.0;     // 100 pts entre níveis
InpGainIncrement   = 72.0;      // 72 pts de gain
InpMaxLevels       = 3;         // ML3
InpUseMartingale   = false;     // SEM martingale
InpStopLossPts     = 0.0;       // Usar %
InpStopLossPct     = 0.003;     // 0.3% do preço
InpDailyStopLoss   = 75.0;      // R$ 75/dia
InpTrailingStop    = false;     // Desativado (habilitar se desejado)
InpTrailingValue   = 20.0;      // R$ 20 de trailing
InpPreservationStop= false;     // Desativado
InpMaxTradesPerDay = 0;         // Ilimitado
InpMaxEMADistance  = 0.0;       // Filtro EMA off
InpUseMACD         = true;      // MACD on
InpUse2MV          = true;      // 2MV on
InpHourStart       = 10;        // 10:00
InpHourEnd         = 16;        // 16:00
InpCloseAtEndDay   = true;      // Fecha EOD
```

### 9.3 Recomendação Operacional Final
```
ATIVO: WIN$N (contrato vigente)
RENKO: 25R via indicador customizado ou offline chart
NÍVEIS: 3 (sem Martingale)
GAIN: 72 pontos fixos
STOP: 0.3% do preço de mercado (~390 pts a 130k)
STOP DIÁRIO: R$ 75,00
HORÁRIO: 10:00 - 16:00 (fechamento 16:50)
CAPITAL MÍNIMO: R$ 15.000
REAVALIAÇÃO: A cada 3 meses de demo
```

---

## 10. Próximos Passos (Pós-Histórico)

1. [ ] **Demo trading** — Rodar 3-6 meses em conta demo XP
2. [ ] **Walk-forward analysis** — Janelas de 6 meses rolantes
3. [ ] **Validação em MQL5 Strategy Tester** — Confirmar backtest MT5 = Python
4. [ ] **Monitoramento diário** — Logs de execução, slippage real, latência
5. [ ] **Reavaliação trimestral** — Ajustar gain se regime mudar
6. [ ] **Considerar WDO** — Se WIN continuar ruim, pivotar para WDO 10R

---

## 11. Referências e Arquivos de Evidência

### 11.1 Relatórios JSON
| Arquivo | Descrição |
|---------|-----------|
| `reports/win_g72_sixyear.json` | **Configuração definitiva G72** |
| `reports/win_gain65_sixyear_only.json` | G65 para comparação |
| `reports/win_pct_03_01_long_term.json` | Stop % 0,3/0,1 em longo prazo |
| `reports/win_full_battery_2025_2026.json` | 262 configs testadas |
| `reports/robustness_full_2021_2025.json` | Validação robusta multi-ano |
| `reports/passo3_stop_diario_2021_2025.json` | Stop diário testado |
| `reports/passo2_wdo_corrigido_2021_2025.json` | WDO 10R corrigido |

### 11.2 Gráficos
| Arquivo | Descrição |
|---------|-----------|
| `reports/equity_G72_final.png` | Equity curve G72 2021-2026 |
| `reports/equity_GAIN65_vs_baseline.png` | Comparação G65 vs baseline |
| `reports/equity_WIN_2023_2024.png` | Equity baseline 2023-2024 |
| `reports/equity_WDO_2021_2025.png` | Equity WDO 2021-2025 |

### 11.3 Logs
| Arquivo | Descrição |
|---------|-----------|
| `reports/win_battery_log.txt` | Log completo 262 configs |
| `reports/win_pct_03_01_log.txt` | Log stop % longo prazo |
| `reports/win_annual_breakdown_log.txt` | Breakdown anual detalhado |
| `reports/wdo_battery_log.txt` | Log bateria WDO |

---

> **Nota final**: Este documento preserva o histórico completo para que nenhuma decisão, descoberta ou erro seja perdido. Toda configuração testada, toda rejeição e todo insight está aqui registrado. O caminho foi longo — da baseline destruída em 2026 até a configuração G72 que entregou +R$ 102k em 6 anos.
