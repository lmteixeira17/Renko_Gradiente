# AGENTS.md — EA Gradiente Linear com Preço Médio no Renko

> Arquivo de referência para agentes de código. Leia este arquivo antes de modificar qualquer coisa no projeto.

---

## Visão Geral do Projeto

Este projeto implementa e valida via backtest o Expert Advisor (EA) **"Gradiente Linear com Preço Médio no Renko"**, baseado na especificação técnica do canal No Risk No Gain (Gean Carlos Gorla).

O projeto possui duas implementações:
1. **Python** — engine de backtest tick-a-tick otimizada com Numba, scripts de validação e otimização de parâmetros.
2. **MQL5** — EA completo para deploy no MetaTrader 5.

**Ativos tradados**: WIN (Mini Índice Bovespa) e WDO (Mini Dólar).

**Estratégia resumida**:
- Gráfico Renko (Nelogica-style) com filtros 2MV Padrão (EMA 21/72 + coloração) e MACD (12,26,9).
- Entrada em pullback na direção da tendência, confirmada por 2MV + MACD.
- Gestão de risco via gradiente linear com múltiplos níveis de preço e preço médio reativo.
- Saída em take-profit no preço médio + ganho, ou stop loss fixo.

---

## Stack Tecnológico

| Componente | Tecnologia |
|------------|------------|
| Linguagem principal | Python 3.11+ |
| Aceleração numérica | NumPy |
| JIT / loops críticos | Numba (`@njit(cache=True)`) |
| Visualização | Matplotlib |
| Leitura de PDF (spec) | PyMuPDF (opcional) |
| Deploy em corretora | MQL5 (MetaTrader 5) |
| Dataset de ticks | BTP (B3 Tick Protocol) v3.2 |

**Não há** `pyproject.toml`, `setup.py`, `requirements.txt`, `package.json`, `Makefile`, `Cargo.toml`, ou qualquer outro arquivo de build/consumo de dependências. As dependências devem ser instaladas manualmente no ambiente Python.

---

## Estrutura de Diretórios

```
Renko_Gradiente/
├── src/                          # Código fonte do EA e engine de backtest
│   ├── btp_loader.py             # Carrega packets BTP tick-a-tick de C:\HIST_B3\generator_v3
│   ├── renko.py                  # Construtor de tijolos Renko (Numba-acelerado, estilo Nelogica)
│   ├── indicators.py             # EMA, MACD, 2MV Padrão
│   ├── ea_gradiente.py           # Lógica pura do EA (estado, sinais, execução)
│   ├── backtest_fast.py          # Simulação tick-a-tick otimizada com Numba
│   └── backtest_engine_v2.py     # Engine completa: sinais → simulação → métricas → JSON
│
├── backtest/                     # Scripts executáveis de backtest, validação e otimização
│   ├── run_backtest_v2.py        # Backtest simples por período
│   ├── run_backtest_annual.py    # Backtest anual (script principal de referência)
│   ├── optimize_params.py        # Grid search de parâmetros
│   ├── validate_quick.py         # Validação rápida multi-config (2 anos)
│   ├── validate_full.py          # Validação robusta multi-ano (2021-2025)
│   ├── validate_robustness.py    # Testes de robustez adicionais
│   ├── passo1_conservadoras.py   # Teste de configs conservadoras WIN
│   ├── passo2_wdo_corrigido.py   # Validação WDO com Renko 10R
│   ├── passo3_stop_diario.py     # Teste de stop financeiro diário
│   ├── plot_equity.py            # Gera curva de equity (WIN)
│   ├── plot_equity_wdo.py        # Gera curva de equity (WDO)
│   ├── auditoria_final.py        # Auditoria completa por ano
│   ├── debug_trades.py           # Debug de trades individuais
│   └── test_single_day.py        # Teste de um único dia
│
├── mql5/                         # Código para MetaTrader 5
│   ├── EA_Gradiente_Renko.mq5    # EA completo (~994 linhas)
│   └── README_MQL5.md            # Documentação de instalação e parâmetros
│
├── config/                       # Diretório reservado para configurações (vazio atualmente)
├── notebooks/                    # Diretório reservado para Jupyter notebooks (vazio atualmente)
├── reports/                      # Relatórios JSON e gráficos PNG gerados
├── ea_gradiente_renko.agent.final.pdf  # Especificação técnica original (PDF)
├── BACKTEST_RESULTS.md           # Resultados consolidados de backtest
├── STATUS.md                     # Estado atual do projeto, entregas e próximos passos
├── MEMORY.md                     # Memória persistente de sessões de trabalho
├── CLAUDE.md                     # Instruções gerais para assistentes
└── README.md                     # Documentação de entrada para humanos
```

