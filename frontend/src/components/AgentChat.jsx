import { useState } from 'react'
import { Bot, Send, Sparkles, UserRound } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'

const quickQuestions = [
  '¿Cuáles son los 10 siniestros con mayor riesgo?',
  '¿Qué proveedores concentran más alertas?',
  '¿Qué ciudades tienen más casos rojos?',
  '¿Qué documentos faltan en los casos críticos?',
  '¿Qué casos tienen montos atípicos?',
  '¿Qué siniestros ocurrieron cerca del inicio de la póliza?',
  '¿Qué patrones se repiten?',
  'Genera un resumen ejecutivo.',
  'Recomienda qué casos revisar primero.'
]

export default function AgentChat() {
  const [messages, setMessages] = useState([
    { role: 'agent', text: 'Hola, soy el agente CheckIA. Respondo con datos sintéticos del sistema y lenguaje de revisión humana.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function send(text = input) {
    const trimmed = text.trim()
    if (!trimmed) return
    setMessages((current) => [...current, { role: 'user', text: trimmed }])
    setInput('')
    setLoading(true)
    try {
      const response = await claimsApi.chat(trimmed)
      setMessages((current) => [...current, { role: 'agent', text: `${response.answer}\n\n${response.disclaimer}` }])
    } catch {
      setMessages((current) => [...current, { role: 'agent', text: 'No pude conectar con el backend. Verifica que FastAPI este ejecutandose.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-[calc(100vh-140px)] gap-5 lg:grid-cols-[280px_1fr]">
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-soft">
        <div className="mb-4 flex items-center gap-2 font-bold text-ink"><Sparkles size={18} /> Preguntas rápidas</div>
        <div className="space-y-2">
          {quickQuestions.map((question) => (
            <button key={question} onClick={() => send(question)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-sm hover:border-electric hover:bg-blue-50">
              {question}
            </button>
          ))}
        </div>
      </div>
      <div className="flex rounded-lg border border-slate-200 bg-white shadow-soft">
        <div className="flex w-full flex-col">
          <div className="flex-1 space-y-4 overflow-y-auto p-5">
            {messages.map((message, index) => (
              <div key={index} className={`flex items-start gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {message.role === 'agent' && <Avatar icon={Bot} tone="agent" />}
                <div className={`max-w-[78%] whitespace-pre-line rounded-lg px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'bg-electric text-white' : 'bg-slate-100 text-slate-800'}`}>
                  {message.text}
                </div>
                {message.role === 'user' && <Avatar icon={UserRound} tone="user" />}
              </div>
            ))}
            {loading && <div className="ml-12 text-sm font-semibold text-slate-500">analizando...</div>}
          </div>
          <div className="border-t border-slate-200 p-4">
            <div className="flex gap-3">
              <input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && send()} className="min-h-11 flex-1 rounded-lg border border-slate-200 px-4 outline-none focus:border-electric" placeholder="Pregunta sobre riesgos, proveedores, documentos o patrones" />
              <button onClick={() => send()} className="grid h-11 w-11 place-items-center rounded-lg bg-electric text-white hover:bg-blue-700" aria-label="Enviar">
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Avatar({ icon: Icon, tone }) {
  return <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${tone === 'agent' ? 'bg-ink text-white' : 'bg-slate-200 text-slate-700'}`}><Icon size={18} /></div>
}
