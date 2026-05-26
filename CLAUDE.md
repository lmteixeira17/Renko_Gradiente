# CLAUDE.md — EA Gradiente Linear com Preço Médio no Renko

Instruções para assistentes trabalhando neste projeto.

## Papel deste projeto

Implementar e validar via backtest o Expert Advisor "Gradiente Linear com Preço Médio no Renko", baseado na especificação técnica do canal No Risk No Gain.

Este projeto contém:
- Implementação Python do EA e engine de backtest
- Scripts de validação e otimização de parâmetros
- Relatórios de backtest em dados tick-a-tick BTP
- Documentação técnica

## Regras obrigatórias

1. **Não commitar credenciais**: nenhuma senha, token ou chave API em texto puro
2. **Não modificar dados BTP**: os packets em `C:\HIST_B3\generator_v3` são somente leitura
3. **Manter `.gitignore` atualizado**: excluir arquivos gerados (JSONs, PNGs, __pycache__)
4. **Documentar alterações**: atualizar `STATUS.md` e `MEMORY.md` após mudanças significativas

## Convenções de código

- Python 3.11+ com type hints
- Numba para loops críticos de performance
- Numpy para vetorização
- Matplotlib para visualizações

## Estrutura de diretórios

```
Renko_Gradiente/
├── src/                    # Código fonte do EA e engine
├── backtest/               # Scripts de backtest e otimização
├── config/                 # Configurações de parâmetros
├── reports/                # Relatórios JSON e gráficos PNG
├── docs/                   # Documentação adicional
├── ea_gradiente_renko.agent.final.pdf  # Especificação original
├── README.md
├── STATUS.md
├── MEMORY.md
└── CLAUDE.md
```

## Como rodar backtest

```bash
cd Renko_Gradiente
python backtest/run_backtest_annual.py
```

## Como adicionar nova configuração

1. Editar script em `backtest/`
2. Rodar e salvar JSON em `reports/`
3. Atualizar `STATUS.md` com métricas
4. Gerar gráfico se relevante

## Decisões arquiteturais já tomadas

- **Numba vs Python puro**: engine tick-a-tick usa Numba (`backtest_fast.py`) para performance; sinais e indicadores usam Python puro (`indicators.py`)
- **Renko builder**: implementação Nelogica-style (reversão requer 2× brick size)
- **Custos de transação**: slippage fixo em pontos + emolumentos % sobre valor financeiro
- **Horário**: filtrável via `start_time_ms` / `end_time_ms` na simulação Numba
- **EOD force-close**: engine Numba tem `force_close_eod` e `force_close_daily_stop` (defaults `False` por compat). Scripts NOVOS devem passar `True` para paridade com MQL5. Sem isso, posições abertas após `end_time_ms` são silenciosamente descartadas (bug histórico — ver STATUS).

## CAVEAT CRÍTICO — Viés do dataset sintético (LER ANTES de interpretar números)

- **Apenas 2026 são ticks REAIS** (86 dias coletados via ProfitDLL). 2021-2025 são **sintéticos**: OHLC M1 real do MT5 + ticks gerados via random walk com microestrutura condicional calibrada nos 86 dias reais de 2026.
- **Bias medido para essa estratégia (2026-05-26)**: gerando versão sintética dos mesmos 79 dias reais de 2026 (mesmo OHLC), o EA G72/SL0,30%/DS75 produziu PnL +R$ 3.968 (sintético) vs -R$ 8.789 (real). **Delta R$ 12.758 em 79 dias → ~R$ 40k/ano de sobre-estimação**.
- **Causa**: ticks sintéticos têm path intra-minuto mais oscilatório que real, criando ~2× mais Renko bricks (R=25, brick 120pts). Estratégia path-dependent com Renko grosso é o pior caso.
- **Implicação**: PnL acumulado reportado em 2021-2025 sintético deve ser interpretado como **otimista por ordem de magnitude**. Ranking RELATIVO entre configs (G72 > G80 etc) ainda preserva. Magnitudes absolutas só são confiáveis em 2026 (real).
- **Validação**: comparação detalhada em `reports/compare_real_vs_syn_2026.json`.

## Contato e contexto

- Projeto faz parte do ecossistema `EA-Trading` em `D:\_Projetos\EA-Trading\10_PROJETOS_EA\`
- Central de acompanhamento: `_Testes_e_Padroes` (somente leitura para este projeto)
- Dataset BTP: `C:\HIST_B3\generator_v3` (mantido por outro processo). 2026 real, 2021-2025 sintético — ver caveat acima.
- Gerador: `D:\_Projetos\EA-Trading\20_INFRA_E_DADOS\ProfitDLL_Coletor` (ler-only deste projeto)
