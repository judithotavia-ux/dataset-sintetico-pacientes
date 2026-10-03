# Dataset Card — UCI Heart Disease — Cleveland (base pública real)

> **DADOS REAIS, PÚBLICOS E ANONIMIZADOS NA ORIGEM** · `data_type = REAL_PUBLIC_ANONYMIZED` · separados do dataset sintético

## Origem

- **Repositório:** UCI Machine Learning Repository — https://archive.ics.uci.edu/dataset/45/heart+disease
- **Coleta:** Cleveland Clinic Foundation (pesquisador responsável: Robert Detrano, M.D., Ph.D.), coleta de 1988
- **Licença:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **DOI:** https://doi.org/10.24432/C52P4X
- **Arquivo usado:** `processed.cleveland.data` (SHA-256 `a74b7efa387bc9d108d7d0115d831fe9b414b29ae7124f331b622b4efa0427c8`)

**Citação obrigatória (CC BY 4.0):**

> Janosi, A., Steinbrunn, W., Pfisterer, M., & Detrano, R. (1989). Heart Disease [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C52P4X

## Anonimização

Segundo a documentação do repositório (heart-disease.names), nomes e números de seguridade social dos pacientes foram removidos e substituídos por valores fictícios. O arquivo processado contém apenas 14 atributos clínicos, sem identificadores.
Este projeto não adicionou nenhum identificador pessoal: `registro_id` é um número sequencial criado aqui.

## Conteúdo

- Registros: **303** (completos: 297).
- Prevalência de doença cardíaca (grau_doenca > 0): **45.9%**.
- Valores ausentes: n_vasos_fluoroscopia: 4, cintilografia_talio: 2.

| Variável | Atributo original | Tipo | Unidade | Descrição |
|---|---|---|---|---|
| `registro_id` | — | string | - | Identificador sequencial criado neste projeto (UCI-CLE-0001…). Não existe na base original. |
| `idade` | age | int | anos | Idade em anos. |
| `sexo` | sex | category | - | Sexo (original: 1 = masculino, 0 = feminino). |
| `tipo_dor_toracica` | cp | category | - | Tipo de dor torácica: angina típica, atípica, dor não anginosa ou assintomático. |
| `pa_sistolica_repouso` | trestbps | int | mmHg | Pressão arterial sistólica em repouso na admissão. |
| `colesterol_total` | chol | int | mg/dL | Colesterol sérico total. |
| `glicemia_jejum_maior_120` | fbs | bool | - | Glicemia de jejum > 120 mg/dL. |
| `ecg_repouso` | restecg | category | - | Eletrocardiograma em repouso: normal, anormalidade ST-T ou hipertrofia ventricular esquerda. |
| `freq_cardiaca_maxima` | thalach | int | bpm | Frequência cardíaca máxima atingida no teste de esforço. |
| `angina_exercicio` | exang | bool | - | Angina induzida pelo exercício. |
| `depressao_st` | oldpeak | float | mm | Depressão do segmento ST induzida pelo exercício em relação ao repouso. |
| `inclinacao_st` | slope | category | - | Inclinação do segmento ST no pico do exercício. |
| `n_vasos_fluoroscopia` | ca | int | vasos | Número de vasos principais (0–3) coloridos na fluoroscopia. |
| `cintilografia_talio` | thal | category | - | Resultado da cintilografia com tálio: normal, defeito fixo ou reversível. |
| `grau_doenca` | num | int | - | Diagnóstico angiográfico original (0 = sem estreitamento > 50%; 1–4 = presença, por grau). |
| `doenca_cardiaca` | — | bool | - | Alvo binário derivado: grau_doenca > 0 (convenção usada na literatura). |
| `fonte` | — | string | - | Nome da base de origem. |
| `data_type` | — | category | - | Marcação obrigatória: REAL_PUBLIC_ANONYMIZED (dado real, público e anonimizado na origem). |
| `research_only` | — | bool | - | Uso exclusivo em pesquisa (sempre true). |

## Usos neste projeto

- Comparar distribuições das variáveis em comum com o dataset sintético (idade, sexo, pressão sistólica, colesterol, glicemia).
- Servir de referência de desempenho de modelos em dados reais (alvo: `doenca_cardiaca`).

## Limitações

- Amostra pequena (303) de um único centro nos EUA, coletada em 1988; não representa a população brasileira atual.
- Pacientes encaminhados para angiografia: há viés de seleção (prevalência de doença muito maior que na população geral).
- Predominância masculina (≈ 68%).
- As variáveis não são idênticas às do dataset sintético (ex.: frequência cardíaca máxima no esforço × frequência em repouso).
