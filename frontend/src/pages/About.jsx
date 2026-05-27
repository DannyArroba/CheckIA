export default function About() {
  return (
    <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-2xl font-bold text-ink">CheckIA</h3>
        <p className="mt-4 leading-7 text-slate-700">
          CheckIA es un prototipo para hackathon que ayuda a analistas de seguros a priorizar la revisión de siniestros.
          Combina reglas de negocio, detección de anomalías y similitud textual para producir un score explicable de 0 a 100.
        </p>
        <p className="mt-4 rounded-lg bg-amber-50 p-4 text-sm font-semibold text-amber-900">
          La aplicación no acusa fraude, no rechaza siniestros y no toma decisiones legales. Solo genera alertas de revisión para análisis humano.
        </p>
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
        <h4 className="font-bold text-ink">Composición del score</h4>
        <div className="mt-4 space-y-3 text-sm text-slate-700">
          <Row label="Reglas explicables" value="70%" />
          <Row label="Modelo IA/anomalías" value="20%" />
          <Row label="NLP/similitud textual" value="10%" />
        </div>
      </section>
    </div>
  )
}

function Row({ label, value }) {
  return <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3"><span>{label}</span><strong>{value}</strong></div>
}
