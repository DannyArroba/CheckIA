import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, CircleDollarSign, FileWarning, ShieldCheck, Users } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import DashboardCharts from '../components/DashboardCharts.jsx'
import KpiCard from '../components/KpiCard.jsx'
import RiskBadge from '../components/RiskBadge.jsx'
import { HackiaDetail } from './Hackia.jsx'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [claims, setClaims] = useState([])
  const [providers, setProviders] = useState([])
  const [cities, setCities] = useState([])
  const [filters, setFilters] = useState({ risk: null, city: null, provider: null })
  const [selectedClaim, setSelectedClaim] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([claimsApi.hackiaSummary(), claimsApi.hackiaClaims()])
      .then(([summaryData, claimsData]) => {
        const mappedClaims = claimsData.map(mapHackiaClaimForDashboard)
        setSummary(buildHackiaDashboardSummary(summaryData, claimsData, mappedClaims))
        setClaims(mappedClaims)
        setProviders(buildProviderRanking(claimsData))
        setCities(buildCityRanking(claimsData))
      })
      .catch(() => setError('No se pudo conectar con la API. Ejecuta el backend y carga tu Excel.'))
  }, [])

  const visibleClaims = useMemo(() => {
    const hasFilters = filters.risk || filters.city || filters.provider
    if (!hasFilters) return summary?.top_claims || []
    return claims
      .filter((claim) => !filters.risk || claim.risk_level === filters.risk)
      .filter((claim) => !filters.city || claim.city === filters.city)
      .filter((claim) => !filters.provider || claim.provider_name === filters.provider)
      .sort((a, b) => b.risk_score - a.risk_score)
      .slice(0, 30)
  }, [claims, filters, summary])

  const activeFilterCount = [filters.risk, filters.city, filters.provider].filter(Boolean).length

  function toggleFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: current[key] === value ? null : value }))
  }

  async function openClaim(claimId) {
    const detail = await claimsApi.hackiaClaim(claimId)
    setSelectedClaim(detail)
  }

  function formatMoney(value) {
    return `$${Number(value || 0).toLocaleString('es-EC', { maximumFractionDigits: 0 })}`
  }

  if (error) return <EmptyState text={error} />
  if (!summary) return <EmptyState text="Cargando analisis de siniestros..." />
  if (!summary.total_claims) return <EmptyState text="Aun no hay siniestros cargados. Sube tu Excel desde Datos o arrastralo sobre la pantalla." />

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <KpiCard title="Total de siniestros" value={summary.total_claims} helper="Dataset importado" icon={ShieldCheck} />
        <KpiCard title="Casos verdes" value={summary.green_cases} helper="Riesgo bajo" tone="green" icon={CheckCircle2} />
        <KpiCard title="Casos amarillos" value={summary.yellow_cases} helper="Revision recomendada" tone="yellow" icon={AlertTriangle} />
        <KpiCard title="Casos rojos" value={summary.red_cases} helper="Prioridad humana" tone="red" icon={FileWarning} />
        <KpiCard title="Monto reclamado" value={formatMoney(summary.total_claim_amount)} helper="Total analizado" icon={CircleDollarSign} />
        <KpiCard title="Proveedores con alertas" value={summary.providers_with_alerts} helper="Con alertas activas" tone="slate" icon={Users} />
      </div>

      <div className="rounded-lg border border-blue-100 bg-blue-50 p-5 text-blue-950">
        <p className="font-bold">Resumen inteligente</p>
        <p className="mt-2 leading-7">{summary.smart_summary}</p>
      </div>

      <DashboardCharts
        summary={summary}
        cities={cities}
        providers={providers}
        selectedRisk={filters.risk}
        selectedCity={filters.city}
        selectedProvider={filters.provider}
        onRiskSelect={(risk) => toggleFilter('risk', risk)}
        onCitySelect={(city) => toggleFilter('city', city)}
        onProviderSelect={(provider) => toggleFilter('provider', provider)}
      />

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-bold text-ink">
              {activeFilterCount ? 'Siniestros filtrados por seleccion del dashboard' : 'Top 10 siniestros con mayor posible riesgo'}
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Los filtros de riesgo, ciudad y proveedor se combinan. Haz clic otra vez sobre el mismo elemento para quitarlo.
            </p>
            {activeFilterCount > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {filters.risk && <FilterChip label={`Riesgo: ${filters.risk}`} onClear={() => toggleFilter('risk', filters.risk)} />}
                {filters.city && <FilterChip label={`Ciudad: ${filters.city}`} onClear={() => toggleFilter('city', filters.city)} />}
                {filters.provider && <FilterChip label={`Proveedor: ${filters.provider}`} onClear={() => toggleFilter('provider', filters.provider)} />}
              </div>
            )}
          </div>
          {activeFilterCount > 0 && (
            <button onClick={() => setFilters({ risk: null, city: null, provider: null })} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold hover:bg-slate-50">
              Limpiar filtros
            </button>
          )}
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          {visibleClaims.map((claim) => (
            <button
              key={claim.claim_id}
              type="button"
              onClick={() => openClaim(claim.claim_id)}
              className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 p-4 text-left transition hover:border-electric hover:bg-blue-50/40"
            >
              <div>
                <p className="font-bold text-electric">{claim.claim_id}</p>
                <p className="text-sm text-slate-600">{claim.city} · {claim.provider_name}</p>
              </div>
              <div className="text-right">
                <p className="text-xl font-bold text-ink">{claim.risk_score}</p>
                <RiskBadge level={claim.risk_level} />
              </div>
            </button>
          ))}
          {visibleClaims.length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500 lg:col-span-2">
              No hay siniestros que coincidan con esa combinacion de filtros.
            </div>
          )}
        </div>
      </div>
      {selectedClaim && <HackiaDetail detail={selectedClaim} onClose={() => setSelectedClaim(null)} />}
    </div>
  )
}

