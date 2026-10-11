import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { ChevronDown, ChevronUp, Send, ThumbsDown, ThumbsUp } from 'lucide-react'
import { chatApi, documentsApi, streamChat } from '../services/api'

function SourcePanel({ sources, highlightId, onSelect }) {
  if (!sources?.length) {
    return <div className="text-sm text-slate-400 p-3">Sources will appear here after an answer.</div>
  }
  return (
    <div className="space-y-2 p-3">
      {sources.map((s) => {
        const active = highlightId === s.chunk_id
        return (
          <button
            key={s.chunk_id}
            type="button"
            onClick={() => onSelect?.(s.chunk_id)}
            className={`w-full text-left rounded-lg border px-3 py-2 transition ${
              active ? 'border-indigo-400 bg-indigo-500/10' : 'border-slate-800 bg-slate-900/60'
            }`}
          >
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>{s.document_name}</span>
              <span>{(s.similarity_score * 100).toFixed(0)}%</span>
            </div>
            <div className="text-xs text-slate-500 mb-1">
              Page {s.page_number ?? '—'} · {s.section_name || 'General'}
            </div>
            <div className="text-sm text-slate-200 line-clamp-4">{s.text_preview}</div>
          </button>
        )
      })}
    </div>
  )
}

export default function Chat() {
  const [params] = useSearchParams()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState(params.get('c') || null)
  const [selectedDocs, setSelectedDocs] = useState(() => (params.get('doc') ? [params.get('doc')] : []))
  const [streaming, setStreaming] = useState(false)
  const [sources, setSources] = useState([])
  const [highlightId, setHighlightId] = useState(null)
  const [showSources, setShowSources] = useState(true)
  const [suggested, setSuggested] = useState([])
  const bottomRef = useRef(null)

  const docsQuery = useQuery({
    queryKey: ['documents'],
    queryFn: async () => (await documentsApi.list()).data,
  })

  const readyDocs = useMemo(
    () => (docsQuery.data || []).filter((d) => d.status === 'ready'),
    [docsQuery.data],
  )

  useEffect(() => {
    const q = params.get('q')
    if (q) setInput(q)
  }, [params])

  useEffect(() => {
    async function loadConversation() {
      const c = params.get('c')
      if (!c) return
      const { data } = await chatApi.detail(c)
      setConversationId(data.id)
      setMessages(
        data.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources || [],
          feedback: m.feedback,
        })),
      )
      const lastAssistant = [...data.messages].reverse().find((m) => m.role === 'assistant')
      setSources(lastAssistant?.sources || [])
    }
    loadConversation().catch(() => {})
  }, [params])

  useEffect(() => {
    if (selectedDocs.length === 1) {
      documentsApi.suggested(selectedDocs[0]).then((res) => setSuggested(res.data)).catch(() => setSuggested([]))
    } else {
      setSuggested(['Summarize the selected documents', 'What are the key points?', 'Extract important dates and names'])
    }
  }, [selectedDocs])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  async function send(questionText) {
    const question = (questionText || input).trim()
    if (!question || streaming) return
    setInput('')
    setStreaming(true)
    setHighlightId(null)

    const userMsg = { id: `u-${Date.now()}`, role: 'user', content: question }
    const assistantMsg = { id: `a-${Date.now()}`, role: 'assistant', content: '', sources: [], pending: true }
    setMessages((prev) => [...prev, userMsg, assistantMsg])

    try {
      await streamChat(
        {
          question,
          conversation_id: conversationId || undefined,
          document_ids: selectedDocs.length ? selectedDocs : undefined,
        },
        {
          onEvent: (event) => {
            if (event.type === 'meta') {
              setConversationId(event.conversation_id)
            }
            if (event.type === 'sources') {
              setSources(event.sources || [])
              setMessages((prev) => {
                const copy = [...prev]
                const last = copy[copy.length - 1]
                if (last?.role === 'assistant') last.sources = event.sources || []
                return copy
              })
            }
            if (event.type === 'token') {
              setMessages((prev) => {
                const copy = [...prev]
                const last = copy[copy.length - 1]
                if (last?.role === 'assistant') {
                  last.content += event.content
                  last.pending = true
                }
                return copy
              })
            }
            if (event.type === 'done') {
              setConversationId(event.conversation_id)
              setSources(event.sources || [])
              setMessages((prev) => {
                const copy = [...prev]
                const last = copy[copy.length - 1]
                if (last?.role === 'assistant') {
                  last.id = event.message_id
                  last.sources = event.sources || []
                  last.pending = false
                }
                return copy
              })
            }
          },
        },
      )
    } catch (err) {
      setMessages((prev) => {
        const copy = [...prev]
        const last = copy[copy.length - 1]
        if (last?.role === 'assistant') {
          last.content = err.message || 'Failed to get answer'
          last.pending = false
        }
        return copy
      })
    } finally {
      setStreaming(false)
    }
  }

  async function giveFeedback(messageId, rating) {
    try {
      await chatApi.feedback(messageId, { rating })
      setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, feedback: rating } : m)))
    } catch {
      // ignore
    }
  }

  function toggleDoc(id) {
    setSelectedDocs((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  return (
    <div className="h-[calc(100vh-5rem)] md:h-[calc(100vh-3rem)] flex flex-col gap-3">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Chat</h1>
          <p className="text-sm text-slate-400">Ask across all docs or filter by selection</p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <button
            type="button"
            onClick={() => setSelectedDocs([])}
            className={`rounded-full px-3 py-1 text-xs border ${
              selectedDocs.length === 0 ? 'border-indigo-400 text-indigo-200' : 'border-slate-700 text-slate-300'
            }`}
          >
            All documents
          </button>
          {readyDocs.map((d) => (
            <button
              key={d.id}
              type="button"
              onClick={() => toggleDoc(d.id)}
              className={`rounded-full px-3 py-1 text-xs border max-w-[180px] truncate ${
                selectedDocs.includes(d.id) ? 'border-indigo-400 text-indigo-200' : 'border-slate-700 text-slate-300'
              }`}
              title={d.original_filename}
            >
              {d.original_filename}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 grid lg:grid-cols-[1fr_320px] gap-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-sm text-slate-400">
                Upload documents, then ask questions. Answers are grounded in your files with citations.
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                    m.role === 'user' ? 'bg-slate-700/80' : 'bg-slate-950/80 border border-slate-800'
                  }`}
                >
                  {m.content || (m.pending ? 'Thinking…' : '')}
                  {m.role === 'assistant' && m.sources?.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-slate-800 space-y-1">
                      <div className="text-xs text-slate-400">Sources</div>
                      {m.sources.map((s) => (
                        <button
                          key={s.chunk_id}
                          type="button"
                          className="block text-xs text-indigo-300 hover:underline"
                          onClick={() => {
                            setSources(m.sources)
                            setHighlightId(s.chunk_id)
                            setShowSources(true)
                          }}
                        >
                          Page {s.page_number ?? '—'} · Chunk {s.chunk_id.slice(0, 8)} · {s.document_name}
                        </button>
                      ))}
                      {!m.pending && typeof m.id === 'string' && !m.id.startsWith('a-') && (
                        <div className="flex gap-2 pt-2">
                          <button type="button" onClick={() => giveFeedback(m.id, 'up')} className={`${m.feedback === 'up' ? 'text-emerald-300' : 'text-slate-400'}`}>
                            <ThumbsUp size={14} />
                          </button>
                          <button type="button" onClick={() => giveFeedback(m.id, 'down')} className={`${m.feedback === 'down' ? 'text-red-300' : 'text-slate-400'}`}>
                            <ThumbsDown size={14} />
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {suggested.length > 0 && (
            <div className="px-4 pb-2 flex flex-wrap gap-2">
              {suggested.map((q) => (
                <button
                  key={q}
                  type="button"
                  disabled={streaming}
                  onClick={() => send(q)}
                  className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-indigo-400 disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault()
              send()
            }}
            className="p-3 border-t border-slate-800 flex gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents…"
              className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 outline-none focus:border-indigo-500"
              disabled={streaming}
            />
            <button
              type="submit"
              disabled={streaming || !input.trim()}
              className="rounded-xl bg-indigo-500 px-3 py-2 disabled:opacity-50"
            >
              <Send size={16} />
            </button>
          </form>
        </div>

        <aside className="rounded-xl border border-slate-800 bg-slate-900/40 min-h-0 flex flex-col">
          <button
            type="button"
            className="flex items-center justify-between px-3 py-2 border-b border-slate-800 text-sm"
            onClick={() => setShowSources((v) => !v)}
          >
            Sources
            {showSources ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {showSources && (
            <div className="flex-1 overflow-y-auto">
              <SourcePanel sources={sources} highlightId={highlightId} onSelect={setHighlightId} />
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
