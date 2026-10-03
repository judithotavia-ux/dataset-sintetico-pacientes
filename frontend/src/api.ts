// Cliente da API FastAPI. Em desenvolvimento o Vite encaminha /api para http://localhost:8000.
const BASE = import.meta.env.VITE_API_URL ?? '/api'

export const DATASET_SIZES = [100, 1_000, 10_000, 100_000] as const
export type DatasetSize = (typeof DATASET_SIZES)[number]
export type ExportFormat = 'csv' | 'xlsx' | 'json' | 'parquet'
export type SplitFilter = 'all' | 'train' | 'validation' | 'test'

export interface CountItem {
  label: string
  value: number
}

export interface DatasetInfo {
  dataset_id: string
  nome: string
  versao: string
  seed: number
  n_registros: number
  criado_em: string
  data_type: 'SYNTHETIC'
  research_only: boolean
  privacy_compliant: boolean
  quality_passed: boolean
}

export interface PrivacyReport {
  compliant: boolean
  blocked_fields: string[]
  warnings: string[]
}

export interface DashboardStats {
  n_registros: number
  idade: CountItem[]
  sexo: CountItem[]
  imc: CountItem[]
  condicoes: CountItem[]
  classificacao_risco: CountItem[]
  desfecho: CountItem[]
  split: CountItem[]
  medias: Record<'idade' | 'imc' | 'pa_sistolica' | 'pa_diastolica' | 'desfecho_adverso_pct', number>
  registros_por_tabela: Record<'patients' | 'clinical_records' | 'lab_results' | 'medications', number>
}

export interface CurrentDataset {
  dataset: DatasetInfo
  stats: DashboardStats
  privacy: PrivacyReport | null
  privacy_checked: boolean
}

export interface PatientsPage {
  total: number
  page: number
  page_size: number
  columns: string[]
  rows: Record<string, string | number | boolean>[]
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new ApiError(0, 'Não foi possível conectar ao backend. Verifique se a API está rodando em http://localhost:8000.')
  }
  if (!response.ok) {
    let message = `Erro ${response.status}`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') message = body.detail
      if (Array.isArray(body.blocked_fields) && body.blocked_fields.length) message += ` Campos: ${body.blocked_fields.join(', ')}`
    } catch {
      /* resposta sem JSON */
    }
    throw new ApiError(response.status, message)
  }
  return response.json() as Promise<T>
}

export const api = {
  current: () => request<CurrentDataset>('/datasets/current'),
  generate: (n_records: DatasetSize, seed: number | null) =>
    request<{ dataset: DatasetInfo; privacy: PrivacyReport }>('/datasets/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ n_records, seed }),
    }),
  validatePrivacy: () => request<PrivacyReport>('/privacy/validate', { method: 'POST' }),
  patients: (page: number, pageSize: number, split: SplitFilter) =>
    request<PatientsPage>(`/datasets/current/patients?page=${page}&page_size=${pageSize}&split=${split}`),

  async download(format: ExportFormat, split: SplitFilter = 'all'): Promise<string> {
    let response: Response
    try {
      response = await fetch(`${BASE}/export/${format}?split=${split}`)
    } catch {
      throw new ApiError(0, 'Não foi possível conectar ao backend.')
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      const campos = Array.isArray(body.blocked_fields) && body.blocked_fields.length ? ` Campos: ${body.blocked_fields.join(', ')}` : ''
      throw new ApiError(response.status, `${body.detail ?? `Erro ${response.status}`}${campos}`)
    }
    const disposition = response.headers.get('Content-Disposition') ?? ''
    const filename = /filename="?([^"]+)"?/.exec(disposition)?.[1] ?? `synthetic_patients.${format}`
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    return filename
  },
}
