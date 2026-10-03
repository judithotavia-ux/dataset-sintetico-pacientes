# Comparação: dataset sintético × base pública real (UCI Heart Disease — Cleveland)

> As duas bases foram lidas de arquivos separados e **não foram combinadas**. O sintético não foi ajustado à base real.

- Sintético: `data\synthetic_dataset.csv` (n = 1000)
- Real: `data\real_public\uci_heart_disease\heart_disease_cleveland.csv` (n = 303) — Janosi, A., Steinbrunn, W., Pfisterer, M., & Detrano, R. (1989). Heart Disease [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C52P4X

## Variáveis numéricas em comum

| Variável | Sintético média (DP) | Real média (DP) | SMD | KS D | KS p | Wasserstein |
|---|---|---|---|---|---|---|
| Idade (anos) | 48.7 (14.8) | 54.44 (9.04) | -0.468 | 0.2339 | 1.17e-11 | 7.244 |
| PA sistólica (mmHg) | 118.22 (14.22) | 131.69 (17.6) | -0.842 | 0.379 | 2.33e-30 | 13.465 |
| Colesterol total (mg/dL) | 193.33 (30.67) | 246.69 (51.78) | -1.254 | 0.508 | 1.91e-55 | 53.36 |

## Proporções em comum

| Variável | Sintético | Real | z | p |
|---|---|---|---|---|
| Sexo masculino | 47.5% | 68.0% | -6.25 | 3.99e-10 |
| Glicemia de jejum > 120 mg/dL | 5.2% | 14.9% | -5.61 | 2.06e-08 |

## Modelos na base real — alvo `doenca_cardiaca` (prevalência 45.9%)

Validação: 5-fold estratificado repetido 10x (50 ajustes por modelo). Valores = média (desvio padrão).

| Modelo | ROC-AUC | Acurácia | F1 | Acurácia balanceada |
|---|---|---|---|---|
| Dummy (classe majoritária) | 0.5 (0.0) | 0.5413 (0.0053) | 0.0 (0.0) | 0.5 (0.0) |
| Regressão logística | 0.9104 (0.0317) | 0.8376 (0.0398) | 0.8157 (0.045) | 0.8336 (0.0398) |
| Random Forest | 0.9097 (0.0335) | 0.8281 (0.0501) | 0.8072 (0.0557) | 0.825 (0.0502) |

## Interpretação

- As diferenças de distribuição são **esperadas e não são defeito**: o gerador não foi calibrado com esta base,
  e a base UCI é de pacientes encaminhados para angiografia nos EUA em 1988 (mais velhos, mais homens, colesterol mais alto).
- SMD (diferença média padronizada) acima de 0,2 indica diferença pequena; acima de 0,5, média; acima de 0,8, grande.
- O KS testa se as duas amostras vêm da mesma distribuição; com amostras grandes, até diferenças pequenas ficam significativas.
- Os modelos na base real servem de **referência de desempenho em dados reais** para a pesquisa.
