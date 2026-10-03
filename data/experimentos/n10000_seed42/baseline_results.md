# Resultados do experimento de referência (baseline)

> **DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES** — as métricas medem a capacidade dos modelos de recuperar a estrutura do gerador sintético; não têm validade clínica.

- Arquivo: `synthetic_dataset.csv` · seed dos modelos: `42`
- Partições: treino 7001, validação 1501, teste 1498 (métricas reportadas no **teste**)
- Preditores: 19 numéricos + 18 categóricos/booleanos (excluídos alvos e variáveis derivadas deles)

## 1. Classificação binária — `desfecho_adverso` (prevalência no teste: 12.9%)

| Modelo | ROC-AUC | PR-AUC | F1 | Acurácia balanceada | Brier | Limiar (validação) |
|---|---|---|---|---|---|---|
| Dummy (classe majoritária) | 0.5 | 0.1288 | 0.2283 | 0.5 | 0.1122 | 0.05 |
| Regressão logística | 0.7811 | 0.3844 | 0.3717 | 0.6314 | 0.1853 | 0.75 |
| Random Forest | 0.7939 | 0.4013 | 0.4074 | 0.6581 | 0.108 | 0.44 |

## 2. Classificação multiclasse — `classificacao_risco`

| Modelo | Acurácia | Macro-F1 | Acurácia balanceada | Macro-F1 (validação) |
|---|---|---|---|---|
| Dummy (classe majoritária) | 0.3732 | 0.1359 | 0.25 | 0.1359 |
| Regressão logística multinomial | 0.7991 | 0.775 | 0.7757 | 0.7918 |
| Random Forest | 0.7236 | 0.6675 | 0.6761 | 0.669 |

Matriz de confusão (Random Forest, linhas = real, colunas = previsto):

| | BAIXO | MODERADO | ALTO | MUITO_ALTO |
|---|---|---|---|---|
| **BAIXO** | 528 | 24 | 7 | 0 |
| **MODERADO** | 117 | 82 | 97 | 3 |
| **ALTO** | 15 | 37 | 220 | 57 |
| **MUITO_ALTO** | 0 | 1 | 56 | 254 |

## 3. Regressão — `pa_sistolica` (mmHg)

| Modelo | MAE | RMSE | R² | R² (validação) |
|---|---|---|---|---|
| Dummy (média) | 11.519 | 14.514 | -0.0 | -0.0004 |
| Ridge | 8.075 | 10.175 | 0.5085 | 0.4841 |
| Random Forest | 8.226 | 10.359 | 0.4906 | 0.4744 |

## Leitura

- Os modelos superam claramente as baselines *dummy*, o que confirma que o dataset contém relações aprendíveis.
- O desempenho não é perfeito porque o gerador inclui ruído aleatório em cada etapa, como em dados observacionais.
- Use estes números apenas como referência para comparar métodos dentro da pesquisa.
