# STATUS.md — EA Gradiente Linear com Preço Médio no Renko

**Atualizado em**: 2026-05-24

## Estado Atual

Projeto de implementação e validação do EA "Gradiente Linear com Preço Médio no Renko", baseado na especificação técnica do canal No Risk No Gain (Gean Carlos Gorla).

### Fase atual
✅ **Fase 1 — Backtest e Validação** concluída  
⏳ **Fase 2 — Port para plataforma de trading** pendente

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

### Resultados de backtest obtidos
| Arquivo | Descrição |
|---------|-----------|
| `reports/backtest_v2_WIN_2024-01-01_2024-03-31.json` | Backtest Q1 2024 WIN |
| `reports/backtest_annual_WIN_2024-01-01_2024-12-31.json` | Backtest anual 2024 WIN |
| `reports/robustness_quick_2023_2024.json` | Validação rápida 6 configs |
| `reports/robustness_full_2021_2025.json` | Validação robusta 9 configs multi-ano |
| `reports/equity_WIN_2023_2024.png` | Gráfico de equity 2023-2024 |

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

### Alerta crítico — 5 anos
- Em 2021-2025, **TODAS** as configurações WIN apresentaram drawdown > 200%
- Martingale é o fator de risco dominante
- Configuração sem Martingale é a única viável para capital de R$ 5.000

### WDO — Problema identificado
- Renko 15R gera poucos tijolos/dia (~20-64)
- Apenas dias com >73 tijolos produzem sinais (viés de seleção)
- Volatilidade caiu drasticamente em 2024 (média 18 tijolos/dia)
- **Recomendação**: usar Renko 10R ou menor para WDO

## Passos em execução

### Passo 1: Configurações Conservadoras WIN (2021-2025)
**Status**: 🔄 Rodando em background
- ML2 SL200: PnL -R$ 175.722, DD 3518% — catastrófico
- ML2 SL250: PnL -R$ 98.791, DD 2034% — catastrófico
- Próximas: ML2 SL200 150/75, ML3 SL200, ML2 SL200 martingale

### Passo 2: WDO Corrigido com Renko 10R (2021-2025)
**Status**: ✅ CONCLUÍDO
- Melhor configuração: **WDO 10R | ML3 | SL20 | price_inc=2 | gain_inc=0.5**
- Resultado 5 anos: PnL **R$ 63.991**, DD **19,5%**, PF **62.05**
- Gráfico: `reports/equity_WDO_2021_2025.png`
- Arquivo JSON: `reports/passo2_wdo_corrigido_2021_2025.json`
- **Descoberta importante**: WDO é mais robusto que WIN com parâmetros corrigidos

## Próximos passos (priorizados)

1. [x] Testar configurações conservadoras (ML2, SL=200) em 5 anos — em andamento, resultados ruins
2. [x] Corrigir WDO com Renko 10R — CONCLUÍDO, resultado excelente
3. [ ] **Implementar stop financeiro diário rigoroso** e testar em 5 anos
4. [ ] **Port para MQL5** (MetaTrader 5) ou NTSL (ProfitChart)
5. [ ] **Walk-forward analysis** com janelas de 6 meses
6. [ ] **Gerar mais visualizações** (drawdown por mês, distribuição de trades)

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
- Relatórios `_Testes_e_Padroes`:
  - `relatorios/2026-05-24_renko_gradiente_validacao.md`
  - `relatorios/2026-05-24_renko_gradiente_validacao_multi_ano.md`
  - `cadastros/renko_gradiente.md`
