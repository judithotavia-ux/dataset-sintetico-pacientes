import { useEffect, useState } from 'react'
import { api, type PatientsPage, type SplitFilter } from '../api'

const PAGE_SIZE = 25

function formatCell(value: string | number | boolean) {
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') return value.toLocaleString('pt-BR')
  return value === '' ? '—' : value
}

export function DataViewer({ onClose }: { onClose: () => void }) {
  const [page, setPage] = useState(1)
  const [split, setSplit] = useState<SplitFilter>('all')
  const [data, setData] = useState<PatientsPage | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let ativo = true
    setLoading(true)
    api
      .patients(page, PAGE_SIZE, split)
      .then((d) => ativo && (setData(d), setError('')))
      .catch((e: Error) => ativo && setError(e.message))
      .finally(() => ativo && setLoading(false))
    return () => {
      ativo = false
    }
  }, [page, split])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4" role="dialog" aria-modal="true">
      <div className="flex max-h-[90vh] w-full max-w-7xl flex-col rounded-xl bg-white shadow-2xl">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Visualizar dados</h2>
            <p className="text-xs font-medium text-amber-700">Todos os registros são SINTÉTICOS — nenhum corresponde a uma pessoa real.</p>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-slate-600">
              Partição{' '}
              <select
                className="ml-1 rounded-md border border-slate-300 px-2 py-1 text-sm"
                value={split}
                onChange={(e) => {
                  setSplit(e.target.value as SplitFilter)
                  setPage(1)
                }}
              >
                <option value="all">Todas</option>
                <option value="train">Treino (70%)</option>
                <option value="validation">Validação (15%)</option>
                <option value="test">Teste (15%)</option>
              </select>
            </label>
            <button onClick={onClose} className="rounded-md border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100">
              Fechar
            </button>
          </div>
        </header>

        <div className="relative flex-1 overflow-auto">
          {error && <p className="p-5 text-sm text-red-700">{error}</p>}
          {data && (
            <table className="min-w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-100 text-slate-700">
                <tr>
                  {data.columns.map((c) => (
                    <th key={c} className="whitespace-nowrap px-3 py-2 font-semibold">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr key={String(row.patient_id)} className="border-t border-slate-100 odd:bg-white even:bg-slate-50">
                    {data.columns.map((c) => (
                      <td key={c} className="whitespace-nowrap px-3 py-1.5 text-slate-800">
                        {formatCell(row[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {loading && <div className="absolute inset-0 flex items-center justify-center bg-white/60 text-sm text-slate-600">Carregando…</div>}
        </div>

        <footer className="flex items-center justify-between border-t border-slate-200 px-5 py-3 text-sm text-slate-600">
          <span>{data ? `${data.total.toLocaleString('pt-BR')} registros` : ''}</span>
          <div className="flex items-center gap-2">
            <button className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Anterior
            </button>
            <span>
              Página {page} de {totalPages}
            </span>
            <button className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
              Próxima
            </button>
          </div>
        </footer>
      </div>
    </div>
  )
}
