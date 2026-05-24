# EA Gradiente Linear com Preço Médio no Renko

Implementação Python do Expert Advisor "Gradiente Linear com Preço Médio" baseado na especificação técnica do canal No Risk No Gain (Gean Carlos Gorla), adaptado para backtest em dados tick-a-tick BTP (B3).

## Estratégia

- **Ativos**: WIN (Mini Índice), WDO (Mini Dólar)
- **Gráfico**: Renko (25R/35R WIN, 15R/18R WDO)
- **Indicadores**: 2MV Padrão (EMA 21/72 + coloração), MACD (12,26,9)
- **Entrada**: Tijolo na direção da tendência + confirmação 2MV + MACD + pullback
- **Gestão**: Gradiente linear com Martingale (1-2-4-8-16) e preço médio reativo
- **Saída**: Take-profit no preço médio + ganho, stop loss fixo

## Estrutura do Projeto

```
Renko_Gradiente/
├── src/
│   ├── btp_loader.py          # Carrega packets BTP
│   ├── renko.py               # Construtor de tijolos Renko (Numba)
│   ├── indicators.py          # EMA, MACD, 2MV Padrão
│   ├── ea_gradiente.py        # Lógica do EA (Python puro)
│   ├── backtest_fast.py       # Simulação tick-a-tick (Numba)
│   └── backtest_engine_v2.py  # Engine de backtest
├── backtest/
│   ├── run_backtest_v2.py     # Script principal de backtest
│   └── optimize_params.py     # Otimização de parâmetros
├── config/
├── reports/                   # Relatórios JSON de backtest
└── README.md
```

## Quick Start

```bash
cd Renko_Gradiente
python backtest/run_backtest_v2.py
```

## Dependências

- Python 3.11+
- NumPy
- Numba
- PyMuPDF (para extrair spec do PDF)

## Dataset

Backtest utiliza dados tick-a-tick BTP de `C:\HIST_B3\generator_v3`.

## Parâmetros Principais

| Parâmetro | WIN Padrão | WDO Padrão |
|-----------|-----------|-----------|
| Renko R | 25 | 15 |
| Tick size | 5.0 pts | 0.5 pts |
| Tick value | R$ 0.20 | R$ 10.00 |
| Incremento preço | 100 pts | 3 pts |
| Incremento ganho | 50 pts | 1 pt |
| Stop loss | 1000 pts | 50 pts |
| Níveis | 5 | 5 |

## Backtest

Engine otimizada com Numba processa ~6M ticks/dia em ~0.1s após warmup.
Métricas calculadas: win rate, profit factor, max drawdown, avg trade.
