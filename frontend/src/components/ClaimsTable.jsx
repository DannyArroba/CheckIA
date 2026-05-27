import RiskBadge from './RiskBadge.jsx'

export default function ClaimsTable({ claims, onSelect }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-soft">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {['ID siniestro', 'Asegurado', 'Ramo', 'Cobertura', 'Ciudad', 'Proveedor', 'Monto', 'Score', 'Riesgo', 'Acción'].map((header) => (
                <th key={header} className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">{header}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {claims.map((claim) => (
              <tr key={claim.claim_id} className="cursor-pointer transition hover:bg-blue-50/60" onClick={() => onSelect(claim.claim_id)}>
                <td className="whitespace-nowrap px-4 py-3 text-sm font-bold text-electric">{claim.claim_id}</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm">
                  <div className="flex items-center gap-2">
                    <span>{claim.anonymous_customer}</span>
                    <ReviewBadge status={claim.review_status} label={claim.review_label} compact />
                  </div>
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm">{claim.line}</td>
                <td className="min-w-44 px-4 py-3 text-sm text-slate-600">{claim.coverage}</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm">{claim.city}</td>
                <td className="min-w-48 px-4 py-3 text-sm">{claim.provider_name}</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm font-semibold">${Number(claim.claim_amount).toLocaleString()}</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm font-bold">{claim.risk_score}</td>
                <td className="whitespace-nowrap px-4 py-3"><RiskBadge level={claim.risk_level} /></td>
                <td className="min-w-52 px-4 py-3 text-sm text-slate-600">{claim.recommended_action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
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
