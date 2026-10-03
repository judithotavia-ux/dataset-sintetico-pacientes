# Metodologia — uso do dataset sintético em uma pesquisa de mestrado em Inteligência Artificial

> **DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES**

Este documento descreve como o *Synthetic Patients Dataset (SPD-BR)* pode ser empregado em uma pesquisa de
mestrado em IA aplicada à saúde, do problema de pesquisa à reprodutibilidade. Ele pode ser adaptado para o
capítulo de metodologia da dissertação.

---

## 1. Problema de pesquisa

Pesquisas de IA em saúde dependem de dados clínicos, mas o acesso a prontuários reais exige aprovação ética
(CEP/CONEP), bases legais da LGPD (Lei 13.709/2018, art. 11 — dados pessoais sensíveis), acordos institucionais
e infraestrutura segura. Isso atrasa ou impede as etapas iniciais de pesquisa: desenho de pipelines, escolha
de algoritmos, testes de software e ensino.

**Pergunta norteadora (exemplo):** *é possível desenvolver e avaliar comparativamente um pipeline de
predição de desfecho adverso e de estratificação de risco usando exclusivamente dados sintéticos, de modo
que o pipeline esteja pronto para ser validado posteriormente em dados reais autorizados?*

Outras perguntas compatíveis com o dataset:

- Qual família de modelos (lineares, árvores, ensembles) melhor recupera relações não lineares e interações
  conhecidas *a priori* (as do gerador)?
- Como técnicas de balanceamento afetam a detecção de um desfecho raro (≈ 13% de prevalência; óbito < 1%)?
- Métodos de explicabilidade (coeficientes, importância por permutação, SHAP) identificam corretamente as
  variáveis que o gerador de fato usa? Como o dataset tem "verdade conhecida", ele permite **validar métodos de
  explicabilidade**, algo impossível em dados reais.
- Qual o impacto do tamanho amostral (100 → 100.000) na estabilidade das métricas?

## 2. Geração dos dados

- **Ferramenta:** aplicação local deste repositório (painel web ou `scripts/generate_dataset.py`).
- **Método:** simulação estatística paramétrica com modelo causal simplificado (ver `docs/arquitetura.md`, seção 5):
  demografia e hábitos → antropometria → condições (logística) → tratamento → sinais vitais e exames →
  escore de risco → desfecho.
- **Tamanhos:** 100, 1.000, 10.000 ou 100.000 pacientes.
- **Reprodutibilidade:** um único `seed` controla toda a aleatoriedade (NumPy PCG64 + Faker).
- **Marcação:** toda linha tem `data_type = "SYNTHETIC"` e `research_only = true`.
- **Ausência de dados reais:** nenhuma fonte com dados pessoais é consultada; os coeficientes foram escolhidos
  para plausibilidade, não estimados de uma população.

Recomenda-se registrar na dissertação: versão do gerador (`generator_version`), seed, tamanho, data de geração
e o `dataset_id` — todos presentes em `metadata.json`.

## 3. Preparação dos dados

1. **Leitura:** `data/synthetic_dataset.csv` (com a coluna `split`) ou `data/splits/{train,validation,test}.csv`.
   Para ≥ 10.000 registros, prefira **Parquet** (tipos preservados, arquivo menor).
2. **Seleção de variáveis por papel** (`ml_role` em `metadata.json`):
   - `id`: `patient_id` — nunca usar como preditor.
   - `meta`: `municipio`, `historico_familiar` (texto), `medicamentos` (texto), `data_atendimento`, `split`,
     `data_type`, `research_only` — fora do modelo (ou usar após engenharia de atributos justificada).
   - `feature`: 37 preditores (19 numéricos + 18 categóricos/booleanos).
   - `target`: `desfecho_adverso`, `resultado_desfecho`, `classificacao_risco`, `escore_risco`, `diagnostico_sintetico`.
