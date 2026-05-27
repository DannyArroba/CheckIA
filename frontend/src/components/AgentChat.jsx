import { useEffect, useState } from 'react'
import { Bot, Cpu, MessageSquarePlus, Send, Sparkles, Trash2, UserRound } from 'lucide-react'
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
    if (!conversationId && list[0]) {
      openConversation(list[0].conversation_id)
    }
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
          text: `${response.answer}\n\n${response.disclaimer}`,
          provider: response.provider || 'reglas',
          relatedClaims: response.related_claims || []
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
                    </div>
                  )}
                </div>
                {message.role === 'usuario' && <Avatar icon={UserRound} tone="user" />}
              </div>
            ))}
            {loading && <LoadingBubble />}
          </div>
          <div className="border-t border-slate-200 p-4">
            <div className="flex gap-3">
              <input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && send()} className="min-h-11 flex-1 rounded-lg border border-slate-200 px-4 outline-none focus:border-electric" placeholder="Pregunta sobre riesgos, proveedores, documentos o patrones" />
              <button onClick={() => send()} className="grid h-11 w-11 place-items-center rounded-lg bg-electric text-white hover:bg-blue-700 disabled:opacity-60" disabled={loading} aria-label="Enviar">
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-soft">
        <div className="mb-4 flex items-center gap-2 font-bold text-ink"><Sparkles size={18} /> Preguntas rápidas</div>
        <div className="space-y-2">
          {quickQuestions.map((question) => (
            <button key={question} onClick={() => send(question)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-sm hover:border-electric hover:bg-blue-50">
              {question}
            </button>
          ))}
        </div>
      </aside>
      <ClaimDetail claim={selectedClaim} onClose={() => setSelectedClaim(null)} />
    </div>
  )
}

function LoadingBubble() {
  return (
    <div className="flex items-start gap-3">
      <Avatar icon={Bot} tone="agent" />
      <div className="rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">
        <div className="flex items-center gap-3">
          <span className="relative flex h-8 w-8">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-300 opacity-50"></span>
            <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-full bg-electric text-white">
              <Bot size={15} />
            </span>
          </span>
          <div>
            <p className="font-bold text-ink">Analizando siniestros...</p>
            <p className="text-xs text-slate-500">Espera un momento mientras CheckIA consulta datos y prepara una respuesta segura.</p>
          </div>
        </div>
      </div>
    </div>
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
