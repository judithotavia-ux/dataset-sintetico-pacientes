# Dataset Card — Synthetic Patients Dataset (SPD-BR)

> **DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES**

| Item | Valor |
|---|---|
| Versão | 1.0.0 |
| dataset_id | `e5d82f16-f486-4485-8aba-f325d5894f04` |
| Gerado em | 2026-10-03T02:48:01+00:00 |
| Registros | 10000 |
| Seed | 42 |
| data_type | `SYNTHETIC` |
| research_only | `true` |

## 1. Origem

Dados **100% sintéticos**, produzidos por um gerador estatístico local. Nenhum prontuário, sistema de saúde, pesquisa populacional, rede social ou qualquer fonte com dados pessoais foi consultado, copiado ou usado como molde. Os identificadores (`patient_id`, prefixo `SYN-`) são aleatórios e os municípios têm nomes inventados.

## 2. Finalidade

Uso acadêmico: testes, treinamento e validação de sistemas de Inteligência Artificial em pesquisa de mestrado.
Serve para desenvolver e testar pipelines (ingestão, pré-processamento, treinamento, avaliação), comparar algoritmos em um ambiente controlado e ensinar/demonstrar técnicas de ML sem expor dados de pacientes.

## 3. Variáveis

### Identificação

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `patient_id` | string | - | id | Identificador aleatório do paciente sintético (prefixo SYN-). Não tem relação com nenhum documento real. |

### Demografia

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `idade` | int | anos | feature | Idade em anos completos. |
| `sexo` | category | - | feature | Sexo biológico simulado (F/M). |
| `municipio` | string | - | meta | Município fictício (nome inventado, não corresponde a cidade real). |
| `estado` | category | - | feature | Unidade federativa (UF) sorteada para o registro sintético. |

### Antropometria

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `peso_kg` | float | kg | feature | Peso corporal. |
| `altura_cm` | float | cm | feature | Altura. |
| `imc` | float | kg/m² | feature | Índice de massa corporal = peso_kg / (altura_cm/100)^2. |

### Sinais vitais

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `pa_sistolica` | int | mmHg | feature | Pressão arterial sistólica. |
| `pa_diastolica` | int | mmHg | feature | Pressão arterial diastólica (sempre menor que a sistólica). |
| `frequencia_cardiaca` | int | bpm | feature | Frequência cardíaca em repouso. |
| `temperatura_c` | float | °C | feature | Temperatura axilar. |

### Histórico familiar

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `hf_diabetes` | bool | - | feature | Histórico familiar sintético de diabetes. |
| `hf_hipertensao` | bool | - | feature | Histórico familiar sintético de hipertensão. |
| `hf_doenca_cardiovascular` | bool | - | feature | Histórico familiar sintético de doença cardiovascular. |
| `historico_familiar` | string | - | meta | Resumo textual do histórico familiar sintético. |

### Hábitos de vida

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `tabagismo` | category | - | feature | Hábito de tabagismo simulado. |
| `consumo_alcool` | category | - | feature | Consumo de álcool simulado. |
| `atividade_fisica` | category | - | feature | Nível de atividade física simulado. |
| `qualidade_dieta` | category | - | feature | Qualidade da dieta simulada. |
| `horas_sono` | float | h | feature | Média de horas de sono por noite. |

### Condição clínica

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `cond_hipertensao` | bool | - | feature | Condição simulada: hipertensão arterial. |
| `cond_diabetes_tipo_2` | bool | - | feature | Condição simulada: diabetes tipo 2. |
| `cond_dislipidemia` | bool | - | feature | Condição simulada: dislipidemia. |
| `cond_obesidade` | bool | - | feature | Condição simulada: obesidade (derivada de IMC >= 30). |
| `cond_asma` | bool | - | feature | Condição simulada: asma. |
| `cond_doenca_renal_cronica` | bool | - | feature | Condição simulada: doença renal crônica. |
| `cond_infeccao_respiratoria_aguda` | bool | - | feature | Condição aguda simulada: infecção respiratória (com febre). |
| `n_condicoes` | int | - | feature | Quantidade de condições simuladas presentes. |
| `condicao_clinica` | category | - | feature | Condição clínica principal simulada (a de maior prioridade presente). |

### Medicamentos

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `medicamentos` | string | - | meta | Medicamentos simulados prescritos, separados por '; ' (vazio = nenhum). |
| `n_medicamentos` | int | - | feature | Quantidade de medicamentos simulados. |
| `aderencia_tratamento` | category | - | feature | Aderência simulada ao tratamento medicamentoso. |

### Exames laboratoriais

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `glicemia_jejum` | float | mg/dL | feature | Exame simulado: glicemia de jejum. |
| `hba1c` | float | % | feature | Exame simulado: hemoglobina glicada. |
| `colesterol_total` | float | mg/dL | feature | Exame simulado: colesterol total. |
| `ldl` | float | mg/dL | feature | Exame simulado: LDL (estimado por Friedewald quando TG < 400). |
| `hdl` | float | mg/dL | feature | Exame simulado: HDL. |
| `triglicerides` | float | mg/dL | feature | Exame simulado: triglicerídeos. |
| `creatinina` | float | mg/dL | feature | Exame simulado: creatinina sérica. |
| `hemoglobina` | float | g/dL | feature | Exame simulado: hemoglobina. |

