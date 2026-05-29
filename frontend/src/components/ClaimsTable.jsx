import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Search, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import RiskBadge from './RiskBadge.jsx'

const columns = [
  { key: 'claim_id', label: 'ID siniestro', className: 'whitespace-nowrap', render: (claim) => <span className="font-bold text-electric">{claim.claim_id}</span> },
  { key: 'policy_id', label: 'ID poliza', className: 'whitespace-nowrap' },
  { key: 'insured_id', label: 'ID asegurado', className: 'whitespace-nowrap' },
  { key: 'anonymous_customer', label: 'Asegurado', className: 'whitespace-nowrap', render: (claim) => (
    <div className="flex items-center gap-2">
      <span>{claim.anonymous_customer}</span>
      <ReviewBadge status={claim.review_status} label={claim.review_label} compact />
    </div>
  ) },
  { key: 'line', label: 'Ramo', className: 'whitespace-nowrap' },
  { key: 'plate', label: 'Placa vehiculo', className: 'whitespace-nowrap' },
  { key: 'coverage', label: 'Cobertura', className: 'min-w-44 text-slate-600' },
  { key: 'claim_date', label: 'Fecha ocurrencia', className: 'whitespace-nowrap' },
  { key: 'report_date', label: 'Fecha reporte', className: 'whitespace-nowrap' },
  { key: 'days_report', label: 'Dias ocurr-reporte', className: 'whitespace-nowrap' },
  { key: 'city', label: 'Ciudad', className: 'whitespace-nowrap' },
  { key: 'branch', label: 'Sucursal', className: 'whitespace-nowrap' },
  { key: 'provider_id', label: 'ID proveedor', className: 'whitespace-nowrap' },
  { key: 'provider_name', label: 'Proveedor', className: 'min-w-48' },
  { key: 'claim_amount', label: 'Monto', className: 'whitespace-nowrap font-semibold', value: (claim) => String(claim.claim_amount), render: (claim) => `$${Number(claim.claim_amount).toLocaleString()}` },
  { key: 'estimated_amount', label: 'Monto estimado', className: 'whitespace-nowrap', value: (claim) => String(claim.estimated_amount), render: (claim) => `$${Number(claim.estimated_amount || 0).toLocaleString()}` },
  { key: 'paid_amount', label: 'Monto pagado', className: 'whitespace-nowrap', value: (claim) => String(claim.paid_amount), render: (claim) => `$${Number(claim.paid_amount || 0).toLocaleString()}` },
  { key: 'status', label: 'Estado', className: 'whitespace-nowrap' },
  { key: 'docs_complete', label: 'Docs completos', className: 'whitespace-nowrap' },
  { key: 'provider_restricted', label: 'Prov. lista restrictiva', className: 'whitespace-nowrap' },
  { key: 'days_from_start', label: 'Dias desde inicio', className: 'whitespace-nowrap' },
  { key: 'days_to_end', label: 'Dias hasta fin', className: 'whitespace-nowrap' },
  { key: 'previous_claims', label: 'Reclamos previos', className: 'whitespace-nowrap' },
  { key: 'insured_sum', label: 'Suma asegurada', className: 'whitespace-nowrap', value: (claim) => String(claim.insured_sum), render: (claim) => `$${Number(claim.insured_sum || 0).toLocaleString()}` },
  { key: 'narrative_similarity', label: 'Similitud narrativa', className: 'whitespace-nowrap' },
  { key: 'police_report_number', label: 'Numero parte policial', className: 'whitespace-nowrap' },
  { key: 'risk_score', label: 'Score', className: 'whitespace-nowrap font-bold', value: (claim) => String(claim.risk_score) },
  { key: 'risk_level', label: 'Riesgo', className: 'whitespace-nowrap', render: (claim) => <RiskBadge level={claim.risk_level} /> },
  { key: 'event_description', label: 'Descripcion del evento', className: 'min-w-80 text-slate-600' },
  { key: 'recommended_action', label: 'Acción', className: 'min-w-52 text-slate-600' }
]

