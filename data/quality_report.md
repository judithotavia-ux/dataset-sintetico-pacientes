# Relatório de Qualidade — Dataset Sintético de Pacientes

> **DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES**

- Gerado em: 2026-10-03 00:17 UTC
- dataset_id: `c78e1dac-cc03-4759-8c05-976c472b9f8d`
- Seed: `42`
- Registros: **1000**
- Qualidade: **APROVADO**
- Privacidade: **CONFORME**

## Verificações de qualidade

| Verificação | Resultado |
|---|---|
| colunas_obrigatorias | OK |
| valores_ausentes | OK |
| tipos_de_dados | OK |
| intervalos_e_categorias | OK |
| imc | OK |
| pressao_arterial | OK |
| identificadores | OK |
| consistencia_interna | OK |

## Validação de privacidade (privacy_guard)

- compliant: `true`
- blocked_fields: nenhum
- warnings: nenhum

## Estatísticas descritivas (variáveis numéricas)

| Variável | Média | DP | Mín | P25 | Mediana | P75 | Máx |
|---|---|---|---|---|---|---|---|
| idade | 48.7 | 14.8 | 18.0 | 38.0 | 49.0 | 59.0 | 89.0 |
| peso_kg | 68.98 | 13.96 | 39.1 | 59.0 | 67.65 | 77.6 | 121.2 |
| altura_cm | 165.65 | 9.06 | 145.0 | 159.4 | 165.1 | 172.4 | 190.2 |
| imc | 25.08 | 4.32 | 16.49 | 22.04 | 24.84 | 27.93 | 39.04 |
| pa_sistolica | 118.22 | 14.22 | 85.0 | 108.0 | 117.0 | 128.0 | 163.0 |
| pa_diastolica | 71.5 | 9.52 | 50.0 | 65.0 | 71.0 | 78.0 | 100.0 |
| frequencia_cardiaca | 74.2 | 10.46 | 45.0 | 67.0 | 74.0 | 81.0 | 114.0 |
| temperatura_c | 36.75 | 0.6 | 35.6 | 36.4 | 36.6 | 36.9 | 40.1 |
| horas_sono | 6.97 | 1.12 | 4.0 | 6.2 | 6.9 | 7.7 | 10.0 |
| n_condicoes | 0.78 | 0.93 | 0.0 | 0.0 | 1.0 | 1.0 | 5.0 |
| n_medicamentos | 0.55 | 0.83 | 0.0 | 0.0 | 0.0 | 1.0 | 5.0 |
| glicemia_jejum | 93.9 | 19.35 | 60.0 | 83.9 | 90.6 | 97.72 | 219.1 |
| hba1c | 4.92 | 0.75 | 4.0 | 4.5 | 4.8 | 5.2 | 9.2 |
| colesterol_total | 193.33 | 30.67 | 110.0 | 173.38 | 193.2 | 212.52 | 304.7 |
| ldl | 117.61 | 33.11 | 30.0 | 97.4 | 117.55 | 138.02 | 226.5 |
| hdl | 50.5 | 10.8 | 20.0 | 43.28 | 50.5 | 57.6 | 90.9 |
| triglicerides | 126.49 | 54.84 | 35.0 | 89.82 | 115.4 | 150.72 | 539.3 |
| creatinina | 0.89 | 0.21 | 0.4 | 0.76 | 0.87 | 0.99 | 2.56 |
| hemoglobina | 13.92 | 1.25 | 9.7 | 13.0 | 13.95 | 14.8 | 18.2 |
| escore_risco | 22.88 | 22.33 | 0.5 | 6.2 | 14.55 | 32.4 | 95.5 |

## Distribuição das variáveis categóricas

- **sexo** — F: 525 (52.5%), M: 475 (47.5%)
- **estado** — RS: 77 (7.7%), RR: 68 (6.8%), PB: 66 (6.6%), SC: 52 (5.2%), MA: 48 (4.8%), TO: 47 (4.7%), ES: 45 (4.5%), PI: 44 (4.4%), RJ: 43 (4.3%), MG: 42 (4.2%), RO: 41 (4.1%), AP: 37 (3.7%), PR: 36 (3.6%), AC: 35 (3.5%), AM: 34 (3.4%), AL: 34 (3.4%), SE: 33 (3.3%), GO: 30 (3.0%), CE: 28 (2.8%), PE: 26 (2.6%), BA: 26 (2.6%), MS: 25 (2.5%), DF: 21 (2.1%), SP: 19 (1.9%), RN: 16 (1.6%), PA: 15 (1.5%), MT: 12 (1.2%)
- **hf_diabetes** — False: 744 (74.4%), True: 256 (25.6%)
- **hf_hipertensao** — False: 630 (63.0%), True: 370 (37.0%)
- **hf_doenca_cardiovascular** — False: 819 (81.9%), True: 181 (18.1%)
- **tabagismo** — NUNCA_FUMOU: 636 (63.6%), EX_FUMANTE: 187 (18.7%), FUMANTE_ATUAL: 177 (17.7%)
- **consumo_alcool** — NENHUM: 429 (42.9%), MODERADO: 427 (42.7%), ELEVADO: 144 (14.4%)
- **atividade_fisica** — SEDENTARIO: 435 (43.5%), MODERADA: 345 (34.5%), ATIVA: 220 (22.0%)
- **qualidade_dieta** — REGULAR: 518 (51.8%), RUIM: 252 (25.2%), BOA: 230 (23.0%)
- **cond_hipertensao** — False: 799 (79.9%), True: 201 (20.1%)
- **cond_diabetes_tipo_2** — False: 916 (91.6%), True: 84 (8.4%)
- **cond_dislipidemia** — False: 819 (81.9%), True: 181 (18.1%)
- **cond_obesidade** — False: 864 (86.4%), True: 136 (13.6%)
- **cond_asma** — False: 924 (92.4%), True: 76 (7.6%)
- **cond_doenca_renal_cronica** — False: 983 (98.3%), True: 17 (1.7%)
- **cond_infeccao_respiratoria_aguda** — False: 919 (91.9%), True: 81 (8.1%)
- **condicao_clinica** — SEM_CONDICAO_CRONICA: 485 (48.5%), HIPERTENSAO: 167 (16.7%), DISLIPIDEMIA: 97 (9.7%), DIABETES_TIPO_2: 76 (7.6%), INFECCAO_RESPIRATORIA_AGUDA: 62 (6.2%), OBESIDADE: 53 (5.3%), ASMA: 43 (4.3%), DOENCA_RENAL_CRONICA: 17 (1.7%)
- **aderencia_tratamento** — NAO_SE_APLICA: 620 (62.0%), ALTA: 213 (21.3%), MEDIA: 114 (11.4%), BAIXA: 53 (5.3%)
- **classificacao_risco** — BAIXO: 395 (39.5%), ALTO: 215 (21.5%), MODERADO: 198 (19.8%), MUITO_ALTO: 192 (19.2%)
- **resultado_desfecho** — SEM_INTERCORRENCIA: 867 (86.7%), INTERNACAO: 98 (9.8%), EVENTO_CARDIOVASCULAR: 28 (2.8%), OBITO: 7 (0.7%)
- **desfecho_adverso** — False: 867 (86.7%), True: 133 (13.3%)
- **split** — train: 699 (69.9%), test: 151 (15.1%), validation: 150 (15.0%)
- **research_only** — True: 1000 (100.0%)
