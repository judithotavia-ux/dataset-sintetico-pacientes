# Resultados do experimento de referência (baseline)

> **DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES** — as métricas medem a capacidade dos modelos de recuperar a estrutura do gerador sintético; não têm validade clínica.

- Arquivo: `synthetic_dataset.csv` · seed dos modelos: `42`
- Partições: treino 699, validação 150, teste 151 (métricas reportadas no **teste**)
- Preditores: 19 numéricos + 18 categóricos/booleanos (excluídos alvos e variáveis derivadas deles)

## 1. Classificação binária — `desfecho_adverso` (prevalência no teste: 15.2%)

| Modelo | ROC-AUC | PR-AUC | F1 | Acurácia balanceada | Brier | Limiar (validação) |
|---|---|---|---|---|---|---|
| Dummy (classe majoritária) | 0.5 | 0.1523 | 0.2644 | 0.5 | 0.1297 | 0.05 |
| Regressão logística | 0.626 | 0.3671 | 0.3784 | 0.6248 | 0.2001 | 0.77 |
| Random Forest | 0.6101 | 0.3193 | 0.3793 | 0.6454 | 0.1354 | 0.34 |

## 2. Classificação multiclasse — `classificacao_risco`

| Modelo | Acurácia | Macro-F1 | Acurácia balanceada | Macro-F1 (validação) |
|---|---|---|---|---|
| Dummy (classe majoritária) | 0.3974 | 0.1422 | 0.25 | 0.1411 |
| Regressão logística multinomial | 0.7152 | 0.6754 | 0.6754 | 0.6965 |
| Random Forest | 0.6093 | 0.5121 | 0.5283 | 0.5948 |

Matriz de confusão (Random Forest, linhas = real, colunas = previsto):

| | BAIXO | MODERADO | ALTO | MUITO_ALTO |
|---|---|---|---|---|
| **BAIXO** | 55 | 2 | 3 | 0 |
| **MODERADO** | 17 | 3 | 9 | 0 |
| **ALTO** | 3 | 4 | 19 | 7 |
| **MUITO_ALTO** | 1 | 0 | 13 | 15 |

## 3. Regressão — `pa_sistolica` (mmHg)

| Modelo | MAE | RMSE | R² | R² (validação) |
|---|---|---|---|---|
| Dummy (média) | 11.472 | 14.462 | -0.0001 | -0.0176 |
| Ridge | 8.697 | 10.638 | 0.4588 | 0.3993 |
| Random Forest | 8.523 | 10.461 | 0.4767 | 0.4003 |

## Leitura

- Os modelos superam claramente as baselines *dummy*, o que confirma que o dataset contém relações aprendíveis.
- O desempenho não é perfeito porque o gerador inclui ruído aleatório em cada etapa, como em dados observacionais.
- Use estes números apenas como referência para comparar métodos dentro da pesquisa.
