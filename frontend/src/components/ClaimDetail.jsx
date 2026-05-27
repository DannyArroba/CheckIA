import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import RiskBadge from './RiskBadge.jsx'

const reviewOptions = [
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'bajo_observacion', label: 'Bajo observación' },
  { value: 'documentacion_solicitada', label: 'Documentación solicitada' },
  { value: 'derivado_analista', label: 'Derivado a analista' },
  { value: 'revisado_sin_alerta', label: 'Revisado sin alerta adicional' }
]

export default function ClaimDetail({ claim, onClose }) {
  const [reviewStatus, setReviewStatus] = useState('pendiente')
  const [reviewNote, setReviewNote] = useState('')
  const [reviews, setReviews] = useState([])

  useEffect(() => {
    if (!claim) return
    setReviewStatus(claim.review_status || 'pendiente')
    claimsApi.reviewActions(claim.claim_id).then(setReviews).catch(() => setReviews([]))
  }, [claim])

  if (!claim) return null

  const latest = reviews[0]

  async function saveReview() {
    await claimsApi.createReviewAction(claim.claim_id, reviewStatus, reviewNote)
    setReviewNote('')
    const rows = await claimsApi.reviewActions(claim.claim_id)
    setReviews(rows)
  }

  return (
    <div className="fixed inset-0 z-40 bg-ink/30 p-4 backdrop-blur-sm" onClick={onClose}>
      <aside className="ml-auto h-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-soft" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-electric">{claim.claim_id}</p>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <h3 className="text-2xl font-bold text-ink">{claim.anonymous_customer}</h3>
              <ReviewBadge status={latest?.status || claim.review_status} label={latest ? labelForStatus(latest.status) : claim.review_label} />
            </div>
            {latest?.note && <p className="mt-2 max-w-xl text-sm text-slate-500">{latest.note}</p>}
          </div>
          <button className="rounded-lg border border-slate-200 p-2 hover:bg-slate-50" onClick={onClose} aria-label="Cerrar">
            <X size={19} />
          </button>
        </div>

        <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-48 flex-1">
              <label className="text-xs font-bold uppercase text-slate-500">Seguimiento humano</label>
              <select value={reviewStatus} onChange={(event) => setReviewStatus(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-200 bg-white px-3">
                {reviewOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </div>
            <div className="min-w-56 flex-[1.4]">
              <label className="text-xs font-bold uppercase text-slate-500">Nota interna</label>
              <input value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-electric" placeholder="Ej. solicitar factura legible" />
            </div>
            <button onClick={saveReview} className="min-h-11 rounded-lg bg-ink px-4 font-semibold text-white hover:bg-slate-800">Guardar</button>
          </div>
          <p className="mt-3 text-xs text-slate-500">Este estado no aprueba ni niega un siniestro. Solo registra el avance de revisión del analista.</p>
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

function ReviewBadge({ status, label }) {
  if (!status) return <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-500">Sin seguimiento</span>
  const tones = {
    pendiente: 'bg-slate-100 text-slate-700 border-slate-200',
    bajo_observacion: 'bg-zinc-200 text-zinc-900 border-zinc-300',
    documentacion_solicitada: 'bg-blue-100 text-blue-800 border-blue-200',
    derivado_analista: 'bg-violet-100 text-violet-800 border-violet-200',
    revisado_sin_alerta: 'bg-emerald-100 text-emerald-800 border-emerald-200'
  }
  return <span className={`rounded-full border px-3 py-1 text-xs font-bold ${tones[status] || tones.pendiente}`}>{label}</span>
}

function labelForStatus(status) {
  return reviewOptions.find((option) => option.value === status)?.label || status
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