3. **Controle de vazamento (leakage):** os alvos são derivados uns dos outros (`escore_risco` → `classificacao_risco`;
   `resultado_desfecho` ↔ `desfecho_adverso`; `diagnostico_sintetico` contém a condição principal). Ao prever um
   alvo, remova os demais. Em regressão de `pa_sistolica`, remova `pa_diastolica` (gerada a partir da sistólica).
4. **Transformações:** padronização (z-score) das numéricas ajustada **somente no treino**; one-hot nas categóricas
   (`handle_unknown="ignore"`). Use `Pipeline` do scikit-learn para garantir que nada da validação/teste vaze.
5. **Desbalanceamento:** `desfecho_adverso` ≈ 13% positivos. Considere `class_weight="balanced"`, reamostragem
   (apenas no treino) e métricas adequadas (PR-AUC, F1).

## 4. Treinamento de modelos

- **Partição fixa:** 70% treino, 15% validação, 15% teste, estratificada por `classificacao_risco`
  (coluna `split`). Use o **teste uma única vez**, ao final.
- **Seleção de hiperparâmetros:** busca (grid/random/bayesiana) avaliada no conjunto de validação, ou validação
  cruzada estratificada (k = 5) dentro do treino.
- **Modelos sugeridos (do mais simples ao mais complexo):** baseline *dummy* → regressão logística / Ridge →
  árvores de decisão → Random Forest / Gradient Boosting (XGBoost, LightGBM) → redes neurais (MLP).
- **Ponto de partida pronto:** `scripts/baseline_experiment.py` treina e avalia três tarefas.

Resultados do baseline (seed 42, 10.000 pacientes, métricas no teste):

| Tarefa | Melhor modelo | Métrica principal | Dummy |
|---|---|---|---|
| Classificação binária `desfecho_adverso` | Random Forest | ROC-AUC 0,794 · PR-AUC 0,401 | 0,500 · 0,129 |
| Multiclasse `classificacao_risco` | Regressão logística multinomial | Macro-F1 0,775 | 0,136 |
| Regressão `pa_sistolica` | Ridge | R² 0,509 · MAE 8,1 mmHg | R² 0,00 · MAE 11,5 |

Os valores não são perfeitos porque o gerador inclui ruído em cada etapa, como em dados observacionais. Não são
evidência clínica: medem a capacidade de recuperar a estrutura do gerador.

## 5. Validação

1. **Validação interna:** desempenho no conjunto de validação para escolher modelos e limiares (por exemplo,
   o limiar de decisão que maximiza o F1 é escolhido na validação, não no teste).
2. **Avaliação final:** uma única medição no teste, com **intervalos de confiança por bootstrap** (por exemplo,
   1.000 reamostragens).
3. **Robustez:** repita o experimento com **vários seeds** (ex.: 10 datasets independentes) e reporte média ± desvio
   padrão. Isso separa o efeito do método da variação amostral.
4. **Curva de aprendizado:** compare 1.000, 10.000 e 100.000 registros.
5. **Validação dos dados:** antes de treinar, rode `scripts/quality_report.py` e registre o resultado
   (qualidade APROVADA e privacidade CONFORME).
6. **Validação externa (fora deste projeto):** qualquer conclusão sobre aplicabilidade clínica exige
   validação em dados reais, com aprovação ética e base legal adequada.

## 6. Métricas

| Tarefa | Métricas recomendadas |
|---|---|
| Classificação binária (desbalanceada) | ROC-AUC, **PR-AUC**, F1, sensibilidade, especificidade, acurácia balanceada, **Brier score** e curva de calibração |
| Multiclasse ordinal (risco) | **macro-F1**, acurácia balanceada, matriz de confusão, kappa de Cohen ponderado (a ordem das classes importa) |
| Regressão | MAE, RMSE, R² |
| Explicabilidade | concordância entre importâncias estimadas e as variáveis efetivamente usadas pelo gerador |
| Justiça (opcional) | diferença de desempenho entre sexos e faixas etárias |

Evite reportar apenas acurácia em problemas desbalanceados: um modelo que sempre prevê "sem desfecho" teria ≈ 87%.

## 7. Limitações

