# Relatório de Qualidade — Dataset Sintético de Pacientes

> **DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES**

- Gerado em: 2026-10-03 02:48 UTC
- dataset_id: `e5d82f16-f486-4485-8aba-f325d5894f04`
- Seed: `42`
- Registros: **10000**
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
| idade | 48.99 | 15.11 | 18.0 | 38.0 | 48.0 | 59.0 | 90.0 |
| peso_kg | 69.72 | 14.1 | 38.0 | 59.7 | 68.8 | 78.7 | 144.3 |
| altura_cm | 165.96 | 8.97 | 145.0 | 159.4 | 165.7 | 172.4 | 200.0 |
| imc | 25.23 | 4.23 | 16.48 | 22.27 | 25.16 | 28.05 | 41.52 |
| pa_sistolica | 118.78 | 14.23 | 85.0 | 109.0 | 118.0 | 128.0 | 181.0 |
| pa_diastolica | 71.47 | 9.48 | 50.0 | 65.0 | 71.0 | 78.0 | 106.0 |
| frequencia_cardiaca | 74.34 | 10.34 | 45.0 | 67.0 | 74.0 | 81.0 | 114.0 |
| temperatura_c | 36.73 | 0.57 | 35.5 | 36.4 | 36.6 | 36.9 | 40.0 |
| horas_sono | 6.98 | 1.1 | 4.0 | 6.2 | 7.0 | 7.7 | 10.0 |
| n_condicoes | 0.79 | 0.92 | 0.0 | 0.0 | 1.0 | 1.0 | 6.0 |
| n_medicamentos | 0.59 | 0.86 | 0.0 | 0.0 | 0.0 | 1.0 | 7.0 |
| glicemia_jejum | 94.0 | 19.35 | 60.0 | 84.3 | 90.8 | 97.6 | 282.5 |
| hba1c | 4.91 | 0.74 | 4.0 | 4.5 | 4.8 | 5.2 | 11.6 |
| colesterol_total | 194.03 | 30.88 | 110.0 | 173.2 | 193.3 | 214.2 | 325.6 |
| ldl | 117.65 | 32.78 | 30.0 | 95.0 | 117.4 | 139.7 | 244.9 |
| hdl | 50.28 | 10.81 | 20.0 | 43.0 | 50.2 | 57.7 | 88.3 |
| triglicerides | 131.51 | 58.85 | 35.0 | 91.6 | 119.6 | 158.02 | 722.0 |
| creatinina | 0.9 | 0.21 | 0.4 | 0.77 | 0.89 | 1.01 | 3.45 |
| hemoglobina | 13.97 | 1.29 | 9.0 | 13.1 | 14.0 | 14.9 | 18.9 |
| escore_risco | 23.69 | 22.45 | 0.2 | 6.3 | 15.5 | 34.42 | 99.3 |

## Distribuição das variáveis categóricas

- **sexo** — F: 5026 (50.3%), M: 4974 (49.7%)
- **estado** — GO: 892 (8.9%), MS: 741 (7.4%), RJ: 723 (7.2%), CE: 707 (7.1%), DF: 603 (6.0%), PA: 577 (5.8%), SC: 533 (5.3%), TO: 516 (5.2%), RR: 514 (5.1%), RN: 430 (4.3%), SE: 425 (4.2%), AC: 417 (4.2%), AP: 396 (4.0%), AM: 331 (3.3%), PR: 316 (3.2%), PI: 257 (2.6%), MG: 248 (2.5%), MT: 235 (2.4%), BA: 207 (2.1%), PB: 191 (1.9%), SP: 176 (1.8%), ES: 173 (1.7%), RO: 153 (1.5%), MA: 82 (0.8%), AL: 79 (0.8%), RS: 78 (0.8%)
- **hf_diabetes** — False: 7496 (75.0%), True: 2504 (25.0%)
- **hf_hipertensao** — False: 6568 (65.7%), True: 3432 (34.3%)
- **hf_doenca_cardiovascular** — False: 8226 (82.3%), True: 1774 (17.7%)
- **tabagismo** — NUNCA_FUMOU: 6269 (62.7%), FUMANTE_ATUAL: 1914 (19.1%), EX_FUMANTE: 1817 (18.2%)
- **consumo_alcool** — MODERADO: 4351 (43.5%), NENHUM: 4168 (41.7%), ELEVADO: 1481 (14.8%)
- **atividade_fisica** — SEDENTARIO: 4499 (45.0%), MODERADA: 3483 (34.8%), ATIVA: 2018 (20.2%)
- **qualidade_dieta** — REGULAR: 4978 (49.8%), RUIM: 2550 (25.5%), BOA: 2472 (24.7%)
- **cond_hipertensao** — False: 7579 (75.8%), True: 2421 (24.2%)
- **cond_diabetes_tipo_2** — False: 9193 (91.9%), True: 807 (8.1%)
- **cond_dislipidemia** — False: 8266 (82.7%), True: 1734 (17.3%)
- **cond_obesidade** — False: 8656 (86.6%), True: 1344 (13.4%)
- **cond_asma** — False: 9262 (92.6%), True: 738 (7.4%)
- **cond_doenca_renal_cronica** — False: 9858 (98.6%), True: 142 (1.4%)
- **cond_infeccao_respiratoria_aguda** — False: 9274 (92.7%), True: 726 (7.3%)
- **condicao_clinica** — SEM_CONDICAO_CRONICA: 4697 (47.0%), HIPERTENSAO: 2066 (20.7%), DISLIPIDEMIA: 973 (9.7%), DIABETES_TIPO_2: 761 (7.6%), INFECCAO_RESPIRATORIA_AGUDA: 519 (5.2%), OBESIDADE: 465 (4.7%), ASMA: 377 (3.8%), DOENCA_RENAL_CRONICA: 142 (1.4%)
- **aderencia_tratamento** — NAO_SE_APLICA: 6106 (61.1%), ALTA: 2154 (21.5%), MEDIA: 1193 (11.9%), BAIXA: 547 (5.5%)
- **classificacao_risco** — BAIXO: 3731 (37.3%), ALTO: 2197 (22.0%), MUITO_ALTO: 2074 (20.7%), MODERADO: 1998 (20.0%)
- **resultado_desfecho** — SEM_INTERCORRENCIA: 8729 (87.3%), INTERNACAO: 919 (9.2%), EVENTO_CARDIOVASCULAR: 302 (3.0%), OBITO: 50 (0.5%)
- **desfecho_adverso** — False: 8729 (87.3%), True: 1271 (12.7%)
- **split** — train: 7001 (70.0%), validation: 1501 (15.0%), test: 1498 (15.0%)
- **research_only** — True: 10000 (100.0%)
