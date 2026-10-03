import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { CountItem } from '../api'

const fmt = (v: number) => v.toLocaleString('pt-BR')

const LABELS: Record<string, string> = {
  F: 'Feminino',
  M: 'Masculino',
  BAIXO: 'Baixo',
  MODERADO: 'Moderado',
  ALTO: 'Alto',
  MUITO_ALTO: 'Muito alto',
  HIPERTENSAO: 'Hipertensão',
  DIABETES_TIPO_2: 'Diabetes tipo 2',
  DISLIPIDEMIA: 'Dislipidemia',
  OBESIDADE: 'Obesidade',
  ASMA: 'Asma',
  DOENCA_RENAL_CRONICA: 'Doença renal crônica',
  INFECCAO_RESPIRATORIA_AGUDA: 'Infecção resp. aguda',
  SEM_CONDICAO_CRONICA: 'Sem condição',
  SEM_INTERCORRENCIA: 'Sem intercorrência',
  INTERNACAO: 'Internação',
  EVENTO_CARDIOVASCULAR: 'Evento cardiovascular',
  OBITO: 'Óbito',
}

const label = (l: string) => LABELS[l] ?? l
const withLabels = (data: CountItem[]) => data.map((d) => ({ ...d, nome: label(d.label) }))

export function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      <div className="mt-3 h-64">{children}</div>
    </section>
  )
}

export function VerticalBars({ data, color = '#2563eb', colors }: { data: CountItem[]; color?: string; colors?: string[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={withLabels(data)} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey="nome" tick={{ fontSize: 11 }} interval={0} />
        <YAxis tick={{ fontSize: 11 }} tickFormatter={fmt} width={52} />
        <Tooltip formatter={(v) => [fmt(Number(v)), 'Pacientes']} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} fill={color} isAnimationActive={false}>
          {colors && data.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function HorizontalBars({ data, color = '#0d9488' }: { data: CountItem[]; color?: string }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={withLabels(data)} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
        <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={fmt} />
        <YAxis type="category" dataKey="nome" tick={{ fontSize: 11 }} width={130} />
        <Tooltip formatter={(v) => [fmt(Number(v)), 'Pacientes']} />
        <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function Donut({ data, colors }: { data: CountItem[]; colors: string[] }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1
  return (
    <div className="flex h-full items-center gap-4">
      <ResponsiveContainer width="60%" height="100%">
        <PieChart>
          <Pie data={withLabels(data)} dataKey="value" nameKey="nome" innerRadius="55%" outerRadius="85%" paddingAngle={2} isAnimationActive={false}>
            {data.map((_, i) => (
              <Cell key={i} fill={colors[i % colors.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v) => [fmt(Number(v)), 'Pacientes']} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="space-y-2 text-sm">
        {data.map((d, i) => (
          <li key={d.label} className="flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-sm" style={{ background: colors[i % colors.length] }} />
            <span className="text-slate-700">{label(d.label)}</span>
            <span className="font-semibold text-slate-900">{((100 * d.value) / total).toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
