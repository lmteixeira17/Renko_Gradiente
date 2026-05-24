# Resultados Consolidados de Backtest

> Última atualização: 2026-05-24

---

## 1. Configuração Base Recomendada

```json
{
  "asset": "WIN",
  "renko_r": 25,
  "tick_size": 5.0,
  "tick_value": 0.20,
  "base_qty": 1,
  "max_levels": 3,
  "martingale": false,
  "price_increment": 100.0,
  "gain_increment": 50.0,
  "stop_loss_pts": 300.0,
  "slippage_pts": 2.0,
  "emolumentos_pct": 0.0001,
  "use_macd": true,
  "use_2mv": true,
  "min_bricks_for_signal": 2
}
```

---

## 2. Resultados WIN

### 2.1 Anual 2024 (251 dias)

| Métrica | Valor |
|---------|-------|
| Trades | 5.119 |
| Win Rate | 97,3% |
| Profit Factor | 1,15 |
| Net PnL | R$ 4.152,26 |
| Max Drawdown | R$ 1.424,39 (28,5%) |
| Avg Trade | R$ 0,81 |

### 2.2 Bi-anual 2023-2024 (499 dias)

| Métrica | Valor |
|---------|-------|
| Trades | 12.461 |
| Win Rate | 97,6% |
| Profit Factor | 1,33 |
| Net PnL | R$ 19.371,63 |
| Max Drawdown | R$ 1.373,11 (27,5%) |
| Avg Trade | R$ 1,55 |

### 2.3 Multi-Ano 2021-2025 (1.167 dias)

| Configuração | Trades | PnL | WR | PF | Max DD |
|-------------|--------|-----|-----|-----|--------|
| 25R nomart ML3 SL300 | 45.932 | R$ 15.106 | 97,4% | 1,06 | R$ 12.054 (241%) |
| 25R mart ML3 SL300 | 46.109 | R$ 94.844 | 98,6% | 1,32 | R$ 11.869 (237%) |
| 35R nomart ML3 SL300 | 14.514 | R$ 21.328 | 94,8% | 1,14 | R$ 4.146 (83%) |
| 25R nomart ML4 SL400 | 45.602 | R$ 35.414 | 98,6% | 1,15 | R$ 11.948 (239%) |
| 25R nomart ML3 SL300 (news filter 10:15) | 39.020 | R$ 12.145 | 97,4% | 1,06 | R$ 10.874 (217%) |

### 2.4 Análise de Variantes (Quick Test 2023-2024)

| Variante | PnL | WR | PF | Max DD |
|----------|-----|-----|-----|--------|
| Sem Martingale (ML3, SL300) | R$ 19.372 | 97,3% | 1,33 | R$ 1.373 (27,5%) |
| Martingale 1-2-4 (ML3, SL300) | R$ 49.241 | 98,5% | 1,71 | R$ 2.104 (42,1%) |
| Martingale 1-2-4-8 (ML4, SL400) | R$ 7.235 | 99,3% | 1,16 | R$ 10.748 (215%) |
| Martingale 1-2-4 (ML3, SL500) | R$ 11.615 | 99,1% | 1,32 | R$ 4.373 (87,5%) |
| Sem Martingale (ML3, SL300, news) | R$ 15.587 | 97,6% | 1,32 | R$ 1.575 (31,5%) |
| Sem Martingale (ML3, SL300, 35R) | R$ 6.315 | 94,9% | 1,25 | R$ 3.224 (64,5%) |

---

## 3. Resultados WDO

> ⚠️ **Alerta**: Resultados WDO apresentam viés de seleção devido à baixa geração de tijolos Renko.

### 3.1 Renko 15R (2021-2023)

| Métrica | Valor |
|---------|-------|
| Trades | 5.268 |
| Win Rate | 100,0% |
| Profit Factor | ∞ |
| Net PnL | R$ 85.618,97 |
| Max Drawdown | R$ 0,00 |

**Problema**: Apenas dias com >73 tijolos geram sinais. Em 2021-2023, média de 60-64 tijolos/dia, com poucos dias acima do threshold. Resultado é enviesado para dias voláteis.

### 3.2 Renko 10R (2024-2025)

| Métrica | Valor |
|---------|-------|
| Trades | 6.512 |
| Win Rate | 100,0% |
| Profit Factor | ∞ |
| Net PnL | R$ 79.162,45 |
| Max Drawdown | R$ 0,00 |

**Problema**: Mesmo viés de seleção. SL de 30 pontos nunca atingido na amostra testada.

### 3.3 Bricks por dia no WDO

| Ano | Renko 15R avg | Renko 10R avg | Dias com sinal |
|-----|--------------|---------------|----------------|
| 2021 | 61,5 | — | ~33% |
| 2022 | 64,1 | — | ~27% |
| 2023 | 64,0 | — | ~30% |
| 2024 | 18,4 | 52,1 | ~18% (10R) |
| 2025 | 48,7 | — | ~3% (15R) |

---

## 4. Conclusões

### 4.1 WIN
- **Curto prazo (1-2 anos)**: estratégia é lucrativa com drawdown controlado (< 30%)
- **Longo prazo (5 anos)**: exposta a eventos extremos que geram drawdowns catastróficos (> 200%)
- **Sem Martingale é obrigatório** para capital de R$ 5.000
- **Profit factor marginal em 5 anos (1,06)**: pouca margem para erros

### 4.2 WDO
- **Requer Renko menor** (10R ou menos) para períodos recentes
- **Viés de seleção severo**: apenas dias voláteis geram sinais
- **SL de 30 pontos pode ser muito amplo** para a volatilidade típica do WDO
- **Necessita reavaliação metodológica** antes de qualquer deploy

### 4.3 Recomendação operacional
```
ATIVO: WIN
RENKO: 25R
NÍVEIS: 3 (sem Martingale)
INCREMENTO PREÇO: 100 pts
INCREMENTO GANHO: 50 pts
STOP LOSS: 300 pts
HORÁRIO: 9:30 - 16:50
CAPITAL MÍNIMO: R$ 5.000
REAVALIAÇÃO: a cada 6 meses
```

---

## 5. Arquivos de dados

- `reports/backtest_annual_WIN_2024-01-01_2024-12-31.json`
- `reports/robustness_quick_2023_2024.json`
- `reports/robustness_full_2021_2025.json`
- `reports/equity_WIN_2023_2024.png`