### Atendimento

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `data_atendimento` | date | - | meta | Data fictícia do atendimento (AAAA-MM-DD). |

### Risco, diagnóstico e desfecho

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `escore_risco` | float | pontos | target | Escore de risco sintético (0–100). Não é escore clínico validado. |
| `classificacao_risco` | category | - | target | Classificação de risco derivada do escore sintético. |
| `diagnostico_sintetico` | string | - | target | Diagnóstico textual simulado (condição principal + situação de controle). |
| `resultado_desfecho` | category | - | target | Desfecho simulado em 12 meses. |
| `desfecho_adverso` | bool | - | target | Indicador binário de desfecho adverso (qualquer desfecho diferente de SEM_INTERCORRENCIA). |

### Aprendizado de máquina

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `split` | category | - | meta | Partição para ML: train (70%), validation (15%), test (15%), estratificada por classificacao_risco. |

### Governança

| Variável | Tipo | Unidade | Papel em ML | Descrição |
|---|---|---|---|---|
| `data_type` | category | - | meta | Marcação obrigatória: todo registro é SYNTHETIC. |
| `research_only` | bool | - | meta | Marcação obrigatória: uso exclusivo em pesquisa (sempre true). |

Alvos sugeridos: `desfecho_adverso` (classificação binária), `classificacao_risco` (multiclasse), `resultado_desfecho` (multiclasse desbalanceada), `escore_risco` / `pa_sistolica` / `hba1c` (regressão).

Resumo deste arquivo: classificação de risco — BAIXO: 37.3%, ALTO: 22.0%, MUITO_ALTO: 20.7%, MODERADO: 20.0%; desfecho adverso em 12 meses: 12.7%.

## 4. Método de geração

Simulação estatística paramétrica com modelo causal simplificado e fictício: idade, sexo, hábitos de vida e histórico familiar influenciam IMC; estes influenciam a probabilidade (função logística) de condições clínicas; condições determinam medicamentos e aderência; sinais vitais e exames dependem das condições e do efeito do tratamento; um escore de risco sintético define a classificação de risco e a probabilidade de desfecho em 12 meses. Toda a aleatoriedade deriva de um único seed (NumPy Generator PCG64 + Faker pt_BR para identificadores e nomes de municípios inventados). Nenhum dado real foi usado como entrada, molde ou referência individual.

Particionamento: 70% treino, 15% validação, 15% teste, estratificado por `classificacao_risco` (coluna `split`). O mesmo seed reproduz exatamente o mesmo dataset e a mesma partição.

## 5. Limitações

- Os dados são inteiramente sintéticos: não representam nenhuma população real e não servem para estimar prevalências, riscos ou efeitos de tratamento reais.
- Os coeficientes do modelo de geração foram escolhidos para produzir valores plausíveis, não estimados de estudos clínicos; relações entre variáveis são simplificadas.
- O escore_risco e a classificacao_risco são construções sintéticas e NÃO equivalem a escores clínicos validados (ex.: Framingham, SCORE2).
- Variáveis independentes entre si no gerador (ex.: estado, municipio, data_atendimento) não carregam sinal preditivo.
- Não há séries temporais longitudinais: cada paciente possui um único atendimento fictício.
- Modelos treinados apenas com estes dados não devem ser usados em decisões clínicas nem considerados validados para uso real.
- Desempenho de modelos neste dataset reflete a estrutura do gerador; resultados precisam ser validados em dados reais devidamente autorizados antes de qualquer conclusão clínica.

## 6. Riscos de uso

- **Falsa sensação de validade clínica:** métricas altas aqui não indicam que um modelo funcionaria com pacientes reais.
- **Vazamento de alvo:** `escore_risco`, `classificacao_risco`, `diagnostico_sintetico` e `resultado_desfecho` são derivados uns dos outros; não use um como preditor do outro sem intenção explícita.
- **Viés do gerador:** o modelo reflete as escolhas do autor do gerador (coeficientes, categorias), não a realidade epidemiológica.
- **Mistura com dados reais:** combinar este dataset com dados reais pode criar registros ambíguos; mantenha sempre `data_type = SYNTHETIC`.

## 7. Usos permitidos

- Pesquisa acadêmica, ensino e prototipagem de modelos de IA.
- Testes de software, de pipelines de dados e de mecanismos de privacidade.
- Análise exploratória, comparação de algoritmos, estudos de reprodutibilidade.

## 8. Usos não recomendados

- Apoio a decisão clínica, diagnóstico ou tratamento de pessoas reais.
- Estimativa de prevalência, incidência ou risco de qualquer população real.
- Publicação de resultados como se fossem evidência clínica.
- Remover as colunas `data_type`/`research_only` ou apresentar os dados como reais.
- Enriquecer os registros com dados pessoais reais (CPF, nome, contato, endereço etc.).

## 9. Privacidade

Validação do `privacy_guard`: compliant = `true`, campos bloqueados = nenhum.