---

## Como Executar

Todos os scripts em `backtest/` são executáveis diretamente. Cada script manipula o `sys.path` internamente para importar de `src/`, então **não é necessário instalar o projeto como pacote**.

```bash
# Backtest anual de referência (WIN 2024)
python backtest/run_backtest_annual.py

# Validação rápida multi-config
python backtest/validate_quick.py

# Validação robusta multi-ano
python backtest/validate_full.py

# Otimização de parâmetros (grid search)
python backtest/optimize_params.py

# Gráfico de equity
python backtest/plot_equity.py

# Auditoria final completa
python backtest/auditoria_final.py
```

**Requisito**: o dataset BTP deve existir em `C:\HIST_B3\generator_v3`. Este caminho é hardcoded em `src/btp_loader.py`.

---

## Convenções de Código

- **Python 3.11+** com `from __future__ import annotations`.
- **Type hints** obrigatórios em funções públicas.
- **Dataclasses** para estruturas de estado (`EAGradienteState`, `BacktestResult`, `Trade`, `Level`, etc.).
- **Numba** (`@njit(cache=True)`) para qualquer loop que processe ticks individualmente.
- **NumPy** para vetorização de indicadores e operações em arrays.
- **Matplotlib** com backend `Agg` para geração de gráficos sem GUI.
- Nomeação de variáveis e comentários em **português** (ex: `preço`, `ganho`, `níveis`, `stop_loss_pts`, `emolumentos_pct`).

### Padrões de importação nos scripts de backtest

Todos os scripts em `backtest/` seguem este padrão no topo do arquivo:

```python
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

---

## Arquitetura do Código

### Pipeline de backtest

```
BTP Packet (ticks) → btp_loader.py → renko.py (bricks)
                                               ↓
backtest_engine_v2.prepare_signals() ← indicators.py (EMA, MACD, 2MV)
                                               ↓
