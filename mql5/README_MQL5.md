# EA Gradiente Renko - MQL5

MetaTrader 5 implementation of the "Gradiente Linear com Preço Médio no Renko" strategy.

## Files

- `EA_Gradiente_Renko.mq5` - Main EA file

## Installation

1. Copy `EA_Gradiente_Renko.mq5` to your MetaTrader 5 Experts folder:
   ```
   C:\Users\[YourName]\AppData\Roaming\MetaQuotes\Terminal\[Hash]\MQL5\Experts\Renko_Gradiente\
   ```

2. Open MetaEditor (from MT5) and compile the EA (F7)

3. The EA will appear in MT5 Navigator under Expert Advisors

## Input Parameters

### Asset Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| `InpTickSize` | 5.0 | Tick size in points (WIN=5, WDO=0.5) |
| `InpTickValue` | 0.20 | Value per point in R$ (WIN=0.20, WDO=10.0) |
| `InpPointValue` | 1.0 | Point value multiplier |

### Renko Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| `InpRenkoR` | 25 | Renko R value (WIN=25, WDO=10) |
| `InpMinBricksSignal` | 2 | Minimum consecutive bricks for continuation signal |

### Gradient Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| `InpBaseQty` | 1 | Contracts per level |
| `InpPriceIncrement` | 100.0 | Price spacing between levels (pts) |
| `InpGainIncrement` | 72.0 | Profit target above average price (pts) |
| `InpMaxLevels` | 3 | Maximum levels (ML3) |
| `InpUseMartingale` | false | Enable martingale (1-2-4-8...) |

### Adaptive Gain Settings (NEW)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `InpUseAdaptiveGain` | false | Enable adaptive gain based on market regime |
| `InpGainLateral` | 50.0 | Profit target for sideways/ranging market (pts) |
| `InpGainTrend` | 100.0 | Profit target for trending market (pts) |
| `InpTrendBricks` | 3 | Consecutive bricks in same direction to detect trend |

### Risk Management
| Parameter | Default | Description |
|-----------|---------|-------------|
| `InpStopLossPts` | 300.0 | Stop loss in points |
| `InpDailyStopLoss` | 999999.0 | Daily financial stop in R$ |
| `InpTrailingStop` | false | Enable trailing stop |
| `InpTrailingValue` | 20.0 | Trailing stop value in R$ |
| `InpPreservationStop` | false | Enable preservation stop |
| `InpPreservationLvls` | 3 | Preservation stop after N levels |

### Filters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `InpUseMACD` | true | Enable MACD filter |
| `InpUse2MV` | true | Enable 2MV filter |

### Trading Hours
| Parameter | Default | Description |
|-----------|---------|-------------|
| `InpHourStart` | 10 | Start hour (0-23) |
| `InpHourEnd` | 16 | End hour (0-23) |
| `InpCloseAtEndDay` | true | Close positions at end of day |

### Execution
| Parameter | Default | Description |
|-----------|---------|-------------|
| `InpSlippagePts` | 2.0 | Maximum slippage in points |
| `InpCommissionPct` | 0.01 | Commission % per side |
| `InpMagicNumber` | 171717 | Magic number for order identification |
| `InpTradeComment` | "GradRenko" | Trade comment |

## Recommended Configurations

### WIN (Mini Índice) - Conservative (Baseline)
```
InpRenkoR = 25
InpBaseQty = 1
InpPriceIncrement = 100.0
InpGainIncrement = 72.0
InpMaxLevels = 3
InpStopLossPts = 300.0
InpUseMartingale = false
InpTickSize = 5.0
InpTickValue = 0.20
```

### WIN (Mini Índice) - Adaptive Gain (Recommended for 2026+)
```
InpRenkoR = 25
InpBaseQty = 1
InpPriceIncrement = 100.0
InpMaxLevels = 3
InpStopLossPts = 390.0   // 0.3% of ~130k
InpUseMartingale = false
InpTickSize = 5.0
InpTickValue = 0.20
InpDailyStopLoss = 75.0
InpUseAdaptiveGain = true
InpGainLateral = 65.0    // 0.05% for sideways
InpGainTrend = 130.0     // 0.1% for trending
InpTrendBricks = 3
```

