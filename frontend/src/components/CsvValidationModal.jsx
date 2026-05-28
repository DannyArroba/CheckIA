import { AlertTriangle, X } from 'lucide-react'

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

export default function CsvValidationModal({ modal, onClose }) {
  if (!modal) return null
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-soft">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-amber-100 text-amber-700">
              <AlertTriangle size={22} />
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
