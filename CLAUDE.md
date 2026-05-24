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

## Contato e contexto

- Projeto faz parte do ecossistema `EA-Trading` em `D:\_Projetos\EA-Trading\10_PROJETOS_EA\`
- Central de acompanhamento: `_Testes_e_Padroes` (somente leitura para este projeto)
- Dataset BTP: `C:\HIST_B3\generator_v3` (mantido por outro processo)
