import { useEffect, useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import ClaimDetail from '../components/ClaimDetail.jsx'
import ClaimsTable from '../components/ClaimsTable.jsx'
import UploadDataset from '../components/UploadDataset.jsx'

export default function Cases() {
  const [claims, setClaims] = useState([])
  const [selected, setSelected] = useState(null)
  const [query, setQuery] = useState('')
  const [risk, setRisk] = useState('Todos')
  const [line, setLine] = useState('Todos')

  useEffect(() => {
    loadClaims()
  }, [])

  async function loadClaims() {
    claimsApi.claims().then(setClaims).catch(() => setClaims([]))
  }

  const lines = useMemo(() => ['Todos', ...new Set(claims.map((claim) => claim.line))], [claims])
  const filtered = claims.filter((claim) => {
    const matchesQuery = [claim.claim_id, claim.anonymous_customer, claim.city, claim.provider_name, claim.coverage].join(' ').toLowerCase().includes(query.toLowerCase())
    const matchesRisk = risk === 'Todos' || claim.risk_level === risk
    const matchesLine = line === 'Todos' || claim.line === line
    return matchesQuery && matchesRisk && matchesLine
  })

  async function openClaim(id) {
    const detail = await claimsApi.claim(id)
    setSelected(detail)
  }

  return (
    <div className="space-y-5">
      <UploadDataset onUploaded={loadClaims} />
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-soft">
        <div className="grid gap-3 lg:grid-cols-[1fr_180px_180px]">
          <label className="flex min-h-11 items-center gap-2 rounded-lg border border-slate-200 px-3">
            <Search size={18} className="text-slate-400" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="w-full outline-none" placeholder="Buscar por ID, ciudad, proveedor o cobertura" />
          </label>
          <select value={risk} onChange={(event) => setRisk(event.target.value)} className="min-h-11 rounded-lg border border-slate-200 px-3">
            {['Todos', 'Bajo', 'Medio', 'Alto'].map((value) => <option key={value}>{value}</option>)}
          </select>
          <select value={line} onChange={(event) => setLine(event.target.value)} className="min-h-11 rounded-lg border border-slate-200 px-3">
            {lines.map((value) => <option key={value}>{value}</option>)}
          </select>
        </div>
      </div>
      <ClaimsTable claims={filtered} onSelect={openClaim} />
      <ClaimDetail claim={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
