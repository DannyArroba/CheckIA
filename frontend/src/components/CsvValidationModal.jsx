import { AlertTriangle, CheckCircle2, X } from 'lucide-react'

export function buildUploadErrorModal(error) {
  const detail = error?.detail
  if (detail?.missing_columns || detail?.validation_errors) {
    return {
      title: 'Este CSV no corresponde a siniestros de CheckIA',
      body: detail.reason || 'El archivo no tiene la estructura requerida para la aplicación.',
      missingColumns: detail.missing_columns || [],
      validationErrors: detail.validation_errors || [],
      detectedColumns: detail.detected_columns || [],
      requiredColumns: detail.required_columns || []
    }
  }
  return {
    title: 'No se pudo cargar el CSV',
    body: 'El archivo no tiene nada que ver con la estructura esperada o no pudo ser leído correctamente.',
    missingColumns: [],
    validationErrors: [],
    detectedColumns: [],
    requiredColumns: []
  }
}

export function buildUploadSuccessModal(response) {
  const result = response?.result || {}
  return {
    type: 'success',
    title: 'Carga incremental completada',
    body: result.message || response.message || 'El archivo fue procesado correctamente.',
    stats: [
      { label: 'Insertados', value: result.inserted ?? 0 },
      { label: 'Duplicados omitidos', value: result.skipped_duplicates ?? 0 },
      { label: 'Total activo', value: result.total_claims ?? '-' }
    ]
  }
}

export default function CsvValidationModal({ modal, onClose }) {
  if (!modal) return null
  const isSuccess = modal.type === 'success'
  const Icon = isSuccess ? CheckCircle2 : AlertTriangle
  const iconTone = isSuccess ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-soft">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className={`grid h-11 w-11 shrink-0 place-items-center rounded-lg ${iconTone}`}>
              <Icon size={22} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-ink">{modal.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{modal.body}</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg border border-slate-200 p-2 hover:bg-slate-50" aria-label="Cerrar">
            <X size={18} />
          </button>
        </div>

        {!!modal.stats?.length && <Stats items={modal.stats} />}
        {!!modal.missingColumns?.length && <Block title="Columnas faltantes" items={modal.missingColumns} tone="red" />}
        {!!modal.validationErrors?.length && <Block title="Valores inválidos detectados" items={modal.validationErrors} tone="amber" />}
        {!!modal.detectedColumns?.length && <Block title="Columnas detectadas" items={modal.detectedColumns} />}
        {!!modal.requiredColumns?.length && <Block title="Columnas requeridas" items={modal.requiredColumns} />}

        <div className="mt-6 flex justify-end">
          <button onClick={onClose} className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
            Entendido
          </button>
        </div>
      </div>
    </div>
  )
}

function Stats({ items }) {
  return (
    <div className="mt-5 grid gap-3 sm:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs font-bold uppercase text-slate-500">{item.label}</p>
          <p className="mt-1 text-2xl font-bold text-ink">{item.value}</p>
        </div>
      ))}
    </div>
  )
}

function Block({ title, items, tone = 'slate' }) {
  const tones = {
    red: 'bg-red-50 text-red-800',
    amber: 'bg-amber-50 text-amber-900',
    slate: 'bg-slate-50 text-slate-700'
  }
  return (
    <div className={`mt-4 rounded-lg p-4 ${tones[tone]}`}>
      <h4 className="text-sm font-bold text-ink">{title}</h4>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.map((item) => (
          <span key={item} className="rounded-full bg-white px-2 py-1 text-xs font-semibold">
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}