backtest_fast._simulate_day() (Numba) → trades → métricas → JSON
```

### Módulos principais

| Módulo | Responsabilidade |
|--------|------------------|
| `btp_loader.py` | Abertura de packets `.btp`, listagem de dias, iteração de datas. |
| `renko.py` | Construção de tijolos Renko a partir de stream de ticks. Implementa convenção Nelogica: `brick_size = R * tick_size - tick_size`, reversão requer `2 * brick_size`. |
| `indicators.py` | Cálculo de EMA, MACD e sinal 2MV Padrão (cor green/red/neutral baseada em preço, EMAs e inclinação). |
| `ea_gradiente.py` | Lógica pura do EA: estado da posição, níveis de gradiente, verificação de sinais, fill de ordens limit, take-profit, stop-loss, trailing stop, stop diário. |
| `backtest_fast.py` | Simulação tick-a-tick em Numba. É o gargalo de performance; processa ~6M ticks/dia em ~0.1s após warmup. |
| `backtest_engine_v2.py` | Orquestração: carrega dados, constroi Renko, calcula sinais, chama simulação Numba, agrega resultados, salva JSON. |

### Decisões arquiteturais críticas

1. **Numba vs Python puro**: a simulação tick-a-tick usa Numba; indicadores e sinais usam Python puro + NumPy.
2. **Renko builder Nelogica-style**: reversão requer movimento de 2× o tamanho do tijolo.
3. **Custos de transação**: slippage fixo em pontos + emolumentos percentuais sobre valor financeiro (`emolumentos_pct`).
4. **Horário de trading**: filtrável via `start_time_ms` / `end_time_ms` na simulação Numba.

---

## Estratégia de Teste e Validação

**Não há testes unitários automatizados** neste projeto. A validação é feita exclusivamente via backtest em dados históricos reais (tick-a-tick BTP).

### Scripts de validação

| Script | Propósito |
|--------|-----------|
| `validate_quick.py` | Testa 6 configurações em 2 anos (2023-2024). Rápido (~minutos). |
| `validate_full.py` | Testa 9+ configurações em 5 anos (2021-2025). Abrangente. |
| `validate_robustness.py` | Variações adicionais de robustez. |
| `passo1_conservadoras.py` | Configurações conservadoras WIN (ML2, SL apertado). |
| `passo2_wdo_corrigido.py` | WDO com Renko corrigido (10R). |
| `passo3_stop_diario.py` | Teste sistemático de stop financeiro diário. |
| `auditoria_final.py` | Auditoria completa com breakdown por ano. |

### Métricas de avaliação

- Net PnL, Win Rate, Profit Factor, Max Drawdown (absoluto e %), Avg Trade, Return/Drawdown ratio.
- Capital de referência para cálculo de drawdown %: **R$ 5.000**.

---

## Configurações Recomendadas (referência)

### WIN (Mini Índice) — Configuração principal

```json
{
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
  "daily_stop_loss": 100.0,
  "start_time_ms": 34200000,
  "end_time_ms": 60600000
}
```

### WDO (Mini Dólar) — Configuração corrigida

```json
{
  "renko_r": 10,
  "tick_size": 0.5,
  "tick_value": 10.0,
  "base_qty": 1,
  "max_levels": 3,
  "martingale": false,
  "price_increment": 2.0,
  "gain_increment": 0.5,
  "stop_loss_pts": 20.0,
  "slippage_pts": 1.0,
  "emolumentos_pct": 0.0001
}
```

---

## Considerações de Segurança

1. **Não commitar credenciais**: nenhuma senha, token ou chave API em texto plano.
2. **Não modificar dados BTP**: os packets em `C:\HIST_B3\generator_v3` são **somente leitura**.
3. **Manter `.gitignore` atualizado**: excluir arquivos gerados (`reports/*.png`, `reports/*.json`, `__pycache__`).
4. **Dataset BTP**: mantido por outro processo externo; este projeto apenas consome.

---

## Arquivos de Documentação e Estado

| Arquivo | Função |
|---------|--------|
| `STATUS.md` | Estado do projeto, entregas concluídas, resultados principais, próximos passos. **Atualizar após mudanças significativas.** |
| `MEMORY.md` | Memória persistente de sessões de trabalho. **Atualizar ao final de cada sessão.** |
| `CLAUDE.md` | Instruções gerais para assistentes (em português). |
| `BACKTEST_RESULTS.md` | Resultados consolidados de backtest em formato legível. |
| `README.md` | Documentação de entrada para humanos (Quick Start, dependências, parâmetros). |
| `mql5/README_MQL5.md` | Documentação específica do EA MQL5 (instalação, parâmetros, recomendações). |

---

## Contexto e Dependências Externas

- Projeto faz parte do ecossistema `EA-Trading` em `D:\_Projetos\EA-Trading\10_PROJETOS_EA\`.
- Central de acompanhamento: `_Testes_e_Padroes` (somente leitura para este projeto).
- Dataset BTP: `C:\HIST_B3\generator_v3` (v3.2, ~138 GB, 7,67 bilhões de ticks, 1.262 dias para WIN e WDO).
- Repositório GitHub: `https://github.com/lmteixeira17/Renko_Gradiente`.

---

## Descobertas Críticas do Projeto (para contexto do agente)

- **Stop diário é essencial**: sem stop financeiro diário, o EA é inviável no longo prazo (DD 625%, PnL negativo em 5 anos). Stop de R$100/dia oferece o melhor Return/DD ratio (4.59).
- **Martingale é proibido para deploy**: apesar de gerar lucros maiores a curto prazo, o drawdown em 5 anos é catastrófico (>2000%).
- **WDO requer Renko menor**: em 2024+, a volatilidade do WDO caiu drasticamente, exigindo Renko 10R ou menor.
- **Profit factor marginal em 5 anos**: para WIN, o PF é ~1.06 em 5 anos, indicando pouca margem para custos reais adicionais.