export default function ClaimsTable({ claims, onSelect }) {
  const [openFilter, setOpenFilter] = useState(null)
  const [filters, setFilters] = useState({})
  const [sort, setSort] = useState({ key: 'risk_score', direction: 'desc' })
  const scrollRef = useRef(null)
  const [scrollState, setScrollState] = useState({ left: false, right: false })

  const filteredClaims = useMemo(() => {
    const rows = claims.filter((claim) => {
      return columns.every((column) => {
        const filter = (filters[column.key] || '').trim().toLowerCase()
        if (!filter) return true
        const raw = column.value ? column.value(claim) : claim[column.key]
        return String(raw ?? '').toLowerCase().includes(filter)
      })
    })
    return [...rows].sort((a, b) => compareValues(sortValue(a, sort.key), sortValue(b, sort.key), sort.direction))
  }, [claims, filters, sort])

  function toggleSort(key) {
    setSort((current) => {
      if (current.key !== key) return { key, direction: 'asc' }
      return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
    })
  }

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  function clearFilter(key) {
    setFilters((current) => {
      const next = { ...current }
      delete next[key]
      return next
    })
  }

  function updateScrollState() {
    const node = scrollRef.current
    if (!node) return
    setScrollState({
      left: node.scrollLeft > 4,
      right: node.scrollLeft + node.clientWidth < node.scrollWidth - 4
    })
  }

  function scrollTable(direction) {
    const node = scrollRef.current
    if (!node) return
    node.scrollBy({ left: direction * Math.max(260, node.clientWidth * 0.65), behavior: 'smooth' })
  }

  useEffect(() => {
    updateScrollState()
    const node = scrollRef.current
    if (!node) return undefined
    node.addEventListener('scroll', updateScrollState)
    window.addEventListener('resize', updateScrollState)
    return () => {
      node.removeEventListener('scroll', updateScrollState)
      window.removeEventListener('resize', updateScrollState)
    }
  }, [filteredClaims.length])

  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-soft">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        Mostrando <strong>{filteredClaims.length}</strong> de <strong>{claims.length}</strong> siniestros
      </div>
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 right-0 z-30 flex items-center justify-between px-2">
          <button
            type="button"
            onClick={() => scrollTable(-1)}
            disabled={!scrollState.left}
            className="pointer-events-auto grid h-9 w-9 place-items-center rounded-full border border-slate-200 bg-white/95 text-slate-700 shadow-soft backdrop-blur hover:border-electric hover:text-electric disabled:cursor-not-allowed disabled:opacity-30"
            title="Mover tabla a la izquierda"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            type="button"
            onClick={() => scrollTable(1)}
            disabled={!scrollState.right}
            className="pointer-events-auto grid h-9 w-9 place-items-center rounded-full border border-slate-200 bg-white/95 text-slate-700 shadow-soft backdrop-blur hover:border-electric hover:text-electric disabled:cursor-not-allowed disabled:opacity-30"
            title="Mover tabla a la derecha"
          >
            <ChevronRight size={18} />
          </button>
        </div>
        <div ref={scrollRef} className="max-h-[70vh] overflow-auto scroll-smooth">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className="sticky top-0 z-20 bg-slate-50 px-4 py-3 text-left align-top text-xs font-bold uppercase tracking-wide text-slate-500 shadow-[0_1px_0_0_rgba(226,232,240,1)]"
                >
                  <div className="flex min-w-28 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => toggleSort(column.key)}
                      className="inline-flex items-center gap-1 text-left hover:text-electric"
                      title={`Ordenar por ${column.label}`}
                    >
                      <span>{column.label}</span>
                      {sort.key === column.key
                        ? sort.direction === 'asc'
                          ? <ArrowUp size={13} />
                          : <ArrowDown size={13} />
                        : <ArrowUpDown size={13} className="text-slate-300" />}
                    </button>
                    <button
                      type="button"
                      onClick={() => setOpenFilter(openFilter === column.key ? null : column.key)}
                      className={`grid h-6 w-6 place-items-center rounded border ${filters[column.key] ? 'border-electric bg-blue-50 text-electric' : 'border-slate-200 bg-white text-slate-400 hover:text-electric'}`}
                      title={`Buscar en ${column.label}`}
                    >
                      <Search size={13} />
                    </button>
                  </div>
                  {openFilter === column.key && (
                    <div className="mt-2 flex min-h-9 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2">
                      <input
                        autoFocus
                        value={filters[column.key] || ''}
                        onChange={(event) => updateFilter(column.key, event.target.value)}
                        onClick={(event) => event.stopPropagation()}
                        className="w-36 bg-transparent text-xs font-medium normal-case tracking-normal text-slate-700 outline-none"
                        placeholder={`Buscar ${column.label.toLowerCase()}`}
                      />
                      {!!filters[column.key] && (
                        <button type="button" onClick={() => clearFilter(column.key)} className="text-slate-400 hover:text-red-600" title="Limpiar">
                          <X size={13} />
                        </button>
                      )}
                    </div>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredClaims.map((claim) => (
              <tr key={claim.claim_id} className="cursor-pointer transition hover:bg-blue-50/60" onClick={() => onSelect(claim.claim_id)}>
                {columns.map((column) => (
                  <td key={column.key} className={`px-4 py-3 text-sm ${column.className || ''}`}>
                    {column.render ? column.render(claim) : claim[column.key]}
                  </td>
                ))}
              </tr>
            ))}
            {filteredClaims.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-sm text-slate-500">
                  No hay siniestros que coincidan con los filtros por columna.
                </td>
              </tr>
            )}
          </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function sortValue(claim, key) {
  const value = claim[key]
  if (value === null || value === undefined || value === '-') return ''
  if (typeof value === 'number') return value
  if (['claim_amount', 'estimated_amount', 'paid_amount', 'days_report', 'days_from_start', 'days_to_end', 'previous_claims', 'insured_sum', 'narrative_similarity', 'risk_score'].includes(key)) {
    const number = Number(String(value).replace(/[^0-9.-]/g, ''))
    return Number.isNaN(number) ? 0 : number
  }
  return String(value).toLowerCase()
}

function compareValues(a, b, direction) {
  if (typeof a === 'number' && typeof b === 'number') {
    return direction === 'asc' ? a - b : b - a
  }
  const result = String(a).localeCompare(String(b), 'es', { numeric: true, sensitivity: 'base' })
  return direction === 'asc' ? result : -result
}

function ReviewBadge({ status, label, compact = false }) {
  if (!status) return null
  const tones = {
    pendiente: 'bg-slate-100 text-slate-700 border-slate-200',
    bajo_observacion: 'bg-zinc-200 text-zinc-900 border-zinc-300',
    documentacion_solicitada: 'bg-blue-100 text-blue-800 border-blue-200',
    derivado_analista: 'bg-violet-100 text-violet-800 border-violet-200',
    revisado_sin_alerta: 'bg-emerald-100 text-emerald-800 border-emerald-200'
  }
  return (
    <span className={`inline-flex rounded-full border font-bold ${compact ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs'} ${tones[status] || tones.pendiente}`}>
      {label}
    </span>
  )
}