- Os dados **não representam nenhuma população real**; prevalências e efeitos são construções do gerador.
- Os coeficientes foram escolhidos por plausibilidade, não estimados de estudos.
- O escore de risco é sintético e não equivale a escores validados (Framingham, SCORE2 etc.).
- As relações são mais "limpas" que na realidade: não há erro de medição sistemático, dados ausentes
  informativos, viés de seleção, mudanças de protocolo ou registros incoerentes.
- Um único atendimento por paciente: não há séries temporais.
- Municípios, UF e data do atendimento não carregam sinal preditivo.
- Bom desempenho aqui **não** garante bom desempenho em dados reais (*domain shift*).

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Interpretar resultados como evidência clínica | avisos permanentes no painel, nos arquivos e na Dataset Card; texto explícito na dissertação |
| Vazamento de alvo | lista de variáveis derivadas (seção 3) e baseline que já as exclui |
| Viés do gerador incorporado ao modelo | declarar o gerador como premissa; validar em dados reais antes de qualquer uso |
| Mistura com dados reais | colunas `data_type`/`research_only` obrigatórias; `privacy_guard` bloqueia exportação sem marcação |
| Inserção indevida de dados pessoais | API rejeita campos proibidos; exportação bloqueada; auditoria técnica |
| Reidentificação | não se aplica: não há pessoas reais por trás dos registros |

## 9. Privacidade

- **Natureza dos dados:** sintéticos desde a origem. Não há titular de dados, então não há dado pessoal no
  sentido da LGPD (art. 5º, I). Por isso o dataset pode ser compartilhado com orientador, banca e repositórios.
- **Privacidade desde a concepção (*privacy by design*):** o esquema não tem campos de identificação; a
  minimização é estrutural (idade em vez de data de nascimento; município inventado em vez de endereço).
- **privacy_guard:** bloqueia campos proibidos pelo nome e pelo conteúdo, exige a marcação SYNTHETIC, impede
  exportação não conforme e registra apenas logs técnicos.
- **Sintético × anonimizado × pseudonimizado** (ver README): dados anonimizados e pseudonimizados **derivam de
  pessoas reais**; estes não.
- **Se a pesquisa evoluir para dados reais:** isso exige uma etapa própria de governança, fora deste sistema.
  Inclui aprovação no CEP, base legal (LGPD art. 11, II, "c": estudos por órgão de pesquisa, com anonimização
  sempre que possível), termo de uso de dados, ambiente seguro e registro das operações. Este sistema
  deliberadamente **não** oferece funcionalidade para importar dados reais.

## 10. Reprodutibilidade

Para reproduzir exatamente qualquer resultado:

1. Mesma versão do código: registre o commit do repositório.
2. Mesmas dependências: as versões estão fixadas em `backend/requirements.txt` e no `frontend/package-lock.json`.
3. Mesmo dataset: `python scripts/generate_dataset.py --n 10000 --seed 42`. O mesmo seed gera o mesmo dataset
   de forma idêntica (verificado em `tests/test_generator.py::test_mesmo_seed_reproduz_exatamente`).
4. Mesma partição: a coluna `split` também é determinada pelo seed.
5. Mesmos modelos: `python scripts/baseline_experiment.py --input <arquivo> --seed 42`.
6. Registro dos artefatos: guarde junto aos resultados `metadata.json` (seed, versão, data, dataset_id),
   `quality_report.md`, `privacy_report.json` e `baseline_results.json`.
7. Ambiente: Python 3.12, Node 20+; opcionalmente `docker compose up --build`.

Sugestão de texto para a dissertação:

> "Os experimentos utilizaram o *Synthetic Patients Dataset (SPD-BR)* v1.0.0, composto por N pacientes
> inteiramente sintéticos gerados com seed S (gerador v1.0.0), particionados em 70/15/15 de forma estratificada
> pela classificação de risco. Nenhum dado real de paciente foi utilizado. O dataset foi aprovado nas
> verificações automáticas de qualidade e de privacidade (privacy_guard)."
