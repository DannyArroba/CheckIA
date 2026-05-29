import { AlertCircle, Database, FileSearch, MessageSquareText, ShieldCheck, UploadCloud } from 'lucide-react'

const steps = [
  {
    icon: UploadCloud,
    title: '1. Cargar datos',
    text: 'Usa Datos para subir el Excel HackIAthon y los PDFs del expediente. Si vuelves a subir el mismo Excel, CheckIA actualiza por ID de siniestro y evita duplicados.'
  },
  {
    icon: ShieldCheck,
    title: '2. Revisar dashboard',
    text: 'Observa totales, semáforo, distribución de riesgo, ciudades y proveedores. El gráfico circular permite filtrar los casos por Bajo, Medio o Alto.'
  },
  {
    icon: FileSearch,
    title: '3. Analizar casos',
    text: 'En Casos puedes buscar por columnas, filtrar por ramo o riesgo, abrir el detalle y revisar reglas activadas, documentos, narrativa y recomendación.'
  },
  {
    icon: MessageSquareText,
    title: '4. Consultar al agente',
    text: 'Pregunta en lenguaje natural por proveedores, ciudades, documentos faltantes, patrones repetidos o casos prioritarios. El agente responde con datos cargados.'
  },
  {
    icon: Database,
    title: '5. Sincronizar MySQL',
    text: 'La base checkia en XAMPP/MySQL guarda siniestros, pólizas, asegurados, proveedores, documentos, textos extraídos, alertas y análisis.'
  },
  {
    icon: AlertCircle,
    title: '6. Registrar seguimiento',
    text: 'Marca casos como pendiente, bajo observación, documentación solicitada, revisado sin alerta o derivado a analista. Es seguimiento humano, no decisión automática.'
  }
]

const signals = [
  'Frecuencia inusual de reclamos por asegurado, póliza o vehículo.',
  'Montos reclamados altos frente a suma asegurada o promedio del ramo.',
  'Proveedores, beneficiarios o talleres recurrentes en casos observados.',
  'Eventos cerca del inicio o fin de vigencia de la póliza.',
  'Documentos incompletos, ilegibles o inconsistentes.',
  'Narrativas similares entre reclamos diferentes.',
  'Cambios recientes en datos del asegurado antes del siniestro.',
  'Reporte tardío entre la fecha de ocurrencia y la fecha de notificación.'
]

export default function About() {
  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-2xl font-bold text-ink">Cómo usar CheckIA</h3>
        <p className="mt-3 max-w-4xl leading-7 text-slate-700">
          CheckIA es un prototipo funcional para apoyar a analistas de siniestros. Cruza datos sintéticos de reclamos, pólizas, asegurados,
          proveedores, vehículos y documentos para detectar posibles señales de riesgo y priorizar revisión humana.
        </p>
        <p className="mt-3 max-w-4xl leading-7 text-slate-700">
          Usa un enfoque híbrido: ML + NLP + agente de IA para consultas en lenguaje natural. El backend calcula el riesgo y el agente redacta respuestas sobre datos ya procesados.
        </p>
        <p className="mt-4 rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-900">
          Esta alerta no constituye una acusación de fraude. El sistema no rechaza siniestros, no toma decisiones legales y no sustituye al analista humano.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {steps.map((step) => {
          const Icon = step.icon
          return (
            <article key={step.title} className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-blue-50 text-electric">
                  <Icon size={20} />
                </span>
                <h4 className="font-bold text-ink">{step.title}</h4>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600">{step.text}</p>
            </article>
          )
        })}
      </section>

      <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
          <h4 className="font-bold text-ink">Composición del score</h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            El puntaje final va de 0 a 100 y combina evidencia trazable. El objetivo es ordenar la revisión, no dictaminar fraude.
          </p>
          <div className="mt-4 space-y-3 text-sm text-slate-700">
            <Row label="Reglas explicables" value="70%" />
            <Row label="ML/anomalías" value="20%" />
            <Row label="NLP/similitud textual" value="10%" />
          </div>
          <div className="mt-5 grid gap-2 text-sm">
            <Badge tone="green" label="0 - 40: Bajo" text="Continuar flujo normal." />
            <Badge tone="yellow" label="41 - 75: Medio" text="Revisión documental recomendada." />
            <Badge tone="red" label="76 - 100: Alto" text="Caso prioritario para revisión especializada." />
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
          <h4 className="font-bold text-ink">Señales que analiza</h4>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {signals.map((signal) => (
              <div key={signal} className="rounded-lg bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700">
                {signal}
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function Badge({ tone, label, text }) {
  const tones = {
    green: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    yellow: 'border-amber-200 bg-amber-50 text-amber-800',
    red: 'border-red-200 bg-red-50 text-red-800'
  }
  return (
    <div className={`rounded-lg border px-4 py-3 ${tones[tone]}`}>
      <strong>{label}</strong>
      <span className="ml-2">{text}</span>
    </div>
  )
}
