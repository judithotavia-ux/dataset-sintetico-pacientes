# Gerador de Dataset Sintético de Pacientes (SPD-BR)

> ## ⚠ DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES
> Todos os registros são fictícios e gerados artificialmente, apenas para pesquisa acadêmica.
> Não use estes dados em decisões clínicas.

Aplicação local para gerar, validar e exportar um **dataset sintético de pacientes** voltado a testes,
treinamento e validação de sistemas de Inteligência Artificial em uma pesquisa de mestrado.

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite, Pydantic, Faker, Pandas
- **Frontend:** React, Vite, TypeScript, Tailwind CSS (painel com gráficos)
- **Privacidade:** camada `privacy_guard`, que bloqueia campos de identificação e impede exportação não conforme
- **ML pronto:** partição 70/15/15 estratificada, seed configurável, experimento baseline com scikit-learn
- **Testes:** 177 testes automatizados (pytest)

---

## Sumário

1. [Os dados são sintéticos](#1-os-dados-são-sintéticos)
2. [Como os dados são gerados](#2-como-os-dados-são-gerados)
3. [Como executar o projeto](#3-como-executar-o-projeto)
4. [Como gerar novos datasets](#4-como-gerar-novos-datasets)
5. [Como usar os dados em experimentos de IA](#5-como-usar-os-dados-em-experimentos-de-ia)
6. [Limitações](#6-limitações)
7. [Cuidados com dados pessoais](#7-cuidados-com-dados-pessoais)
8. [Sintético × anonimizado × pseudonimizado](#8-diferença-entre-dados-sintéticos-anonimizados-e-pseudonimizados)
9. [Estrutura do projeto](#9-estrutura-do-projeto)
10. [Testes](#10-testes)

---

## 1. Os dados são sintéticos

- Nenhum dado real foi usado: não há scraping, prontuários, bases hospitalares nem redes sociais.
- Nenhum registro é cópia, reconstrução ou adaptação de uma pessoa real.
- Não há nome, CPF, RG, CNS, prontuário, telefone, e-mail, endereço nem data de nascimento.
- `patient_id` é aleatório (`SYN-` + 16 hexadecimais), sem relação com documentos.
- Os municípios têm **nomes inventados** (ex.: "Vale de Aurival").
- Todo registro traz `data_type = "SYNTHETIC"` e `research_only = true`.

## 2. Como os dados são gerados

O gerador não sorteia números independentes. Ele segue um **modelo causal simplificado e fictício**, para que
existam relações aprendíveis por modelos de ML:

```
idade, sexo, hábitos de vida, histórico familiar
   → IMC, peso, altura
   → condições clínicas (probabilidade logística)
   → medicamentos e aderência ao tratamento
   → sinais vitais e exames laboratoriais (com efeito do tratamento)
   → escore de risco sintético → classificação de risco
   → desfecho simulado em 12 meses
```

Toda a aleatoriedade vem de um único **seed** (NumPy PCG64 + Faker pt_BR). O mesmo seed gera exatamente o
mesmo dataset. Detalhes e equações estão em [`docs/arquitetura.md`](docs/arquitetura.md), seção 5.

### Variáveis (50 colunas)

| Grupo | Variáveis |
|---|---|
| Identificação | `patient_id` |
| Demografia | `idade`, `sexo`, `municipio` (fictício), `estado` |
| Antropometria | `peso_kg`, `altura_cm`, `imc` |
| Sinais vitais | `pa_sistolica`, `pa_diastolica`, `frequencia_cardiaca`, `temperatura_c` |
| Histórico familiar | `hf_diabetes`, `hf_hipertensao`, `hf_doenca_cardiovascular`, `historico_familiar` |
| Hábitos de vida | `tabagismo`, `consumo_alcool`, `atividade_fisica`, `qualidade_dieta`, `horas_sono` |
| Condição clínica | 7 indicadores `cond_*`, `n_condicoes`, `condicao_clinica` |
| Medicamentos | `medicamentos`, `n_medicamentos`, `aderencia_tratamento` |
| Exames | `glicemia_jejum`, `hba1c`, `colesterol_total`, `ldl`, `hdl`, `triglicerides`, `creatinina`, `hemoglobina` |
| Atendimento | `data_atendimento` (fictícia, 2023–2024) |
| Desfecho | `escore_risco`, `classificacao_risco`, `diagnostico_sintetico`, `resultado_desfecho`, `desfecho_adverso` |
| ML / governança | `split`, `data_type`, `research_only` |

Descrição, unidade, faixa e papel em ML de cada variável: [`data/metadata.json`](data/metadata.json) e
[`data/dataset_card.md`](data/dataset_card.md).

## 3. Como executar o projeto

### Pré-requisitos

- Python **3.12+**
- Node.js **20+** (com npm)
- (opcional) Docker Desktop

### Instalação (uma vez)

**Windows (PowerShell), na raiz do projeto:**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

**Linux/macOS:**

```bash
bash scripts/setup.sh
```

Instalação manual equivalente:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd frontend && npm install && cd ..
```

### Executar (dois terminais)

```powershell
# Terminal 1 — API em http://localhost:8000 (documentação interativa em /docs)
scripts\run_backend.ps1          # ou: cd backend; ..\.venv\Scripts\python -m uvicorn app.main:app --reload

# Terminal 2 — painel em http://localhost:5173
scripts\run_frontend.ps1         # ou: cd frontend; npm run dev
```

No Linux/macOS use `scripts/run_backend.sh` e `scripts/run_frontend.sh`.

Abra **http://localhost:5173**. Lá estão:

- a mensagem permanente "DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES";
- os botões **Gerar Dataset**, **Gerar Novo Dataset** (seed aleatório), **Validar Privacidade**,
  **Visualizar Dados**, **Exportar CSV**, **Exportar Excel**, **Exportar JSON** e **Exportar Parquet**;
- o painel com quantidade de pacientes e de registros, distribuições de idade, sexo e IMC, condições
  clínicas, classificação de risco, desfecho e status de privacidade.

### Com Docker (opcional)

```bash
docker compose up --build
```

Painel em http://localhost:8080 e API em http://localhost:8000/docs.

## 4. Como gerar novos datasets

**Pelo painel:** escolha a quantidade (100, 1.000, 10.000 ou 100.000) e o seed, e clique em **Gerar Dataset**.
**Gerar Novo Dataset** usa um seed aleatório (exibido na tela para reprodução).

**Pela linha de comando** (com o ambiente virtual ativo):

```bash
# dataset de exemplo deste repositório
python scripts/generate_dataset.py --n 1000 --seed 42

# outros formatos e pasta própria
python scripts/generate_dataset.py --n 100000 --seed 7 --formats csv,parquet --out data/experimento_seed7

# também tornar o dataset o ativo no painel web
python scripts/generate_dataset.py --n 10000 --seed 42 --store-db
```

Cada geração produz o dataset (`synthetic_dataset.*`), as partições (`splits/train|validation|test.csv`),
`metadata.json`, `dataset_card.md`, `quality_report.md/.json` e `privacy_report.json`.

**Validar um arquivo já existente:**

```bash
python scripts/quality_report.py --input data/synthetic_dataset.csv
```

Tempos de referência (notebook comum): 1.000 pacientes < 1 s; 100.000 pacientes ≈ 30 s para gerar, validar e
gravar no banco. A exportação em Excel de 100.000 linhas leva ≈ 30 s; para ML prefira CSV ou Parquet.

## 5. Como usar os dados em experimentos de IA

```python
import pandas as pd

df = pd.read_csv("data/synthetic_dataset.csv", keep_default_na=False, na_values=[""])
treino, validacao, teste = (df[df.split == s] for s in ("train", "validation", "test"))

alvo = "desfecho_adverso"
# Remova alvos derivados uns dos outros para evitar vazamento:
excluir = ["patient_id", "split", "data_type", "research_only", "municipio", "historico_familiar",
           "medicamentos", "data_atendimento", "escore_risco", "classificacao_risco",
           "diagnostico_sintetico", "resultado_desfecho", "desfecho_adverso"]
X_treino, y_treino = treino.drop(columns=excluir), treino[alvo]
```

| Tipo de tarefa | Alvo sugerido |
|---|---|
| Classificação binária | `desfecho_adverso` (≈ 13% positivos, desbalanceado) |
| Classificação multiclasse | `classificacao_risco` (4 classes ordinais) ou `resultado_desfecho` |
| Regressão | `pa_sistolica`, `hba1c`, `escore_risco` |
| Padrões / agrupamento | perfis de pacientes (clustering), associação entre condições |
| Análise exploratória | todas as variáveis; distribuições em `quality_report.md` |

**Experimento pronto:**

```bash
python scripts/baseline_experiment.py --input data/synthetic_dataset.csv --seed 42
```

Ele treina regressão logística, Random Forest e Ridge, compara com baselines *dummy* e grava
`baseline_results.md`. Com 10.000 pacientes (seed 42): ROC-AUC 0,79 para desfecho, macro-F1 0,78 para risco e
R² 0,51 para pressão sistólica.

A metodologia completa para a dissertação (problema, preparação, treinamento, validação, métricas, riscos e
reprodutibilidade) está em [`docs/metodologia.md`](docs/metodologia.md).

## 6. Limitações

- Não representa nenhuma população real; prevalências e efeitos são construções do gerador.
- Coeficientes escolhidos por plausibilidade, não estimados de estudos clínicos.
- `escore_risco` não é um escore clínico validado.
- Relações mais "limpas" que na prática: sem erro de medição sistemático, viés de seleção ou ausência informativa.
- Um atendimento por paciente (sem séries temporais).
- Bom desempenho aqui não garante desempenho em dados reais.

## 7. Cuidados com dados pessoais

- O sistema **não aceita** dados pessoais. Se uma requisição à API trouxer campos como `cpf`, `nome`,
  `telefone`, `email`, `endereco`, `numero_prontuario` ou `data_nascimento`:
  - a requisição é recusada (HTTP 422);
  - o `privacy_guard` emite um alerta;
  - a auditoria registra a tentativa só com o nome do campo, nunca com o valor.
- `validate_privacy(dataset)` retorna `{"compliant": ..., "blocked_fields": [...], "warnings": [...]}` e verifica:
  - nomes de colunas;
  - conteúdo com formato de CPF, e-mail, telefone, CEP ou CNS;
  - a marcação SYNTHETIC.
- Toda exportação passa pelo `privacy_guard`. Se o dataset não estiver conforme, **nenhum arquivo é gravado**.
- **Não adicione** colunas com dados reais aos arquivos gerados nem misture este dataset com bases reais.
- Este sistema deliberadamente **não tem** função de importar dados reais. Usar dados reais na pesquisa exige
  uma etapa própria de governança:
  - aprovação no CEP;
  - base legal da LGPD (art. 11);
  - termo de uso de dados;
  - ambiente seguro.

## 8. Diferença entre dados sintéticos, anonimizados e pseudonimizados

| | Sintético (este projeto) | Anonimizado | Pseudonimizado |
|---|---|---|---|
| Origem | gerado artificialmente; **não há pessoa real** por trás do registro | dados de pessoas reais com identificadores removidos/generalizados | dados de pessoas reais com identificadores trocados por códigos |
| Ligação com o titular | inexistente | não deve ser possível reverter com meios razoáveis | **reversível** para quem tem a chave/tabela de correspondência |
| Status na LGPD | não é dado pessoal | não é dado pessoal, salvo se a anonimização puder ser revertida (art. 12) | **continua sendo dado pessoal** (definição de pseudonimização no art. 13, §4º) |
| Risco de reidentificação | não se aplica | existe (cruzamento de quase-identificadores) | alto, se a chave vazar |
| Fidelidade estatística à realidade | só a que o gerador modelar | alta | total |
| Uso típico | desenvolvimento, testes, ensino, comparação de métodos | pesquisa e estatística com dados reais | operação interna e pesquisa com possibilidade de reidentificação controlada |

Em resumo: dados anonimizados e pseudonimizados **vêm de pessoas reais**; dados sintéticos não.

## 9. Estrutura do projeto

```
backend/    API FastAPI, gerador, privacy_guard, qualidade, exportação, banco (6 tabelas)
frontend/   painel React + Vite + TypeScript + Tailwind
data/       dataset de exemplo (1.000 pacientes, seed 42), splits, metadata.json, dataset_card.md, relatórios
tests/      177 testes automatizados
docs/       arquitetura.md, metodologia.md
scripts/    generate_dataset.py, quality_report.py, baseline_experiment.py, setup/run (.ps1 e .sh)
```

Arquitetura, modelo de banco e fluxo: [`docs/arquitetura.md`](docs/arquitetura.md).

## 10. Testes

```bash
python -m pytest          # ou scripts\run_tests.ps1
```

Os testes cobrem:

- geração e reprodutibilidade por seed;
- cálculo do IMC;
- cada regra de qualidade (com defeitos injetados);
- detecção de campos proibidos e de conteúdo sensível;
- exportação nos 4 formatos e o bloqueio por privacidade;
- duplicidade de identificadores;
- integridade banco ↔ dataset;
- a API de ponta a ponta.

---

Licença: MIT (ver [`LICENSE`](LICENSE)). Os dados gerados são sintéticos e destinados exclusivamente a pesquisa.
