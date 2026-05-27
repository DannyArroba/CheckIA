import { X } from 'lucide-react'
import RiskBadge from './RiskBadge.jsx'

export default function ClaimDetail({ claim, onClose }) {
  if (!claim) return null
  return (
    <div className="fixed inset-0 z-40 bg-ink/30 p-4 backdrop-blur-sm" onClick={onClose}>
      <aside className="ml-auto h-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-soft" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-electric">{claim.claim_id}</p>
            <h3 className="text-2xl font-bold text-ink">{claim.anonymous_customer}</h3>
          </div>
          <button className="rounded-lg border border-slate-200 p-2 hover:bg-slate-50" onClick={onClose} aria-label="Cerrar">
            <X size={19} />
          </button>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <Metric label="Score" value={claim.risk_score} />
          <Metric label="Nivel" value={<RiskBadge level={claim.risk_level} />} />
          <Metric label="Monto" value={`$${Number(claim.claim_amount).toLocaleString()}`} />
        </div>
        <Section title="Información general">
          <Info label="Ramo" value={claim.line} />
          <Info label="Cobertura" value={claim.coverage} />
          <Info label="Ciudad" value={claim.city} />
          <Info label="Proveedor" value={claim.provider_name} />
          <Info label="Fecha siniestro" value={claim.claim_date} />
          <Info label="Fecha reporte" value={claim.report_date} />
        </Section>
        <Section title="Información de póliza">
          <Info label="Póliza" value={claim.policy_id} />
          <Info label="Inicio" value={claim.policy_start_date} />
          <Info label="Fin" value={claim.policy_end_date} />
          <Info label="Suma asegurada" value={`$${Number(claim.insured_amount).toLocaleString()}`} />
        </Section>
        <Section title="Información documental">
          <Info label="Documentos" value={claim.document_names || 'Sin registros'} />
          <Info label="Estados" value={claim.document_statuses || 'Sin registros'} />
        </Section>
        <Section title="Narrativa del reclamo">
          <p className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-700">{claim.narrative}</p>
        </Section>
        <Section title="Reglas activadas">
          <div className="space-y-3">
            {claim.rules?.length ? claim.rules.map((rule) => (
              <div key={rule.codigo} className="rounded-lg border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-bold text-ink">{rule.nombre}</p>
                  <span className="text-sm font-bold text-electric">+{rule.puntos} pts</span>
                </div>
                <p className="mt-2 text-sm text-slate-600">{rule.explicacion}</p>
              </div>
            )) : <p className="text-sm text-slate-600">No se activaron señales relevantes.</p>}
          </div>
        </Section>
        <Section title="Explicación y recomendación">
          <p className="text-sm leading-6 text-slate-700">{claim.explainability?.explicacion}</p>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {claim.explainability?.factores?.map((factor) => <li key={factor}>{factor}</li>)}
          </ul>
          <p className="mt-4 rounded-lg bg-blue-50 p-4 text-sm font-semibold text-blue-900">{claim.explainability?.mensaje_etico}</p>
        </Section>
      </aside>
    </div>
  )
}

function Metric({ label, value }) {
  return <div className="rounded-lg bg-slate-50 p-4"><p className="text-xs font-bold uppercase text-slate-500">{label}</p><div className="mt-2 text-xl font-bold text-ink">{value}</div></div>
}

function Section({ title, children }) {
  return <section className="mt-6"><h4 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">{title}</h4>{children}</section>
}

function Info({ label, value }) {
  return <div className="grid grid-cols-[140px_1fr] gap-3 border-b border-slate-100 py-2 text-sm"><span className="font-semibold text-slate-500">{label}</span><span className="text-slate-800">{String(value ?? '-')}</span></div>
}
