import { useEffect, useState } from 'react'
import { Bot, Cpu, LoaderCircle, MessageSquarePlus, SearchCheck, Send, ShieldCheck, Sparkles, Trash2, UserRound } from 'lucide-react'
import { claimsApi } from '../api/claimsApi.js'
import ClaimDetail from './ClaimDetail.jsx'

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

const welcome = {
  role: 'agente',
  text: 'Hola, soy el agente CheckIA. Puedo ayudarte a revisar posibles señales de riesgo en siniestros, siempre como apoyo para análisis humano.',
  provider: 'sistema',
  relatedClaims: []
}

export default function AgentChat() {
  const [messages, setMessages] = useState([welcome])
  const [conversations, setConversations] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null)
  const [selectedClaim, setSelectedClaim] = useState(null)

  useEffect(() => {
    claimsApi.agentStatus().then(setStatus).catch(() => setStatus({ available: false, model: 'gemma2:2b' }))
    loadConversations()
  }, [])

  async function loadConversations() {
    const list = await claimsApi.agentConversations().catch(() => [])
    setConversations(list)
    if (!conversationId && list[0]) openConversation(list[0].conversation_id)
  }

  async function openConversation(id) {
    setConversationId(id)
    const rows = await claimsApi.agentHistory(id).catch(() => [])
    if (!rows.length) {
      setMessages([welcome])
      return
    }
    setMessages(rows.map((row) => ({
      role: row.role,
      text: row.message_text,
      provider: row.provider,
      relatedClaims: extractClaimIds(row.message_text)
    })))
  }

  async function newChat() {
    const created = await claimsApi.createConversation()
    setConversationId(created.conversation_id)
    setMessages([welcome])
    await loadConversations()
  }

  async function deleteConversation(id) {
    await claimsApi.deleteConversation(id)
    if (id === conversationId) {
      setConversationId(null)
      setMessages([welcome])
    }
    await loadConversations()
  }

  async function send(text = input) {
    const trimmed = text.trim()
    if (!trimmed || loading) return
    const activeConversation = conversationId || (await claimsApi.createConversation()).conversation_id
    setConversationId(activeConversation)
    setMessages((current) => [...current, { role: 'usuario', text: trimmed, relatedClaims: [] }])
    setInput('')
    setLoading(true)
    try {
      const response = await claimsApi.chat(trimmed, activeConversation)
      setMessages((current) => [
        ...current,
        {
          role: 'agente',
          text: response.answer,
          provider: response.provider || 'reglas',
          relatedClaims: response.related_claims || [],
          suggestions: response.suggestions || []
        }
      ])
      await loadConversations()
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: 'agente',
          text: 'No pude conectar con el backend. Verifica que FastAPI esté ejecutándose.',
          provider: 'error',
          relatedClaims: []
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  async function openClaim(claimId) {
    const detail = await claimsApi.claim(claimId)
    setSelectedClaim(detail)
  }

  return (
    <div className="grid min-h-[calc(100vh-140px)] gap-5 xl:grid-cols-[280px_1fr_280px]">
      <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-soft">
        <button onClick={newChat} className="mb-4 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg bg-electric px-3 text-sm font-semibold text-white hover:bg-blue-700">
          <MessageSquarePlus size={17} /> Nuevo chat
        </button>
        <div className="space-y-2">
          {conversations.length === 0 && <p className="text-sm text-slate-500">Aún no hay conversaciones guardadas.</p>}
          {conversations.map((item) => (
            <div key={item.conversation_id} className={`group flex items-center gap-2 rounded-lg border p-2 ${item.conversation_id === conversationId ? 'border-electric bg-blue-50' : 'border-slate-200'}`}>
              <button onClick={() => openConversation(item.conversation_id)} className="min-w-0 flex-1 text-left">
                <p className="truncate text-sm font-bold text-ink">{item.title}</p>
                <p className="text-xs text-slate-500">{item.message_count} mensajes</p>
              </button>
              <button onClick={() => deleteConversation(item.conversation_id)} className="grid h-8 w-8 place-items-center rounded text-slate-400 hover:bg-white hover:text-red-600" title="Eliminar chat">
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="flex rounded-lg border border-slate-200 bg-white shadow-soft">
        <div className="flex w-full flex-col">
          <div className="border-b border-slate-200 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-ink">Chat de análisis</h3>
                <p className="text-xs text-slate-500">Las respuestas son apoyo para revisión humana, no decisiones finales.</p>
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                <Cpu size={15} /> {status?.available ? `Ollama conectado: ${status.model}` : 'Ollama sin conexión activa'}
              </div>
            </div>
            {loading && <TopLoadingBar />}
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto p-5">
            {messages.map((message, index) => (
              <div key={index} className={`flex items-start gap-3 ${message.role === 'usuario' ? 'justify-end' : 'justify-start'}`}>
                {message.role !== 'usuario' && <Avatar icon={Bot} tone="agent" />}
                <div className={`max-w-[82%] rounded-lg px-4 py-3 text-sm leading-6 ${message.role === 'usuario' ? 'bg-electric text-white' : 'bg-slate-100 text-slate-800'}`}>
                  <MessageText text={message.text} onClaimClick={openClaim} />
                  {message.role !== 'usuario' && (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-white px-2 py-1 text-[11px] font-bold uppercase text-slate-500">{message.provider}</span>
                      {(message.relatedClaims || []).map((claimId) => (
                        <button key={claimId} onClick={() => openClaim(claimId)} className="rounded-full bg-blue-100 px-2 py-1 text-xs font-bold text-blue-800 hover:bg-blue-200">
                          {claimId}
                        </button>
                      ))}
                      {(message.suggestions || []).map((suggestion) => (
                        <button key={suggestion} onClick={() => send(suggestion)} className="rounded-full border border-blue-200 bg-white px-2 py-1 text-xs font-bold text-blue-700 hover:bg-blue-50">
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {message.role === 'usuario' && <Avatar icon={UserRound} tone="user" />}
              </div>
            ))}
            {loading && <LoadingBubble provider={status?.available ? 'ollama' : 'reglas'} />}
          </div>

          <div className="border-t border-slate-200 p-4">
            <div className="flex gap-3">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && send()}
                className="min-h-11 flex-1 rounded-lg border border-slate-200 px-4 outline-none focus:border-electric"
                placeholder={loading ? 'CheckIA está preparando la respuesta...' : 'Pregunta sobre riesgos, proveedores, documentos o patrones'}
                disabled={loading}
              />
              <button onClick={() => send()} className="grid h-11 w-11 place-items-center rounded-lg bg-electric text-white hover:bg-blue-700 disabled:opacity-60" disabled={loading} aria-label="Enviar">
                {loading ? <LoaderCircle className="animate-spin" size={18} /> : <Send size={18} />}
              </button>
            </div>
          </div>
        </div>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-soft">
        <div className="mb-4 flex items-center gap-2 font-bold text-ink"><Sparkles size={18} /> Preguntas rápidas</div>
        <div className="space-y-2">
          {quickQuestions.map((question) => (
            <button key={question} onClick={() => send(question)} disabled={loading} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-sm hover:border-electric hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50">
              {question}
            </button>
          ))}
        </div>
      </aside>
      <ClaimDetail claim={selectedClaim} onClose={() => setSelectedClaim(null)} />
    </div>
  )
}

function TopLoadingBar() {
  return (
    <div className="mt-4 h-1 overflow-hidden rounded-full bg-slate-100">
      <div className="h-full w-1/2 animate-[loadingSlide_1.25s_ease-in-out_infinite] rounded-full bg-electric" />
    </div>
  )
}

function LoadingBubble({ provider }) {
  const steps = provider === 'ollama'
    ? ['Interpretando la pregunta', 'Revisando si requiere datos', 'Generando respuesta con Ollama']
    : ['Interpretando la pregunta', 'Preparando respuesta breve', 'Mostrando resultado']

  return (
    <div className="flex items-start gap-3">
      <Avatar icon={Bot} tone="agent" />
      <div className="max-w-[82%] rounded-lg border border-blue-100 bg-blue-50 px-4 py-4 text-sm text-blue-950 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="relative grid h-12 w-12 shrink-0 place-items-center rounded-full bg-white">
            <span className="absolute h-12 w-12 animate-ping rounded-full bg-blue-200 opacity-60" />
            <LoaderCircle className="relative animate-spin text-electric" size={26} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="font-bold text-ink">Analizando siniestros...</p>
              <TypingDots />
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Espera un momento. CheckIA está interpretando tu mensaje y decidirá si necesita consultar datos o responder directo.
            </p>
            <div className="mt-3 grid gap-2">
              {steps.map((step, index) => (
                <div key={step} className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                  {index < 2 ? <SearchCheck size={14} className="text-emerald-600" /> : <ShieldCheck size={14} className="text-electric" />}
                  {step}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-electric [animation-delay:-0.2s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-electric [animation-delay:-0.1s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-electric" />
    </span>
  )
}

function MessageText({ text, onClaimClick }) {
  const parts = text.split(/(CLM-\d{4})/g)
  return (
    <div className="whitespace-pre-line">
      {parts.map((part, index) => {
        if (/^CLM-\d{4}$/.test(part)) {
          return (
            <button key={`${part}-${index}`} onClick={() => onClaimClick(part)} className="mx-0.5 rounded bg-blue-100 px-1.5 py-0.5 font-bold text-blue-800 hover:bg-blue-200">
              {part}
            </button>
          )
        }
        return <span key={`${part}-${index}`}>{part}</span>
      })}
    </div>
  )
}

function Avatar({ icon: Icon, tone }) {
  return <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${tone === 'agent' ? 'bg-ink text-white' : 'bg-slate-200 text-slate-700'}`}><Icon size={18} /></div>
}

function extractClaimIds(text) {
  return [...new Set((text.match(/CLM-\d{4}/g) || []))]
}