### WDO (Mini Dólar) - Conservative
```
InpRenkoR = 10
InpBaseQty = 1
InpPriceIncrement = 2.0
InpGainIncrement = 1.0
InpMaxLevels = 3
InpStopLossPts = 20.0
InpUseMartingale = false
InpTickSize = 0.5
InpTickValue = 10.0
```

## How It Works

1. **Renko Building**: The EA builds Renko bricks tick-by-tick using the Nelogica convention
2. **Signal Detection**: On each new brick, calculates EMA(21), EMA(72), MACD histogram, and 2MV color
3. **Entry**: Enters when a pullback (correction) ends and price returns to trend direction, confirmed by 2MV + MACD
4. **Gradient Levels**: Places limit orders at spaced intervals below/above entry (for long/short)
5. **Average Price**: Recalculates average price as each level fills
6. **Target**: Sets profit target at average price + gain_increment
7. **Stop**: Fixed stop loss at average price - stop_loss_pts
8. **Daily Stop**: Stops trading if daily loss reaches threshold
9. **End of Day**: Closes all positions at end of trading hours

## Optimization

The EA includes `OnTester()` with a custom optimization criterion:
- **Return/Drawdown ratio** weighted by Profit Factor and Win Rate
- Use Strategy Tester in "Slow complete algorithm" mode
- Recommended optimization parameters: `InpRenkoR`, `InpPriceIncrement`, `InpGainIncrement`, `InpStopLossPts`

## Warnings

- **STOP DIÁRIO É ESSENCIAL** - Sem stop diário, o EA tem DD 625% e PnL negativo em 5 anos. Recomendado: R$100-200/dia
- **Martingale is NOT recommended** - backtests show DD > 2000% over 5 years
- **Always use `InpCloseAtEndDay = true`** for day trading
- **Test on demo account first** before live trading
- **Minimum capital**: R$ 5,000 for WIN with no martingale

## Critical Discovery - Daily Stop (Passo 3 Results)

Backtest over 5 years (2021-2025) on WIN proves that daily financial stop is **mandatory**:

| Daily Stop | PnL | Drawdown | Return/DD |
|------------|-----|----------|-----------|
| R$ 100 | R$ 25,111 | 109% | **4.59** |
| R$ 200 | R$ 29,941 | 138% | 4.35 |
| R$ 300 | R$ 27,844 | 151% | 3.70 |
| R$ 500 | R$ 22,419 | 209% | 2.14 |
| None | **-R$ 2,230** | **625%** | **-0.07** |

**Recommendation**: Use `InpDailyStopLoss = 100.0` for best risk-adjusted returns.

## Adaptive Gain Feature

Based on backtest discoveries (May 2025):
- **Sideways market (2025)**: Smaller gain (0.05%) performed better — target is hit more frequently
- **Trending market (2026)**: Larger gain (0.1%) performed better — captures more of the move

The adaptive gain automatically switches between `InpGainLateral` and `InpGainTrend` based on recent Renko brick direction:
- If last `InpTrendBricks` bricks are in the **same direction** → uses `InpGainTrend`
- Otherwise → uses `InpGainLateral`

## Backtest Results (Reference)

### WIN 25R nomart ML3 SL300 (2021-2025)
- Net PnL: R$ 19,372
- Max Drawdown: 27.5%
- Profit Factor: 1.33
- Win Rate: 95.8%

### WIN 25R nomart ML3 with Stop % (2021-2026) — BEST CONFIG
- Config: SL 0.3%, Gain 0.1%, Daily Stop R$75
- Net PnL: **R$ 36,430** (6 years)
- Max Drawdown: 77.8% (cap R$15k) / 116.6% (cap R$10k)
- Profit Factor: 1.07
- Win Rate: 85.8%

### WDO 10R nomart ML3 SL20 (2021-2025)
- Net PnL: R$ 63,992
- Max Drawdown: 19.5%
- Profit Factor: 62.05
- Win Rate: 90.6%
