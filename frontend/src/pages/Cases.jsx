import { useEffect, useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import ClaimsTable from '../components/ClaimsTable.jsx'
import { HackiaDetail } from './Hackia.jsx'

export default function Cases() {
  const [rawClaims, setRawClaims] = useState([])
  const [selected, setSelected] = useState(null)
  const [query, setQuery] = useState('')
  const [risk, setRisk] = useState('Todos')
  const [line, setLine] = useState('Todos')

  useEffect(() => {
    loadClaims()
  }, [])

  async function loadClaims() {
    claimsApi.hackiaClaims().then(setRawClaims).catch(() => setRawClaims([]))
  }

  const claims = useMemo(() => rawClaims.map(mapHackiaClaimForTable), [rawClaims])
  const lines = useMemo(() => ['Todos', ...new Set(claims.map((claim) => claim.line).filter(Boolean))], [claims])
  const risks = useMemo(() => ['Todos', ...new Set(claims.map((claim) => claim.risk_level).filter(Boolean))], [claims])
  const filtered = claims.filter((claim) => {
    const matchesQuery = [claim.claim_id, claim.anonymous_customer, claim.city, claim.provider_name, claim.coverage].join(' ').toLowerCase().includes(query.toLowerCase())
    const matchesRisk = risk === 'Todos' || claim.risk_level === risk
    const matchesLine = line === 'Todos' || claim.line === line
    return matchesQuery && matchesRisk && matchesLine
  })

  async function openClaim(id) {
    const detail = await claimsApi.hackiaClaim(id)
    setSelected(detail)
  }

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-950">
        Esta bandeja usa el dataset HackIAthon importado desde Excel y PDFs. Los casos demo CLM ya no se muestran aqui.
      </div>
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-soft">
        <div className="grid gap-3 lg:grid-cols-[1fr_180px_180px]">
          <label className="flex min-h-11 items-center gap-2 rounded-lg border border-slate-200 px-3">
            <Search size={18} className="text-slate-400" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="w-full outline-none" placeholder="Buscar por SIN, asegurado, ciudad, proveedor o cobertura" />
          </label>
          <select value={risk} onChange={(event) => setRisk(event.target.value)} className="min-h-11 rounded-lg border border-slate-200 px-3">
            {risks.map((value) => <option key={value}>{value}</option>)}
          </select>
          <select value={line} onChange={(event) => setLine(event.target.value)} className="min-h-11 rounded-lg border border-slate-200 px-3">
            {lines.map((value) => <option key={value}>{value}</option>)}
          </select>
        </div>
      </div>
      {claims.length ? (
        <ClaimsTable claims={filtered} onSelect={openClaim} />
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-slate-600 shadow-soft">
          Aun no hay siniestros HackIAthon cargados. Sube tu Excel desde Datos o arrastralo sobre la pantalla.
        </div>
      )}
      {selected && <HackiaDetail detail={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function mapHackiaClaimForTable(claim) {
  return {
    claim_id: claim.id_siniestro,
    anonymous_customer: claim.asegurado_nombre || claim.id_asegurado || 'Asegurado anonimo',
    line: claim.ramo || 'Sin ramo',
    coverage: claim.cobertura || 'Sin cobertura',
    city: claim.ciudad || 'Sin ciudad',
    provider_name: claim.proveedor_nombre || claim.id_proveedor || 'Sin proveedor',
    claim_amount: Number(claim.monto_reclamado || 0),
    risk_score: Number(claim.puntaje_riesgo || 0),
    risk_level: claim.nivel_riesgo || 'Bajo',
    recommended_action: claim.nivel_riesgo === 'Critico' || claim.nivel_riesgo === 'Alto'
      ? 'Revision prioritaria por analista'
      : claim.nivel_riesgo === 'Medio'
        ? 'Revision documental recomendada'
        : 'Continuar flujo normal con monitoreo'
  }
}
