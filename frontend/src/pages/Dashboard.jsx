import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, CircleDollarSign, FileWarning, ShieldCheck, Users } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import DashboardCharts from '../components/DashboardCharts.jsx'
import KpiCard from '../components/KpiCard.jsx'
import RiskBadge from '../components/RiskBadge.jsx'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [providers, setProviders] = useState([])
  const [cities, setCities] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([claimsApi.summary(), claimsApi.providers(), claimsApi.cities()])
      .then(([summaryData, providerData, cityData]) => {
        setSummary(summaryData)
        setProviders(providerData)
        setCities(cityData)
      })
      .catch(() => setError('No se pudo conectar con la API. Ejecuta el backend para ver datos.'))
  }, [])

  if (error) return <EmptyState text={error} />
  if (!summary) return <EmptyState text="Cargando análisis de siniestros..." />

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <KpiCard title="Total de siniestros" value={summary.total_claims} helper="Base sintética" icon={ShieldCheck} />
        <KpiCard title="Casos verdes" value={summary.green_cases} helper="Riesgo bajo" tone="green" icon={CheckCircle2} />
        <KpiCard title="Casos amarillos" value={summary.yellow_cases} helper="Revisión recomendada" tone="yellow" icon={AlertTriangle} />
        <KpiCard title="Casos rojos" value={summary.red_cases} helper="Prioridad humana" tone="red" icon={FileWarning} />
        <KpiCard title="Monto reclamado" value={`$${Number(summary.total_claim_amount).toLocaleString()}`} helper="Total analizado" icon={CircleDollarSign} />
        <KpiCard title="Proveedores con alertas" value={summary.providers_with_alerts} helper="Medio o alto" tone="slate" icon={Users} />
      </div>
      <div className="rounded-lg border border-blue-100 bg-blue-50 p-5 text-blue-950">
        <p className="font-bold">Resumen inteligente</p>
        <p className="mt-2 leading-7">{summary.smart_summary}</p>
      </div>
      <DashboardCharts summary={summary} cities={cities} providers={providers} />
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
        <h3 className="mb-4 font-bold text-ink">Top 10 siniestros con mayor posible riesgo</h3>
        <div className="grid gap-3 lg:grid-cols-2">
          {summary.top_claims.map((claim) => (
            <div key={claim.claim_id} className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 p-4">
              <div>
                <p className="font-bold text-electric">{claim.claim_id}</p>
                <p className="text-sm text-slate-600">{claim.city} · {claim.provider_name}</p>
              </div>
              <div className="text-right">
                <p className="text-xl font-bold text-ink">{claim.risk_score}</p>
                <RiskBadge level={claim.risk_level} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ text }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-8 text-slate-600 shadow-soft">{text}</div>
}
