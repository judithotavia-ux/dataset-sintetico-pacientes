import { useCallback, useEffect, useState } from 'react'
import { api, ApiError, DATASET_SIZES, type CurrentDataset, type DatasetSize, type ExportFormat, type PrivacyReport } from './api'
import { ChartCard, Donut, HorizontalBars, VerticalBars } from './components/Charts'
import { DataViewer } from './components/DataViewer'

const DISCLAIMER = 'DATASET SINTÉTICO — NÃO CONTÉM DADOS REAIS DE PACIENTES'
const RISK_COLORS = ['#16a34a', '#eab308', '#f97316', '#dc2626']
const SEX_COLORS = ['#db2777', '#2563eb']

type Notice = { kind: 'success' | 'error' | 'info'; text: string } | null

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

function PrivacyPanel({ report, checked, onValidate, busy }: { report: PrivacyReport | null; checked: boolean; onValidate: () => void; busy: boolean }) {
  const status = !checked || !report ? 'pendente' : report.compliant ? 'conforme' : 'bloqueado'
  const styles = {
    pendente: 'border-slate-300 bg-slate-50 text-slate-700',
    conforme: 'border-green-300 bg-green-50 text-green-800',
    bloqueado: 'border-red-300 bg-red-50 text-red-800',
  }[status]
  return (
    <section className={`rounded-xl border p-4 ${styles}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">Status de privacidade (privacy_guard)</h3>
          <p className="text-2xl font-bold">
            {status === 'pendente' && 'Não validado'}
            {status === 'conforme' && '✓ Conforme'}
            {status === 'bloqueado' && '✕ Bloqueado'}
          </p>
        </div>
        <button onClick={onValidate} disabled={busy} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">
          Validar Privacidade
        </button>
      </div>
      {report && (
        <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <p className="font-medium">Campos bloqueados</p>
            <p>{report.blocked_fields.length ? report.blocked_fields.join(', ') : 'Nenhum (CPF, RG, CNS, prontuário, telefone, e-mail, endereço e nome ausentes)'}</p>
          </div>
          <div>
            <p className="font-medium">Avisos</p>
            <p>{report.warnings.length ? report.warnings.join(' ') : 'Nenhum. Todos os registros marcados como SYNTHETIC e research_only.'}</p>
          </div>
        </div>
      )}
    </section>
  )
}

export default function App() {
  const [current, setCurrent] = useState<CurrentDataset | null>(null)
  const [size, setSize] = useState<DatasetSize>(1_000)
  const [seed, setSeed] = useState('42')
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<Notice>(null)
  const [viewer, setViewer] = useState(false)
  const [loaded, setLoaded] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const dados = await api.current()
      setCurrent(dados)
      const n = dados.dataset.n_registros
      if ((DATASET_SIZES as readonly number[]).includes(n)) setSize(n as DatasetSize)
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setCurrent(null)
      else setNotice({ kind: 'error', text: (e as Error).message })
    } finally {
      setLoaded(true)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function run(label: string, action: () => Promise<void>) {
    setBusy(label)
    setNotice(null)
    try {
      await action()
    } catch (e) {
      setNotice({ kind: 'error', text: (e as Error).message })
    } finally {
      setBusy(null)
    }
  }

  const generate = (useRandomSeed: boolean) =>
    run(useRandomSeed ? 'novo' : 'gerar', async () => {
      const seedValue = useRandomSeed ? null : seed.trim() === '' ? null : Number(seed)
      if (seedValue !== null && (!Number.isInteger(seedValue) || seedValue < 0)) throw new Error('O seed deve ser um número inteiro maior ou igual a zero.')
      const result = await api.generate(size, seedValue)
      setSeed(String(result.dataset.seed))
      await refresh()
      setNotice({ kind: 'success', text: `${result.dataset.n_registros.toLocaleString('pt-BR')} pacientes sintéticos gerados (seed ${result.dataset.seed}).` })
    })

  const validatePrivacy = () =>
    run('privacidade', async () => {
      const report = await api.validatePrivacy()
      setCurrent((c) => (c ? { ...c, privacy: report, privacy_checked: true } : c))
      setNotice(report.compliant ? { kind: 'success', text: 'Privacidade validada: dataset conforme.' } : { kind: 'error', text: 'Dataset NÃO conforme: exportação bloqueada.' })
    })

  const exportAs = (format: ExportFormat) =>
    run(`export-${format}`, async () => {
      const filename = await api.download(format)
      setNotice({ kind: 'success', text: `Arquivo exportado: ${filename}` })
    })

  const stats = current?.stats
  const totalRows = stats ? Object.values(stats.registros_por_tabela).reduce((a, b) => a + b, 0) : 0
  const hasData = Boolean(current)
  const btn = 'rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50'

  return (
    <div className="min-h-screen text-slate-900">
      <div className="sticky top-0 z-40 bg-amber-400 px-4 py-2 text-center text-sm font-bold tracking-wide text-amber-950 shadow" role="status">
        ⚠ {DISCLAIMER}
      </div>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">Gerador de Dataset Sintético de Pacientes</h1>
            <p className="text-sm text-slate-600">Pesquisa acadêmica em Inteligência Artificial · dados fictícios, reprodutíveis por seed · uso exclusivo em pesquisa</p>
          </div>
          {current && (
            <p className="text-xs text-slate-500">
              dataset <code>{current.dataset.dataset_id.slice(0, 8)}</code> · v{current.dataset.versao} · gerado em {new Date(current.dataset.criado_em + 'Z').toLocaleString('pt-BR')}
            </p>
          )}
        </header>

        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm">
              <span className="block text-xs font-medium text-slate-600">Quantidade de pacientes</span>
              <select className="mt-1 rounded-lg border border-slate-300 px-3 py-2" value={size} onChange={(e) => setSize(Number(e.target.value) as DatasetSize)}>
                {DATASET_SIZES.map((n) => (
                  <option key={n} value={n}>
                    {n.toLocaleString('pt-BR')}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="block text-xs font-medium text-slate-600">Seed (reprodutibilidade)</span>
              <input className="mt-1 w-32 rounded-lg border border-slate-300 px-3 py-2" inputMode="numeric" value={seed} onChange={(e) => setSeed(e.target.value.replace(/\D/g, ''))} placeholder="aleatório" />
            </label>
            <button className={`${btn} bg-blue-600 text-white hover:bg-blue-700`} disabled={!!busy} onClick={() => generate(false)}>
              {busy === 'gerar' ? 'Gerando…' : 'Gerar Dataset'}
            </button>
            <button className={`${btn} border border-blue-600 text-blue-700 hover:bg-blue-50`} disabled={!!busy} onClick={() => generate(true)} title="Gera um novo dataset com seed aleatório">
              {busy === 'novo' ? 'Gerando…' : 'Gerar Novo Dataset'}
            </button>
            <button className={`${btn} border border-slate-300 hover:bg-slate-100`} disabled={!hasData || !!busy} onClick={() => setViewer(true)}>
              Visualizar Dados
            </button>
            <span className="mx-1 hidden h-8 w-px bg-slate-200 md:block" />
            {(
              [
                ['csv', 'Exportar CSV'],
                ['xlsx', 'Exportar Excel'],
                ['json', 'Exportar JSON'],
                ['parquet', 'Exportar Parquet'],
              ] as [ExportFormat, string][]
            ).map(([format, text]) => (
              <button key={format} className={`${btn} border border-slate-300 hover:bg-slate-100`} disabled={!hasData || !!busy} onClick={() => exportAs(format)}>
                {busy === `export-${format}` ? 'Exportando…' : text}
              </button>
            ))}
          </div>
          {(busy === 'gerar' || busy === 'novo') && size >= 10_000 && (
            <p className="mt-3 text-xs text-slate-500">Gerando {size.toLocaleString('pt-BR')} pacientes, validando qualidade e privacidade e gravando no banco… (100.000 leva cerca de 30 segundos)</p>
          )}
          {busy === 'export-xlsx' && (stats?.n_registros ?? 0) >= 10_000 && <p className="mt-3 text-xs text-slate-500">Planilhas grandes demoram (100.000 linhas ≈ 30 s). Para ML, prefira CSV ou Parquet.</p>}
        </section>

        {notice && (
          <div
            className={`rounded-lg border px-4 py-3 text-sm ${
              notice.kind === 'success' ? 'border-green-300 bg-green-50 text-green-800' : notice.kind === 'error' ? 'border-red-300 bg-red-50 text-red-800' : 'border-blue-300 bg-blue-50 text-blue-800'
            }`}
          >
            {notice.text}
          </div>
        )}

        {!loaded && <p className="text-sm text-slate-500">Carregando…</p>}

        {loaded && !current && !notice && (
          <div className="rounded-xl border-2 border-dashed border-slate-300 p-10 text-center text-slate-600">
            Nenhum dataset gerado ainda. Escolha a quantidade e clique em <strong>Gerar Dataset</strong>.
          </div>
        )}

        {current && stats && (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Stat label="Pacientes gerados" value={stats.n_registros.toLocaleString('pt-BR')} hint={`Seed ${current.dataset.seed}`} />
              <Stat
                label="Registros no banco"
                value={totalRows.toLocaleString('pt-BR')}
                hint={`${stats.registros_por_tabela.lab_results.toLocaleString('pt-BR')} exames · ${stats.registros_por_tabela.medications.toLocaleString('pt-BR')} medicamentos`}
              />
              <Stat label="Médias" value={`${stats.medias.idade} anos`} hint={`IMC ${stats.medias.imc} · PA ${stats.medias.pa_sistolica}/${stats.medias.pa_diastolica} mmHg`} />
              <Stat
                label="Partições ML"
                value={stats.split.map((s) => s.value.toLocaleString('pt-BR')).join(' / ')}
                hint={`treino / validação / teste · desfecho adverso ${stats.medias.desfecho_adverso_pct}%`}
              />
            </div>

            <PrivacyPanel report={current.privacy} checked={current.privacy_checked} onValidate={validatePrivacy} busy={!!busy} />

            <div className="grid gap-4 lg:grid-cols-2">
              <ChartCard title="Distribuição de idade" subtitle="Pacientes por faixa etária (anos)">
                <VerticalBars data={stats.idade} />
              </ChartCard>
              <ChartCard title="Distribuição por sexo">
                <Donut data={stats.sexo} colors={SEX_COLORS} />
              </ChartCard>
              <ChartCard title="Distribuição de IMC" subtitle="Categorias de índice de massa corporal (kg/m²)">
                <VerticalBars data={stats.imc} color="#7c3aed" />
              </ChartCard>
              <ChartCard title="Classificação de risco" subtitle="Escore sintético — não é escore clínico validado">
                <VerticalBars data={stats.classificacao_risco} colors={RISK_COLORS} />
              </ChartCard>
              <ChartCard title="Condições clínicas sintéticas" subtitle="Um paciente pode ter mais de uma condição">
                <HorizontalBars data={stats.condicoes} />
              </ChartCard>
              <ChartCard title="Desfecho simulado em 12 meses">
                <HorizontalBars data={stats.desfecho} color="#475569" />
              </ChartCard>
            </div>
          </>
        )}

        <footer className="border-t border-slate-200 pt-4 text-xs text-slate-500">
          {DISCLAIMER}. Dados gerados artificialmente para pesquisa acadêmica; não utilizar em decisões clínicas. API: <a className="underline" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">/docs</a>
        </footer>
      </main>

      {viewer && <DataViewer onClose={() => setViewer(false)} />}
    </div>
  )
}
