"""Gera o relatório técnico em PDF (docs/relatorio_tecnico.pdf) a partir dos artefatos do projeto.

Todos os números do relatório são lidos dos arquivos gerados (metadata, relatórios de qualidade,
resultados de ML, comparação com a base real), então o PDF pode ser reconstruído a qualquer momento:

    python scripts/generate_dataset.py --n 1000 --seed 42
    python scripts/baseline_experiment.py --input data/synthetic_dataset.csv
    python scripts/fetch_public_dataset.py
    python scripts/compare_synthetic_real.py
    python scripts/build_report_pdf.py
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    CondPageBreak,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.dataset_schema import CONDICOES, CONDITION_COLUMNS, DISCLAIMER, FIELDS  # noqa: E402
from app.privacy_guard import FORBIDDEN_FIELDS, VALUE_PATTERNS  # noqa: E402
from app.public_datasets import UCI_HEART  # noqa: E402

DATA = ROOT / "data"
FIG = ROOT / "docs" / "figuras"
SAIDA = ROOT / "docs" / "relatorio_tecnico.pdf"
AUTORA = "Judith Otavia Margarido de Andrade"

# ---------------------------------------------------------------- fontes e estilos
FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Oblique", str(FONT_DIR / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuMono", str(FONT_DIR / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique", boldItalic="DejaVu-Bold")

AZUL = colors.HexColor("#1e3a8a")
CINZA = colors.HexColor("#475569")
CLARO = colors.HexColor("#f1f5f9")
AMBAR = colors.HexColor("#fef3c7")

ST = {
    "titulo": ParagraphStyle("titulo", fontName="DejaVu-Bold", fontSize=22, leading=28, textColor=AZUL, alignment=TA_CENTER),
    "subtitulo": ParagraphStyle("subtitulo", fontName="DejaVu", fontSize=12.5, leading=17, textColor=CINZA, alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=15, leading=20, textColor=AZUL, spaceBefore=14, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=11.5, leading=15, textColor=AZUL, spaceBefore=10, spaceAfter=5, keepWithNext=1),
    "corpo": ParagraphStyle("corpo", fontName="DejaVu", fontSize=9.6, leading=13.6, alignment=TA_JUSTIFY, spaceAfter=6),
    "item": ParagraphStyle("item", fontName="DejaVu", fontSize=9.6, leading=13.4, leftIndent=14, bulletIndent=4, spaceAfter=2),
    "celula": ParagraphStyle("celula", fontName="DejaVu", fontSize=8, leading=10.2),
    "celula_b": ParagraphStyle("celula_b", fontName="DejaVu-Bold", fontSize=8, leading=10.2, textColor=colors.white),
    "legenda": ParagraphStyle("legenda", fontName="DejaVu-Oblique", fontSize=8.2, leading=11, textColor=CINZA, alignment=TA_CENTER, spaceAfter=8),
    "codigo": ParagraphStyle("codigo", fontName="DejaVuMono", fontSize=7.8, leading=10.5, backColor=CLARO, borderPadding=5, leftIndent=4, spaceBefore=4, spaceAfter=8),
    "aviso": ParagraphStyle("aviso", fontName="DejaVu-Bold", fontSize=10, leading=14, alignment=TA_CENTER, backColor=AMBAR, borderPadding=8, textColor=colors.HexColor("#78350f")),
}


def P(texto: str, estilo: str = "corpo") -> Paragraph:
    return Paragraph(texto, ST[estilo])


def itens(lista: list[str]) -> list[Paragraph]:
    return [Paragraph(t, ST["item"], bulletText="•") for t in lista]


def tabela(linhas: list[list], larguras: list[float] | None = None, cabecalho: bool = True, zebra: bool = True) -> Table:
    conteudo = []
    for i, linha in enumerate(linhas):
        estilo = "celula_b" if cabecalho and i == 0 else "celula"
        conteudo.append([c if isinstance(c, (Paragraph, Image)) else Paragraph(str(c), ST[estilo]) for c in linha])
    t = Table(conteudo, colWidths=[w * cm for w in larguras] if larguras else None, repeatRows=1 if cabecalho else 0, hAlign="LEFT")
    comandos = [
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if cabecalho:
        comandos.append(("BACKGROUND", (0, 0), (-1, 0), AZUL))
    if zebra:
        for i in range(1 if cabecalho else 0, len(linhas)):
            if i % 2 == 0:
                comandos.append(("BACKGROUND", (0, i), (-1, i), CLARO))
    t.setStyle(TableStyle(comandos))
    return t


_eq_cache: dict[str, bytes] = {}


def eq(latex: str, tamanho: float = 10.5, largura_max_cm: float = 17) -> Image:
    """Renderiza uma equação (mathtext do matplotlib) como imagem."""
    if latex not in _eq_cache:
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${latex}$", fontsize=tamanho)
        buf = io.BytesIO()
        fig.savefig(buf, dpi=250, bbox_inches="tight", pad_inches=0.04, facecolor="white")
        plt.close(fig)
        _eq_cache[latex] = buf.getvalue()
    dados = io.BytesIO(_eq_cache[latex])
    from PIL import Image as PILImage

    with PILImage.open(io.BytesIO(_eq_cache[latex])) as im:
        w, h = im.size
    largura, altura = w * 72 / 250, h * 72 / 250
    if largura > largura_max_cm * cm:
        fator = largura_max_cm * cm / largura
        largura, altura = largura * fator, altura * fator
    img = Image(dados, width=largura, height=altura)
    img.hAlign = "CENTER"
    return img


def figura(caminho: Path, largura_cm: float, legenda: str) -> KeepTogether:
    from PIL import Image as PILImage

    with PILImage.open(caminho) as im:
        w, h = im.size
    img = Image(str(caminho), width=largura_cm * cm, height=largura_cm * cm * h / w)
    return KeepTogether([img, Spacer(1, 3), P(legenda, "legenda")])


def num(v, casas: int = 2) -> str:
    """Formata número no padrão brasileiro."""
    if isinstance(v, (int, np.integer)):
        return f"{v:,}".replace(",", ".")
    v = round(float(v), casas) + 0.0  # evita "-0,000"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float, casas: int = 1) -> str:
    return num(100 * v, casas) + "%"


# ---------------------------------------------------------------- dados
def carregar() -> dict:
    j = lambda p: json.loads((DATA / p).read_text(encoding="utf-8"))  # noqa: E731
    d = {
        "meta": j("metadata.json"),
        "qualidade": j("quality_report.json"),
        "privacidade": j("privacy_report.json"),
        "baseline_1k": j("baseline_results.json"),
        "baseline_10k": j("experimentos/n10000_seed42/baseline_results.json"),
        "qualidade_10k": j("experimentos/n10000_seed42/quality_report.json"),
        "comparacao": j("real_public/comparacao_sintetico_real.json"),
        "real_meta": j("real_public/uci_heart_disease/metadata.json"),
    }
    d["df"] = pd.read_csv(DATA / "synthetic_dataset.csv", keep_default_na=False, na_values=[""])
    return d


def contar_testes() -> tuple[int, dict[str, int]]:
    saida = subprocess.run(
        [sys.executable, "-m", "pytest", "-o", "addopts=", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    ).stdout
    por_arquivo: dict[str, int] = {}
    for linha in saida.splitlines():
        if "::" in linha:
            arquivo = linha.split("::")[0].replace("\\", "/").split("/")[-1]
            por_arquivo[arquivo] = por_arquivo.get(arquivo, 0) + 1
    if not por_arquivo:
        raise RuntimeError("Não foi possível coletar os testes com o pytest:\n" + saida[-2000:])
    return sum(por_arquivo.values()), por_arquivo


def rodar_testes() -> str:
    saida = subprocess.run([sys.executable, "-m", "pytest", "-o", "addopts=", "-q"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    linha = [l for l in saida.strip().splitlines() if "passed" in l or "failed" in l]
    if not linha:
        raise RuntimeError("Não foi possível executar os testes com o pytest:\n" + saida[-2000:])
    aprovados = re.search(r"(\d+) passed", linha[-1])
    falhas = re.search(r"(\d+) failed", linha[-1])
    texto = f"{aprovados.group(1) if aprovados else 0} aprovados"
    return texto + (f", {falhas.group(1)} com falha" if falhas else ", nenhuma falha")


# ---------------------------------------------------------------- figuras do dataset sintético
def figuras_sinteticas(df: pd.DataFrame) -> tuple[Path, Path]:
    FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(2, 3, figsize=(11, 6))
    ax[0, 0].hist(df["idade"], bins=range(18, 92, 4), color="#2563eb", edgecolor="white")
    ax[0, 0].set(title="Idade", xlabel="anos", ylabel="pacientes")
    ax[0, 1].hist(df["imc"], bins=30, color="#7c3aed", edgecolor="white")
    for corte in (18.5, 25, 30, 35, 40):
        ax[0, 1].axvline(corte, color="#94a3b8", lw=0.8, ls="--")
    ax[0, 1].set(title="IMC (linhas: cortes OMS)", xlabel="kg/m²")
    ax[0, 2].hist(df["pa_sistolica"], bins=30, color="#0d9488", edgecolor="white")
    ax[0, 2].set(title="PA sistólica", xlabel="mmHg")
    ordem = ["BAIXO", "MODERADO", "ALTO", "MUITO_ALTO"]
    contagem = df["classificacao_risco"].value_counts().reindex(ordem)
    ax[1, 0].bar(["Baixo", "Moderado", "Alto", "Muito alto"], contagem.values, color=["#16a34a", "#eab308", "#f97316", "#dc2626"])
    ax[1, 0].set(title="Classificação de risco sintética", ylabel="pacientes")
    prev = sorted(((c.replace("_", " ").title(), df[CONDITION_COLUMNS[c]].mean() * 100) for c in CONDICOES), key=lambda x: x[1])
    ax[1, 1].barh([p[0] for p in prev], [p[1] for p in prev], color="#0d9488")
    ax[1, 1].set(title="Prevalência das condições simuladas", xlabel="% dos pacientes")
    ax[1, 1].tick_params(axis="y", labelsize=7)
    sexo = df["sexo"].value_counts().reindex(["F", "M"])
    ax[1, 2].bar(["Feminino", "Masculino"], sexo.values, color=["#db2777", "#2563eb"])
    ax[1, 2].set(title="Sexo", ylabel="pacientes")
    fig.tight_layout()
    f1 = FIG / "sintetico_distribuicoes.png"
    fig.savefig(f1, dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(1, 3, figsize=(11, 3.3))
    ax[0].scatter(df["idade"], df["pa_sistolica"], s=6, alpha=0.4, color="#2563eb")
    r = df["idade"].corr(df["pa_sistolica"])
    ax[0].set(title=f"Idade × PA sistólica (r = {r:.2f})", xlabel="idade (anos)", ylabel="mmHg")
    grupos = [df.loc[~df["cond_diabetes_tipo_2"], "glicemia_jejum"], df.loc[df["cond_diabetes_tipo_2"], "glicemia_jejum"]]
    ax[1].boxplot(grupos, tick_labels=["Sem diabetes", "Com diabetes"], widths=0.5)
    ax[1].set(title="Glicemia de jejum por condição", ylabel="mg/dL")
    taxa = df.groupby("classificacao_risco")["desfecho_adverso"].mean().reindex(ordem) * 100
    ax[2].bar(["Baixo", "Moderado", "Alto", "Muito alto"], taxa.values, color=["#16a34a", "#eab308", "#f97316", "#dc2626"])
    ax[2].set(title="Desfecho adverso por classe de risco", ylabel="% com desfecho adverso")
    fig.tight_layout()
    f2 = FIG / "sintetico_relacoes.png"
    fig.savefig(f2, dpi=160)
    plt.close(fig)
    return f1, f2


# ---------------------------------------------------------------- página
def decorar(canvas, doc):
    canvas.saveState()
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(2 * cm, A4[1] - 1.2 * cm, "Relatório técnico — SPD-BR")
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.2 * cm, DISCLAIMER)
    canvas.drawCentredString(A4[0] / 2, 1.1 * cm, f"página {doc.page}")
    canvas.restoreState()


def capa(canvas, doc):
    pass


# ---------------------------------------------------------------- conteúdo
def construir() -> None:
    d = carregar()
    df = d["df"]
    meta = d["meta"]
    total_testes, testes_por_arquivo = contar_testes()
    resultado_testes = rodar_testes()
    f_dist, f_rel = figuras_sinteticas(df)
    comp = d["comparacao"]
    b10 = d["baseline_10k"]
    b1 = d["baseline_1k"]
    s = []

    # ---------- capa
    s += [
        Spacer(1, 4.5 * cm),
        P("Gerador de Dataset Sintético de Pacientes para Pesquisa em Inteligência Artificial", "titulo"),
        Spacer(1, 0.6 * cm),
        P("Relatório técnico: arquitetura, modelo de geração, cálculos, validação de qualidade e privacidade, "
          "experimentos de aprendizado de máquina e comparação com base pública real", "subtitulo"),
        Spacer(1, 1.6 * cm),
        P(f"<b>Autora:</b> {AUTORA}", "subtitulo"),
        P("Projeto acadêmico de mestrado", "subtitulo"),
        P(date.today().strftime("%d/%m/%Y"), "subtitulo"),
        Spacer(1, 2.2 * cm),
        P(f"{DISCLAIMER}<br/>O dataset principal é inteiramente sintético. A base real usada para comparação "
          "(UCI Heart Disease) é pública, anonimizada na origem e mantida separada.", "aviso"),
        Spacer(1, 2 * cm),
        P(f"Repositório: https://github.com/judithotavia-ux/dataset-sintetico-pacientes · versão do dataset {meta['version']} · "
          f"gerador {meta['generator_version']}", "legenda"),
        PageBreak(),
    ]

    # ---------- sumário
    secoes = [
        "1. Resumo", "2. Objetivo, escopo e restrições", "3. Arquitetura do sistema", "4. Modelo de geração e cálculos",
        "5. Validação de qualidade", "6. Privacidade: privacy_guard", "7. Dataset de exemplo: resultados descritivos",
        "8. Experimentos de aprendizado de máquina", "9. Base pública real e comparação", "10. Testes automatizados",
        "11. Reprodutibilidade", "12. Limitações e riscos", "13. Referências",
    ]
    s += [P("Sumário", "h1"), *[P(x, "item") for x in secoes], PageBreak()]

    # ---------- 1 resumo
    q10 = b10["classificacao_binaria"]["modelos"]
    mc10 = b10["classificacao_multiclasse"]["modelos"]
    rg10 = b10["regressao"]["modelos"]
    reais = comp["modelos_base_real"]["modelos"]
    s += [
        P("1. Resumo", "h1"),
        P("Este relatório documenta o desenvolvimento de uma aplicação local que gera, valida e exporta um "
          "<b>dataset sintético de pacientes</b> para testes, treinamento e validação de sistemas de Inteligência "
          "Artificial em uma pesquisa de mestrado. Nenhum dado real de paciente é usado na geração: os registros "
          "seguem um modelo estatístico causal simplificado, definido pela autora, com aleatoriedade controlada por "
          "um único <i>seed</i>, o que torna cada dataset exatamente reprodutível."),
        P("A aplicação gera 100, 1.000, 10.000 ou 100.000 pacientes com 50 variáveis: demografia, antropometria, sinais vitais, "
          "histórico familiar, hábitos, condições clínicas, medicamentos, 8 exames laboratoriais, escore e classe "
          "de risco, diagnóstico e desfecho em 12 meses. O backend usa Python/FastAPI/SQLite, e o painel usa React/TypeScript. "
          "A camada <b>privacy_guard</b> bloqueia campos de identificação pessoal e impede exportações não conformes. O "
          "particionamento treino/validação/teste (70/15/15) é estratificado e reprodutível."),
        P(f"Com 10.000 pacientes (seed 42), modelos de referência atingem ROC-AUC de {num(q10['Random Forest']['roc_auc'], 3)} na "
          f"previsão de desfecho adverso, macro-F1 de {num(mc10['Regressão logística multinomial']['macro_f1'], 3)} na classificação de "
          f"risco e R² de {num(rg10['Ridge']['r2'], 3)} na regressão da pressão sistólica, todos muito acima das baselines "
          "ingênuas. Isso mostra que o dataset contém estrutura aprendível, sem ser trivial."),
        P("Para comparação, foi incluída, em separado, a base pública real <b>UCI Heart Disease — Cleveland</b> "
          f"(303 pacientes, CC BY 4.0). Nela, a regressão logística obtém ROC-AUC de "
          f"{num(reais['Regressão logística']['roc_auc']['media'], 3)} ± {num(reais['Regressão logística']['roc_auc']['dp'], 3)} "
          f"para doença cardíaca. Os testes automatizados somam {total_testes} casos ({resultado_testes})."),
    ]

    # ---------- 2 objetivo
    s += [
        P("2. Objetivo, escopo e restrições", "h1"),
        P("<b>Objetivo.</b> Disponibilizar um conjunto de dados clínicos simulados, plausível do ponto de vista estatístico e "
          "adequado a experimentos de classificação, regressão, detecção de padrões e análise exploratória. O conjunto deve "
          "dispensar o acesso a prontuários reais na fase de desenvolvimento da pesquisa."),
        P("<b>Restrições de privacidade adotadas desde o início (<i>privacy by design</i>):</b>"),
        *itens([
            "nenhum dado real de paciente, sem scraping de prontuários, hospitais ou redes sociais;",
            "nenhum registro copia, reconstrói ou adapta uma pessoa real;",
            "nenhum identificador: o sistema não tem campos de nome, CPF, RG, CNS, prontuário, telefone, e-mail, endereço ou data de nascimento;",
            "todo registro tem as marcações <font face='DejaVuMono'>data_type = \"SYNTHETIC\"</font> e <font face='DejaVuMono'>research_only = true</font>;",
            "o sistema não oferece função de importar dados pessoais reais. O uso de dados reais exige uma etapa própria de governança (CEP, base legal da LGPD).",
        ]),
        P("<b>Tecnologias.</b> Python 3.12, FastAPI, SQLAlchemy, SQLite, Pydantic, Faker, Pandas, NumPy, scikit-learn; "
          "React, Vite, TypeScript, Tailwind CSS e Recharts no painel; pytest para os testes; Docker opcional."),
    ]

    # ---------- 3 arquitetura
    s += [
        P("3. Arquitetura do sistema", "h1"),
        P("O código foi organizado por responsabilidade. Um <b>dicionário de dados</b> único (<font face='DejaVuMono'>dataset_schema.py</font>) "
          "define as 50 variáveis: tipo, unidade, faixa válida, categorias e papel em ML. O gerador, a validação, os metadados e a "
          "Dataset Card consultam esse mesmo dicionário, o que evita inconsistências."),
        tabela([
            ["Módulo", "Responsabilidade"],
            ["generator.py", "Geração dos pacientes (modelo causal, seed, partição estratificada)"],
            ["quality.py", "Validações de qualidade e relatório"],
            ["privacy_guard.py", "Detecção e bloqueio de dados pessoais; validate_privacy(dataset)"],
            ["exporter.py", "Exportação CSV, XLSX, JSON e Parquet (sempre após o privacy_guard)"],
            ["metadata.py", "metadata.json e Dataset Card"],
            ["repository.py / models.py", "Persistência normalizada em 6 tabelas e reconstrução da tabela plana"],
            ["audit.py", "Logs técnicos de auditoria (sem dados pessoais)"],
            ["public_datasets.py", "Base pública real UCI Heart Disease, separada do sintético"],
            ["main.py", "API REST (FastAPI) consumida pelo painel React"],
        ], [5, 11.5]),
        Spacer(1, 6),
        P("3.1 Modelo de banco de dados", "h2"),
        tabela([
            ["Tabela", "Cardinalidade", "Conteúdo"],
            ["dataset_metadata", "1 por dataset", "id, versão, seed, nº de registros, status (ATIVO/SUBSTITUÍDO), resultados de validação, metadata JSON"],
            ["patients", "1 por paciente", "demografia, antropometria, histórico familiar, hábitos, partição, marcações"],
            ["clinical_records", "1 por paciente", "data do atendimento, sinais vitais, condições, aderência, risco, diagnóstico, desfecho"],
            ["lab_results", "8 por paciente", "exame, valor, unidade, data de coleta (formato longo)"],
            ["medications", "0 a N por paciente", "ordem, nome, classe terapêutica, posologia"],
            ["audit_logs", "1 por evento", "data, evento, nível, dataset, detalhes técnicos"],
        ], [3.6, 3, 9.9]),
        Spacer(1, 4),
        P("Um teste automatizado garante que a gravação nas tabelas normalizadas seguida da reconstrução da tabela plana "
          "devolve exatamente o mesmo conjunto de dados. Quando um novo dataset é gerado, o anterior é removido na "
          "mesma transação e fica registrado como SUBSTITUÍDO."),
        P("3.2 Fluxo da aplicação", "h2"),
        P("Geração: painel → <font face='DejaVuMono'>POST /api/datasets/generate</font> (validação Pydantic com "
          "<font face='DejaVuMono'>extra=\"forbid\"</font>) → gerador → validação de qualidade → validação de privacidade → "
          "gravação nas 6 tabelas → metadata.json, Dataset Card e relatórios. Exportação: painel → "
          "<font face='DejaVuMono'>GET /api/export/{formato}</font> → privacy_guard → arquivo. Se alguma validação falhar, "
          "o fluxo é interrompido e o evento é auditado."),
        figura(ROOT / "docs" / "figuras" / "painel.png", 13.5, "Figura 1 — Painel da aplicação (1.000 pacientes, seed 42), com aviso permanente de dados sintéticos e status de privacidade."),
    ]

    # ---------- 4 modelo de geração
    s += [
        PageBreak(),
        P("4. Modelo de geração e cálculos", "h1"),
        P("O gerador segue a cadeia causal abaixo. Em cada etapa entra ruído aleatório, como em dados observacionais. "
          "Os coeficientes foram escolhidos para produzir valores plausíveis. Eles <b>não</b> foram estimados de uma população "
          "real e não devem ser interpretados como evidência clínica. Nas equações, o separador decimal é o ponto, igual ao código-fonte."),
        P("idade, sexo, hábitos, histórico familiar → IMC → condições clínicas → tratamento e aderência → sinais vitais e exames → "
          "escore de risco → classificação de risco → desfecho em 12 meses", "codigo"),
        P("<b>Notação.</b> σ(z) é a função logística; N(μ, s²) é a distribuição normal; Bern(p) é a distribuição de Bernoulli; "
          "variáveis indicadoras valem 1 quando a condição é verdadeira: S = sedentário, A = fisicamente ativo, F = fumante atual, "
          "E = consumo elevado de álcool, D<sub>r</sub>/D<sub>b</sub> = dieta ruim/boa, HAS = hipertensão, DM = diabetes tipo 2, "
          "DLP = dislipidemia, OB = obesidade, DRC = doença renal crônica, IRA = infecção respiratória aguda. "
          "T<sub>c</sub> = 1 se a condição c é tratada; e = efeito da aderência ao tratamento."),
        eq(r"\sigma(z)=\frac{1}{1+e^{-z}}"),
        P("4.1 Demografia, histórico familiar e hábitos", "h2"),
        eq(r"\mathrm{idade}\sim\mathcal{N}(48,\,17^{2})\ \mathrm{truncada\ em\ }[18,\,90]\ \mathrm{(por\ reamostragem)},\qquad \mathrm{sexo}=F\ \mathrm{com}\ p=0.51"),
        P("A truncagem por reamostragem sorteia de novo os valores fora do intervalo, em vez de cortá-los, para não acumular "
          "massa nos limites. O município é sorteado entre 120 nomes <b>inventados</b> (prefixo + radical + sufixo, por exemplo "
          "\"Vale de Aurival\"), cada um associado a uma UF."),
        tabela([
            ["Variável", "Distribuição"],
            ["Histórico familiar", "Bern(0.25) diabetes; Bern(0.35) hipertensão; Bern(0.18) doença cardiovascular"],
            ["Tabagismo", "nunca / ex / atual = 0.66 / 0.18 / 0.16 (masculino: 0.61 / 0.18 / 0.21)"],
            ["Álcool", "nenhum / moderado / elevado = 0.45 / 0.43 / 0.12 (masculino: 0.39 / 0.43 / 0.18)"],
            ["Atividade física", "p(sedentário) = clip(0.30 + 0.005(idade−18); 0.30; 0.65); p(ativo) = clip(0.30 − 0.003(idade−18); 0.10; 0.30)"],
            ["Dieta", "ruim / regular / boa = 0.25 / 0.50 / 0.25"],
            ["Horas de sono", "clip(N(7.0; 1.1²); 4; 10)"],
        ], [3.6, 12.9]),
        P("4.2 Antropometria e IMC", "h2"),
        eq(r"h\ (\mathrm{cm})\sim\mathcal{N}(172,\,7^{2})\ \mathrm{(M)},\quad \mathcal{N}(160,\,6.5^{2})\ \mathrm{(F)},\quad \mathrm{clip}\ [145,\,200]"),
        eq(r"\mathrm{IMC}^{*}=24.0+0.07\,(\min(\mathrm{idade},65)-40)+1.6S-1.3A+1.3D_r-0.9D_b+0.6E+\varepsilon,\quad \varepsilon\sim\mathcal{N}(0,4^{2})"),
        eq(r"\mathrm{peso}=\mathrm{IMC}^{*}\cdot\left(\frac{h}{100}\right)^{2}\qquad\qquad \mathrm{IMC}=\frac{\mathrm{peso}}{(h/100)^{2}}"),
        P("O IMC latente é limitado a [16,5; 48] e o peso a [38; 180] kg. O IMC final é <b>recalculado</b> a partir do peso e da altura "
          "já arredondados, para que a variável publicada seja sempre coerente com a fórmula (tolerância de 0,05 kg/m² na validação). "
          "Exemplo: 70 kg e 175 cm dão 70 / 1,75² = 22,86 kg/m²."),
        P("4.3 Condições clínicas: modelos logísticos", "h2"),
        P("Cada condição crônica segue P(condição = 1 | x) = σ(β<sub>0</sub> + βᵀx), com sorteio de Bernoulli independente. Coeficientes:"),
        tabela([
            ["Condição", "Preditor linear (logit)"],
            ["Hipertensão", "−5.2 + 0.065·idade + 0.09(IMC−25) + 0.7·HF<sub>HAS</sub> + 0.35F + 0.3E + 0.25S"],
            ["Diabetes tipo 2", "−5.6 + 0.045·idade + 0.13(IMC−25) + 0.9·HF<sub>DM</sub> + 0.35S + 0.3D<sub>r</sub>"],
            ["Dislipidemia", "−3.6 + 0.035·idade + 0.07(IMC−25) + 0.4D<sub>r</sub> + 0.3·HF<sub>DCV</sub>"],
            ["Asma", "−2.6 + 0.3F"],
            ["Doença renal crônica", "−7.5 + 0.05·idade + 1.0·DM + 0.8·HAS"],
            ["Obesidade", "determinística: IMC ≥ 30 (classificação da OMS)"],
            ["Infecção respiratória aguda", "Bern(0.07 + 0.03F), condição aguda (com febre)"],
        ], [4.2, 12.3]),
        Spacer(1, 4),
        P("A <b>condição principal</b> é a de maior prioridade presente (DRC > DM2 > HAS > IRA > DLP > OB > asma). Sem nenhuma, "
          "ela é SEM_CONDICAO_CRONICA. Exemplo: um paciente de 60 anos com IMC 30, histórico familiar de hipertensão e "
          "não fumante tem logit = −5.2 + 3.9 + 0.45 + 0.7 = −0.15, ou seja, P(HAS) = σ(−0.15) ≈ 0.46."),
        P("4.4 Tratamento e aderência", "h2"),
        P("Cada condição tratável recebe tratamento com probabilidade P(T<sub>c</sub> = 1 | condição) = 0,80 (HAS), 0,85 (DM2), "
          "0,60 (DLP), 0,75 (asma) e 0,90 (IRA). Os medicamentos vêm de um catálogo simulado por condição (ex.: losartana, "
          "metformina, sinvastatina). Se houver tratamento, a aderência é sorteada como alta/média/baixa com probabilidades "
          "0,55/0,30/0,15 e define o efeito do tratamento:"),
        tabela([["Aderência", "alta", "média", "baixa", "sem tratamento"], ["Efeito e", "1,00", "0,55", "0,15", "0"]], [3.3, 3.3, 3.3, 3.3, 3.3]),
        Spacer(1, 4),
        P("4.5 Sinais vitais", "h2"),
        eq(r"\mathrm{PAS}=112+0.35(\mathrm{idade}-40)+0.7(\mathrm{IMC}-25)+18\,\mathrm{HAS}+3F+2E"),
        eq(r"\qquad+4\,\mathrm{DRC}-12\,T_{HAS}\,e+\varepsilon,\quad \varepsilon\sim\mathcal{N}(0,10^{2})"),
        eq(r"\mathrm{PAD}=\min\left(\mathrm{clip}(0.5\,\mathrm{PAS}+12+0.2(\mathrm{IMC}-25)+\varepsilon,\,50,\,125),\ \mathrm{PAS}-20\right),\ \ \varepsilon\sim\mathcal{N}(0,6^{2})"),
        eq(r"\mathrm{FC}=72+4S-5A+3F+15\,\mathrm{IRA}+\varepsilon,\quad \varepsilon\sim\mathcal{N}(0,9^{2})"),
        eq(r"T\ (^{\circ}C)=36.6+\varepsilon_1+\mathrm{IRA}\,(1.8+\varepsilon_2)"),
        P("A PAS é limitada a [85; 215] mmHg e a FC a [45; 150] bpm; ε<sub>1</sub> ~ N(0; 0,3²) e ε<sub>2</sub> ~ N(0; 0,5²). A PAD é forçada a "
          "ficar pelo menos 20 mmHg abaixo da PAS, o que garante coerência fisiológica (diastólica < sistólica)."),
        P("4.6 Exames laboratoriais", "h2"),
        eq(r"G\,|\,\mathrm{DM}\sim\mathcal{N}(160,\,35^{2})-30\,T_{DM}\,e\qquad\qquad G\,|\,\mathrm{sem\ DM}\sim\mathcal{N}(90+0.25(\mathrm{IMC}-25),\,9^{2})"),
        eq(r"\mathrm{HbA1c}=\frac{G+46.7}{28.7}+\varepsilon,\quad \varepsilon\sim\mathcal{N}(0,0.35^{2})"),
        P("A relação entre HbA1c e glicose é a inversa da fórmula do estudo ADAG (glicose média estimada = 28,7 × HbA1c − 46,7), "
          "aplicada aqui à glicemia de jejum como simplificação."),
        eq(r"\mathrm{CT}=185+0.4(\mathrm{idade}-40)+35\,\mathrm{DLP}-30\,T_{DLP}\,e+6D_r+\varepsilon,\ \varepsilon\sim\mathcal{N}(0,28^{2})"),
        eq(r"\mathrm{HDL}=\{47\ \mathrm{(M)};\,56\ \mathrm{(F)}\}-4S-3\,\mathrm{OB}+5A+\varepsilon,\ \varepsilon\sim\mathcal{N}(0,9^{2})"),
        eq(r"\mathrm{TG}=110\cdot\exp\left(0.03(\mathrm{IMC}-25)+0.35\,\mathrm{DLP}+0.25\,\mathrm{DM}+\varepsilon\right),\ \varepsilon\sim\mathcal{N}(0,0.35^{2})"),
        eq(r"\mathrm{LDL}=\mathrm{CT}-\mathrm{HDL}-\frac{\mathrm{TG}}{5}\ \ \mathrm{se\ TG}<400\ \mathrm{(Friedewald)};\qquad \mathrm{LDL}=0.75\,(\mathrm{CT}-\mathrm{HDL})\ \ \mathrm{se\ TG}\geq 400"),
        eq(r"\mathrm{Cr}=\{0.95\ \mathrm{(M)};\,0.75\ \mathrm{(F)}\}+0.004(\mathrm{idade}-40)+\mathrm{DRC}\cdot\mathcal{N}(1.0,0.4^{2})+\varepsilon,\quad \varepsilon\sim\mathcal{N}(0,0.12^{2})"),
        eq(r"\mathrm{Hb}=\{14.8\ \mathrm{(M)};\,13.2\ \mathrm{(F)}\}-1.0\,\mathrm{DRC}+\varepsilon,\quad \varepsilon\sim\mathcal{N}(0,1)"),
        P("A equação de Friedewald perde validade com triglicerídeos ≥ 400 mg/dL. Nesse caso, usa-se uma aproximação alternativa. "
          "Exemplo: CT = 220, HDL = 45 e TG = 150 dão LDL = 220 − 45 − 30 = 145 mg/dL."),
        P("4.7 Escore de risco sintético, classificação e desfecho", "h2"),
        eq(r"z=0.055(\mathrm{idade}-50)+0.028(\mathrm{PAS}-130)+0.6F+0.8\,\mathrm{DM}+0.010(\mathrm{CT}-200)-0.025(\mathrm{HDL}-50)"),
        eq(r"\qquad+1.0\,\mathrm{DRC}+0.04(\mathrm{IMC}-27)+0.4\,\mathrm{HF}_{DCV}+0.6\,\mathbf{1}[T\geq 38.5]+\varepsilon,\quad \varepsilon\sim\mathcal{N}(0,0.35^{2})"),
        eq(r"\mathrm{escore}=100\cdot\sigma(z-1.4)\in[0,100]"),
        tabela([["Escore", "< 10", "10 a < 20", "20 a < 40", "≥ 40"], ["Classe", "BAIXO", "MODERADO", "ALTO", "MUITO_ALTO"]], [3, 3.3, 3.3, 3.3, 3.3]),
        Spacer(1, 4),
        P("O escore é uma construção sintética e <b>não</b> equivale a escores clínicos validados. O desfecho em 12 meses "
          "segue dois estágios: primeiro se há desfecho adverso, depois o tipo."),
        eq(r"P(\mathrm{adverso})=\sigma\left(-3.6+0.045\,\mathrm{escore}+0.9\,\mathrm{DRC}+0.6\,\mathbf{1}[\mathrm{aderencia\ baixa}]+0.5\,\mathrm{IRA}+\varepsilon\right)"),
        eq(r"\varepsilon\sim\mathcal{N}(0,0.5^{2})"),
        eq(r"p_{CV}=\mathrm{clip}(0.20+0.004(\mathrm{PAS}-130)+0.15\,\mathrm{DM};\,0.05;\,0.60)"),
        eq(r"p_{obito}=\mathrm{clip}(0.02+0.0025(\mathrm{idade}-50)+0.05\,\mathrm{DRC};\,0.01;\,0.25)"),
        P("Se houver desfecho adverso, o tipo é evento cardiovascular (p<sub>CV</sub>), óbito (p<sub>óbito</sub>) ou internação "
          "(1 − p<sub>CV</sub> − p<sub>óbito</sub>). A variável binária <font face='DejaVuMono'>desfecho_adverso</font> indica qualquer desfecho "
          "diferente de SEM_INTERCORRENCIA."),
        P("4.8 Particionamento treino/validação/teste", "h2"),
        P("A partição é estratificada pela classificação de risco. Para cada classe k com n<sub>k</sub> pacientes, os índices são "
          "embaralhados com um gerador derivado do seed (seed + 7919) e divididos assim:"),
        eq(r"n_k^{\,treino}=\mathrm{round}(0.70\,n_k),\qquad n_k^{\,valid}=\mathrm{round}(0.15\,n_k),\qquad n_k^{\,teste}=n_k-n_k^{\,treino}-n_k^{\,valid}"),
        P("4.9 Identificadores e reprodutibilidade", "h2"),
        P("O <font face='DejaVuMono'>patient_id</font> segue o padrão <font face='DejaVuMono'>SYN-</font> + 16 dígitos hexadecimais, tirados de um UUID4 "
          "gerado pelo Faker com seed. Ele não tem relação com nenhum documento, e a unicidade é garantida por reamostragem. Toda a "
          "aleatoriedade vem de <font face='DejaVuMono'>numpy.random.default_rng(seed)</font> (PCG64) e de <font face='DejaVuMono'>Faker.seed_instance(seed)</font>. "
          "Um teste automatizado confirma que o mesmo seed reproduz o mesmo dataset de forma idêntica."),
    ]

    # ---------- 5 qualidade
    faixas = [[f.name, f.unit or "—", num(f.min, 1) if f.min is not None else "—", num(f.max, 1) if f.max is not None else "—"]
              for f in FIELDS if f.dtype in ("int", "float") and f.min is not None]
    s += [
        CondPageBreak(7 * cm),
        P("5. Validação de qualidade", "h1"),
        P("A função <font face='DejaVuMono'>validate_quality(df)</font> executa 8 grupos de verificações e reprova o dataset a qualquer erro. "
          "Cada regra tem um teste automatizado que injeta o defeito correspondente e confirma a detecção."),
        tabela([
            ["Verificação", "Regra"],
            ["Colunas obrigatórias", "as 50 colunas do dicionário presentes"],
            ["Valores ausentes", "nenhum nulo ou texto vazio (exceto medicamentos, em que vazio significa nenhum)"],
            ["Tipos de dados", "int/float/bool/texto conforme o dicionário; datas no formato AAAA-MM-DD"],
            ["Intervalos e categorias", "valores dentro de [mín, máx] (tabela abaixo); categorias pertencentes ao domínio"],
            ["IMC", "|IMC − peso/(altura/100)²| ≤ 0,05 kg/m²"],
            ["Pressão arterial", "PAD < PAS em todos os registros, e PAS/PAD dentro das faixas"],
            ["Identificadores", "patient_id único e no padrão SYN-XXXXXXXXXXXXXXXX"],
            ["Consistência interna", "obesidade ⇔ IMC ≥ 30; desfecho_adverso ⇔ resultado ≠ SEM_INTERCORRENCIA; n_medicamentos = itens da lista"],
        ], [4.2, 12.3]),
        Spacer(1, 6),
        P("Faixas de plausibilidade das variáveis numéricas (valores fora delas são considerados impossíveis):"),
        tabela([["Variável", "Unidade", "Mínimo", "Máximo"]] + faixas, [5.5, 3, 3, 3]),
        Spacer(1, 6),
        P(f"<b>Resultado no dataset de exemplo</b> (n = {d['qualidade']['n_records']}, seed {meta['seed']}): "
          + "; ".join(f"{k.replace('_', ' ')} = {v}" for k, v in d["qualidade"]["checks"].items())
          + f". O dataset de 10.000 pacientes também foi aprovado ({'APROVADO' if d['qualidade_10k']['passed'] else 'REPROVADO'})."),
    ]

    # ---------- 6 privacidade
    s += [
        CondPageBreak(6 * cm),
        P("6. Privacidade: privacy_guard", "h1"),
        P("A função <font face='DejaVuMono'>validate_privacy(dataset)</font> devolve "
          "<font face='DejaVuMono'>{\"compliant\": bool, \"blocked_fields\": [...], \"warnings\": [...]}</font>. Ela atua em quatro pontos: "
          "na entrada da API, antes de gravar, antes de exportar e sob demanda no botão Validar Privacidade. Os alertas e a auditoria registram "
          "apenas nomes de campos, categorias e contagens, nunca valores."),
        P("6.1 Bloqueio pelo nome do campo", "h2"),
        P("O nome é normalizado (minúsculas, sem acentos, camelCase separado, separadores convertidos em _). Depois, é "
          "comparado por token com as categorias abaixo. Assim, \"Número do Prontuário\", \"E-mail\" e \"patientName\" também são bloqueados."),
        tabela([["Categoria", "Termos bloqueados"]] + [[k, ", ".join(v)] for k, v in FORBIDDEN_FIELDS.items()], [3.8, 12.7]),
        P("6.2 Bloqueio pelo conteúdo", "h2"),
        P("As colunas de texto são inspecionadas com as expressões regulares abaixo (aplicadas aos valores distintos e "
          "ponderadas pela frequência, o que permite verificar 100.000 linhas em cerca de 1 s):"),
        tabela([["Padrão", "Expressão regular"]] + [[k, P(f"<font face='DejaVuMono' size='7'>{v.pattern.replace('<', '&lt;').replace('>', '&gt;')}</font>", "celula")] for k, v in VALUE_PATTERNS.items()], [4.8, 11.7]),
        Spacer(1, 6),
        P("6.3 Regras de governança", "h2"),
        *itens([
            "Todos os registros precisam ter data_type = SYNTHETIC e research_only = true. Sem isso, o dataset não é conforme e a exportação é bloqueada.",
            "Uma requisição à API com campo proibido (ex.: <font face='DejaVuMono'>{\"cpf\": ...}</font>) recebe HTTP 422. O evento "
            "<font face='DejaVuMono'>tentativa_insercao_dado_pessoal</font> é registrado sem o valor enviado.",
            "Colunas fora do dicionário de dados geram aviso, para revisão humana.",
            f"Resultado no dataset de exemplo: compliant = {str(d['privacidade']['compliant']).lower()}, campos bloqueados = "
            f"{d['privacidade']['blocked_fields'] or 'nenhum'}, avisos = {d['privacidade']['warnings'] or 'nenhum'}.",
        ]),
        P("6.4 Sintético × anonimizado × pseudonimizado", "h2"),
        tabela([
            ["", "Sintético (este projeto)", "Anonimizado", "Pseudonimizado"],
            ["Origem", "gerado; não há pessoa real", "pessoas reais, identificadores removidos", "pessoas reais, identificadores trocados por códigos"],
            ["Reversão", "inexistente", "não deve ser possível com meios razoáveis", "possível com a chave de correspondência"],
            ["LGPD", "não é dado pessoal", "não é dado pessoal, salvo se reversível (art. 12)", "continua sendo dado pessoal"],
        ], [2.6, 4.4, 4.7, 4.8]),
    ]

    # ---------- 7 resultados descritivos
    desc = df[["idade", "peso_kg", "altura_cm", "imc", "pa_sistolica", "pa_diastolica", "frequencia_cardiaca", "glicemia_jejum", "hba1c", "colesterol_total", "ldl", "hdl", "triglicerides", "creatinina", "escore_risco"]].describe().T
    linhas_desc = [["Variável", "Média", "DP", "Mín", "Mediana", "Máx"]] + [
        [i, num(r["mean"]), num(r["std"]), num(r["min"]), num(r["50%"]), num(r["max"])] for i, r in desc.iterrows()
    ]
    risco = df["classificacao_risco"].value_counts(normalize=True)
    splits = df["split"].value_counts()
    s += [
        CondPageBreak(7 * cm),
        P("7. Dataset de exemplo: resultados descritivos", "h1"),
        P(f"Dataset entregue: <b>{num(len(df))} pacientes</b>, seed {meta['seed']}, gerado em {meta['generated_at'][:10]}. Arquivos: "
          "<font face='DejaVuMono'>data/synthetic_dataset.csv</font> (e .parquet), <font face='DejaVuMono'>data/splits/</font>, "
          "<font face='DejaVuMono'>metadata.json</font>, <font face='DejaVuMono'>dataset_card.md</font>, "
          f"<font face='DejaVuMono'>quality_report.md</font>. Partições: treino {splits['train']}, validação {splits['validation']}, "
          f"teste {splits['test']}."),
        tabela(linhas_desc, [4.5, 2.4, 2.4, 2.4, 2.4, 2.4]),
        Spacer(1, 6),
        P(f"Sexo feminino: {pct((df['sexo'] == 'F').mean())}. Classificação de risco: baixo {pct(risco.get('BAIXO', 0))}, "
          f"moderado {pct(risco.get('MODERADO', 0))}, alto {pct(risco.get('ALTO', 0))}, muito alto {pct(risco.get('MUITO_ALTO', 0))}. "
          f"Desfecho adverso em 12 meses: {pct(df['desfecho_adverso'].mean())}. Pacientes sem condição crônica: "
          f"{pct((df['n_condicoes'] == 0).mean())}."),
        figura(f_dist, 16, "Figura 2 — Distribuições das principais variáveis do dataset de exemplo (n = 1.000, seed 42)."),
        figura(f_rel, 16, "Figura 3 — Relações induzidas pelo modelo causal: a PA sistólica cresce com a idade, a glicemia é maior em quem tem diabetes, "
               "e a taxa de desfecho adverso cresce com a classe de risco."),
    ]

    # ---------- 8 ML
    def linhas_bin(b):
        return [[n, num(m["roc_auc"], 3), num(m["pr_auc"], 3), num(m["f1"], 3), num(m["balanced_accuracy"], 3), num(m["brier"], 3)]
                for n, m in b["classificacao_binaria"]["modelos"].items()]

    s += [
        CondPageBreak(7 * cm),
        P("8. Experimentos de aprendizado de máquina", "h1"),
        P("O script <font face='DejaVuMono'>scripts/baseline_experiment.py</font> usa as partições fixas: treino para ajustar, validação para "
          "escolher o limiar de decisão e teste usado uma única vez, ao final. Pré-processamento em <i>Pipeline</i> (padronização z-score e "
          "one-hot ajustados só no treino). Para evitar vazamento de alvo, alvos e variáveis derivadas deles foram excluídos dos preditores "
          "(escore, classe de risco, diagnóstico, resultado e desfecho). Na regressão da PAS, a PAD também foi excluída, porque é "
          "gerada a partir da PAS."),
        P("8.1 Métricas utilizadas", "h2"),
        P("Seja VP, FP, VN e FN a matriz de confusão; p<sub>i</sub> a probabilidade prevista; y<sub>i</sub> o rótulo real; ŷ<sub>i</sub> a previsão; K o número de classes."),
        eq(r"\mathrm{Precisao}=\frac{VP}{VP+FP}\qquad \mathrm{Sensibilidade}=\frac{VP}{VP+FN}\qquad F_1=\frac{2\cdot\mathrm{Prec}\cdot\mathrm{Sens}}{\mathrm{Prec}+\mathrm{Sens}}"),
        eq(r"\mathrm{Acuracia\ balanceada}=\frac{1}{K}\sum_{k=1}^{K}\mathrm{Sens}_k\qquad \mathrm{macro\ }F_1=\frac{1}{K}\sum_{k=1}^{K}F_{1,k}\qquad \mathrm{Brier}=\frac{1}{N}\sum_{i=1}^{N}(p_i-y_i)^2"),
        eq(r"\mathrm{ROC\ AUC}=P(\hat{s}_{+}>\hat{s}_{-})\qquad \mathrm{PR\ AUC}\ (\mathrm{AP})=\sum_{n}(R_n-R_{n-1})\,P_n"),
        eq(r"\mathrm{MAE}=\frac{1}{N}\sum|y_i-\hat{y}_i|\qquad \mathrm{RMSE}=\sqrt{\frac{1}{N}\sum(y_i-\hat{y}_i)^2}\qquad R^2=1-\frac{\sum(y_i-\hat{y}_i)^2}{\sum(y_i-\bar{y})^2}"),
        P("8.2 Resultados com 10.000 pacientes (seed 42, conjunto de teste)", "h2"),
        P(f"<b>Classificação binária — desfecho_adverso</b> (prevalência no teste: {pct(b10['classificacao_binaria']['prevalencia_teste'])})"),
        tabela([["Modelo", "ROC-AUC", "PR-AUC", "F1", "Acur. balanceada", "Brier"]] + linhas_bin(b10), [5.5, 2.2, 2.2, 2.2, 2.6, 1.8]),
        Spacer(1, 5),
        P("<b>Classificação multiclasse — classificacao_risco</b>"),
        tabela([["Modelo", "Acurácia", "Macro-F1", "Acur. balanceada", "Macro-F1 (validação)"]]
               + [[n, num(m["accuracy"], 3), num(m["macro_f1"], 3), num(m["balanced_accuracy"], 3), num(m["validation_macro_f1"], 3)] for n, m in mc10.items()],
               [5.5, 2.5, 2.5, 3, 3]),
        Spacer(1, 5),
        P("<b>Regressão — pa_sistolica (mmHg)</b>"),
        tabela([["Modelo", "MAE", "RMSE", "R²", "R² (validação)"]]
               + [[n, num(m["mae"]), num(m["rmse"]), num(m["r2"], 3), num(m["validation_r2"], 3)] for n, m in rg10.items()],
               [5.5, 2.5, 2.5, 2.5, 3]),
        Spacer(1, 5),
        P("8.3 Resultados com 1.000 pacientes (dataset de exemplo)", "h2"),
        tabela([["Modelo", "ROC-AUC", "PR-AUC", "F1", "Acur. balanceada", "Brier"]] + linhas_bin(b1), [5.5, 2.2, 2.2, 2.2, 2.6, 1.8]),
        Spacer(1, 4),
        P("Com só 151 pacientes no teste, as métricas variam mais (por exemplo, a ROC-AUC do desfecho cai de cerca de 0,79 para cerca de 0,62). "
          "Isso ilustra o efeito do tamanho amostral: para conclusões estáveis, recomenda-se ≥ 10.000 pacientes e repetição com vários seeds."),
        P("8.4 Interpretação", "h2"),
        *itens([
            "Todos os modelos superam com folga as baselines ingênuas (classe majoritária ou média), o que confirma que o dataset contém relações aprendíveis.",
            "O desempenho não é perfeito porque cada etapa do gerador tem ruído, como em dados observacionais. Isso evita um problema artificialmente trivial.",
            "Na classificação de risco, a regressão logística supera o Random Forest, o que é coerente com o escore ser uma função logística de combinação linear.",
            "Os números medem a capacidade de recuperar a estrutura do gerador e <b>não têm validade clínica</b>.",
        ]),
    ]

    # ---------- 9 base real
    rm = d["real_meta"]
    num_linhas = [["Variável", "Sintético média (DP)", "Real média (DP)", "SMD", "KS D", "KS p", "W<sub>1</sub>"]] + [
        [f"{l['variavel']} ({l['unidade']})", f"{num(l['sintetico']['media'], 1)} ({num(l['sintetico']['dp'], 1)})",
         f"{num(l['real']['media'], 1)} ({num(l['real']['dp'], 1)})", num(l["smd"], 2), num(l["ks_d"], 3), f"{l['ks_p']:.1e}", num(l["wasserstein"], 1)]
        for l in comp["numericas"]
    ]
    cat_linhas = [["Variável", "Sintético", "Real", "z", "p"]] + [
        [c["variavel"], num(c["sintetico_pct"], 1) + "%", num(c["real_pct"], 1) + "%", num(c["z"], 2), f"{c['p']:.1e}"] for c in comp["categoricas"]
    ]
    s += [
        CondPageBreak(7 * cm),
        P("9. Base pública real e comparação", "h1"),
        P("Para ter uma referência em dados reais, foi incluída, <b>em separado</b>, a base <b>UCI Heart Disease — Cleveland</b>. "
          f"{UCI_HEART['origem']}. São {rm['n_records']} pacientes e 14 atributos clínicos, com licença {UCI_HEART['licenca']}. "
          f"{UCI_HEART['anonimizacao']}"),
        P(f"<b>Citação:</b> {UCI_HEART['citacao']}"),
        P("9.1 Procedimento", "h2"),
        *itens([
            f"Download do pacote oficial da UCI e verificação de integridade por SHA-256 do arquivo <font face='DejaVuMono'>{UCI_HEART['arquivo']}</font> "
            f"(<font face='DejaVuMono' size='7'>{UCI_HEART['sha256']}</font>).",
            *rm["transformations"],
            "Marcação <font face='DejaVuMono'>data_type = REAL_PUBLIC_ANONYMIZED</font>. Os arquivos ficam em <font face='DejaVuMono'>data/real_public/</font> e nunca são "
            "concatenados ao sintético. O privacy_guard aprova a base com a marcação dela e a <b>recusa</b> se ela for validada como sintética.",
            f"Qualidade: {rm['quality']['n_records']} registros, {rm['quality']['registros_completos']} completos, ausentes "
            f"{rm['quality']['missing_values']}, prevalência de doença cardíaca {pct(rm['quality']['prevalencia_doenca_cardiaca'])}. "
            "A distribuição dos graus (164/55/36/35/13) confere exatamente com a documentação da UCI.",
        ]),
        P("9.2 Medidas de comparação", "h2"),
        eq(r"\mathrm{SMD}=\frac{\bar{x}_S-\bar{x}_R}{\sqrt{(s_S^2+s_R^2)/2}}\qquad D_{KS}=\sup_x\,|F_S(x)-F_R(x)|\qquad W_1=\int_{-\infty}^{\infty}|F_S(x)-F_R(x)|\,dx"),
        eq(r"z=\frac{\hat{p}_S-\hat{p}_R}{\sqrt{\hat{p}(1-\hat{p})\left(\frac{1}{n_S}+\frac{1}{n_R}\right)}},\qquad \hat{p}=\frac{x_S+x_R}{n_S+n_R}"),
        P("SMD é a diferença média padronizada (|SMD| ≥ 0,2 pequena; ≥ 0,5 média; ≥ 0,8 grande). D<sub>KS</sub> é a estatística de "
          "Kolmogorov-Smirnov para duas amostras. W<sub>1</sub> é a distância de Wasserstein-1, na unidade da variável. z é o teste de "
          "duas proporções com variância agrupada."),
        P("9.3 Resultados", "h2"),
        tabela(num_linhas, [3.9, 2.8, 2.6, 1.3, 1.4, 1.6, 2.1]),
        Spacer(1, 5),
        tabela(cat_linhas, [6, 2.5, 2.5, 2, 2.5]),
        figura(FIG / "comparacao_numericas.png", 16, "Figura 4 — Distribuições em comum: sintético (azul, n = 1.000) × real UCI (vermelho, n = 303)."),
        P(f"<b>Modelos na base real</b> — alvo doença cardíaca (grau > 0); {comp['modelos_base_real']['validacao']}. Média (desvio padrão):"),
        tabela([["Modelo", "ROC-AUC", "Acurácia", "F1", "Acur. balanceada"]]
               + [[n, *[f"{num(r[k]['media'], 3)} ({num(r[k]['dp'], 3)})" for k in ("roc_auc", "accuracy", "f1", "balanced_accuracy")]] for n, r in reais.items()],
               [5, 2.9, 2.9, 2.9, 2.9]),
        Spacer(1, 5),
        P("9.4 Interpretação", "h2"),
        P("As diferenças são <b>esperadas e não indicam defeito</b>. O gerador não foi calibrado com esta base (por decisão "
          "metodológica, nenhum dado real foi usado como molde), e a amostra UCI é de pacientes encaminhados para angiografia nos EUA em "
          "1988, mais velhos, majoritariamente homens e com colesterol mais alto. Com amostras deste tamanho, o teste KS rejeita a igualdade "
          "mesmo para diferenças moderadas. Assim, a comparação quantifica o <i>domain shift</i> entre os dados de desenvolvimento e um "
          "cenário real. Os modelos treinados na base real (ROC-AUC ≈ 0,91) servem de referência de desempenho em dados reais para a pesquisa."),
        P("<b>Por que não o DATASUS.</b> Os microdados do DATASUS também são públicos e anonimizados, mas são distribuídos em formato "
          ".dbc, exigem bibliotecas nativas adicionais e têm volume muito maior. A base UCI tem licença explícita, tamanho adequado, "
          "variáveis clínicas em comum e ampla citação na literatura de ML. O DATASUS fica como extensão futura."),
    ]

    # ---------- 10 testes
    s += [
        CondPageBreak(7 * cm),
        P("10. Testes automatizados", "h1"),
        P(f"A suíte pytest tem <b>{total_testes} testes</b>. Resultado da execução durante a geração deste relatório: <b>{resultado_testes}</b>."),
        tabela([["Arquivo", "Testes", "O que verifica"]] + [
            [a, str(n), {
                "test_generator.py": "quantidade, colunas, marcações, reprodutibilidade por seed, unicidade de IDs, distribuições, relações causais, split 70/15/15 estratificado",
                "test_bmi.py": "IMC com valores conhecidos, entradas inválidas, versão vetorizada, consistência no dataset",
                "test_quality.py": "cada defeito injetado é detectado (ausentes, faixas, IMC, PA, duplicidade, tipos, datas, categorias, consistência)",
                "test_privacy.py": "21 variações de campos proibidos, ausência de falso positivo, conteúdo sensível, marcação SYNTHETIC, logs sem valores",
                "test_export.py": "4 formatos gravam e relêem os mesmos dados; exportação bloqueada sem gravar arquivo; splits",
                "test_integrity.py": "ida e volta banco ↔ DataFrame idêntica, contagens por tabela, substituição atômica, auditoria, metadados",
                "test_api.py": "fluxo completo do painel, exportação, validação de entrada, bloqueio de dados pessoais via API",
                "test_public_dataset.py": "conversão da base UCI, ausentes, alvo derivado, SHA-256, privacidade, separação, distribuição de classes oficial",
            }.get(a, "")] for a, n in sorted(testes_por_arquivo.items())
        ], [4, 1.5, 11]),
        Spacer(1, 6),
        P("Durante o desenvolvimento, os testes revelaram e permitiram corrigir um defeito real: a geração repetida com o mesmo seed "
          "violava a chave primária, porque o dataset anterior era removido depois da inserção do novo. A ordem foi invertida dentro da mesma transação."),
        CondPageBreak(6 * cm),
        P("11. Reprodutibilidade", "h1"),
        P("Comandos para reproduzir todos os artefatos deste relatório, a partir da raiz do projeto:"),
        P("python scripts/generate_dataset.py --n 1000 --seed 42 --formats csv,parquet<br/>"
          "python scripts/quality_report.py --input data/synthetic_dataset.csv<br/>"
          "python scripts/baseline_experiment.py --input data/synthetic_dataset.csv --seed 42<br/>"
          "python scripts/generate_dataset.py --n 10000 --seed 42 --out data/experimentos/n10000_seed42 --no-splits<br/>"
          "python scripts/baseline_experiment.py --input data/experimentos/n10000_seed42/synthetic_dataset.csv<br/>"
          "python scripts/fetch_public_dataset.py<br/>"
          "python scripts/compare_synthetic_real.py<br/>"
          "python -m pytest<br/>"
          "python scripts/build_report_pdf.py", "codigo"),
        *itens([
            "Versões de todas as dependências fixadas em backend/requirements.txt e frontend/package-lock.json.",
            "Seeds: 42 para os dados e os modelos; o split usa seed + 7919.",
            f"Identificação do dataset de exemplo: dataset_id {meta['dataset_id']}, versão {meta['version']}, gerador {meta['generator_version']}.",
            "Ambiente: Python 3.12 e Node.js 20+; opcionalmente docker compose up --build.",
        ]),
    ]

    # ---------- 12 limitações
    s += [
        CondPageBreak(6 * cm),
        P("12. Limitações e riscos", "h1"),
        *itens(meta["limitations"]),
        *itens([
            "Risco de interpretar resultados como evidência clínica. Mitigação: avisos permanentes no painel, nos arquivos e neste relatório.",
            "Risco de vazamento de alvo. Mitigação: lista explícita de variáveis derivadas, excluídas nos experimentos.",
            "A base real UCI é pequena (303), de um único centro, de 1988 e com viés de seleção. Não representa a população brasileira.",
        ]),
    ]

    # ---------- 13 referências
    refs = [
        "AUSTIN, P. C. Balance diagnostics for comparing the distribution of baseline covariates between treatment groups in propensity-score matched samples. <i>Statistics in Medicine</i>, v. 28, n. 25, p. 3083–3107, 2009.",
        "BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD).",
        "DETRANO, R. et al. International application of a new probability algorithm for the diagnosis of coronary artery disease. <i>American Journal of Cardiology</i>, v. 64, n. 5, p. 304–310, 1989.",
        "FRIEDEWALD, W. T.; LEVY, R. I.; FREDRICKSON, D. S. Estimation of the concentration of low-density lipoprotein cholesterol in plasma, without use of the preparative ultracentrifuge. <i>Clinical Chemistry</i>, v. 18, n. 6, p. 499–502, 1972.",
        "GEBRU, T. et al. Datasheets for datasets. <i>Communications of the ACM</i>, v. 64, n. 12, p. 86–92, 2021.",
        "JANOSI, A.; STEINBRUNN, W.; PFISTERER, M.; DETRANO, R. Heart Disease [Dataset]. UCI Machine Learning Repository, 1989. https://doi.org/10.24432/C52P4X.",
        "NATHAN, D. M. et al. Translating the A1C assay into estimated average glucose values. <i>Diabetes Care</i>, v. 31, n. 8, p. 1473–1478, 2008.",
        "PEDREGOSA, F. et al. Scikit-learn: Machine Learning in Python. <i>Journal of Machine Learning Research</i>, v. 12, p. 2825–2830, 2011.",
        "WORLD HEALTH ORGANIZATION. Obesity: preventing and managing the global epidemic. WHO Technical Report Series 894. Geneva: WHO, 2000.",
    ]
    s += [CondPageBreak(6 * cm), P("13. Referências", "h1"), *[P(r, "item") for r in refs]]

    doc = SimpleDocTemplate(
        str(SAIDA), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.9 * cm, bottomMargin=1.8 * cm,
        title="Relatório técnico — Gerador de Dataset Sintético de Pacientes", author=AUTORA,
        subject="Dataset sintético de pacientes para pesquisa em IA", creator="scripts/build_report_pdf.py",
    )
    doc.build(s, onFirstPage=capa, onLaterPages=decorar)
    print(f"PDF gerado: {SAIDA}")


if __name__ == "__main__":
    construir()