function buildHackiaDashboardSummary(summaryData, rawClaims, mappedClaims) {
  const distribution = (summaryData?.risk_distribution || []).map((row) => ({
    risk_level: row.nivel_riesgo,
    count: row.total
  }))
  const byLevel = Object.fromEntries(distribution.map((row) => [row.risk_level, row.count]))
  const totalAmount = rawClaims.reduce((sum, claim) => sum + Number(claim.monto_reclamado || 0), 0)
  const totalAlerts = rawClaims.reduce((sum, claim) => sum + Number(claim.alertas || 0), 0)
  return {
    total_claims: summaryData?.counts?.siniestros || rawClaims.length,
    green_cases: byLevel.Bajo || 0,
    yellow_cases: byLevel.Medio || 0,
    red_cases: (byLevel.Alto || 0) + (byLevel.Critico || 0),
    total_claim_amount: totalAmount,
    providers_with_alerts: new Set(rawClaims.filter((claim) => Number(claim.alertas || 0) > 0).map((claim) => claim.proveedor_nombre || claim.id_proveedor).filter(Boolean)).size,
    risk_distribution: distribution,
    top_claims: mappedClaims.slice(0, 10),
    smart_summary: `Dataset activo con ${summaryData?.counts?.siniestros || rawClaims.length} siniestros importados y ${totalAlerts} alertas de revision. El tablero prioriza casos para analisis humano, sin acusar ni decidir automaticamente.`
  }
}

function mapHackiaClaimForDashboard(claim) {
  return {
    claim_id: claim.id_siniestro,
    city: claim.ciudad || 'Sin ciudad',
    provider_name: claim.proveedor_nombre || claim.id_proveedor || 'Sin proveedor',
    claim_amount: Number(claim.monto_reclamado || 0),
    risk_score: Number(claim.puntaje_riesgo || 0),
    risk_level: claim.nivel_riesgo || 'Bajo'
  }
}

function buildCityRanking(claimsData) {
  const grouped = new Map()
  claimsData.forEach((claim) => {
    const city = claim.ciudad || 'Sin ciudad'
    grouped.set(city, (grouped.get(city) || 0) + 1)
  })
  return [...grouped.entries()].map(([city, claims]) => ({ city, claims })).sort((a, b) => b.claims - a.claims)
}

function buildProviderRanking(claimsData) {
  const grouped = new Map()
  claimsData.forEach((claim) => {
    const provider = claim.proveedor_nombre || claim.id_proveedor || 'Sin proveedor'
    const current = grouped.get(provider) || { provider_name: provider, alerts: 0 }
    current.alerts += Number(claim.alertas || 0)
    grouped.set(provider, current)
  })
  return [...grouped.values()].sort((a, b) => b.alerts - a.alerts)
}

function FilterChip({ label, onClear }) {
  return (
    <button type="button" onClick={onClear} className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-bold text-blue-800 hover:bg-blue-100">
      {label} x
    </button>
  )
}

function EmptyState({ text }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-8 text-slate-600 shadow-soft">{text}</div>
}
