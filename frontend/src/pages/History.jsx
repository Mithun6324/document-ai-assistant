import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Download } from 'lucide-react'
import { chatApi } from '../services/api'

export default function History() {
  const { data = [], isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: async () => (await chatApi.history()).data,
  })

  async function exportMd(id, title) {
    const res = await chatApi.export(id)
    const blob = new Blob([res.data], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title || 'conversation'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold">Chat History</h1>
        <p className="text-sm text-slate-400">Revisit and export previous conversations</p>
      </div>

      {isLoading && <div className="text-slate-400">Loading…</div>}

      <div className="space-y-2">
        {data.map((c) => (
          <div key={c.id} className="rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <Link to={`/chat?c=${c.id}`} className="min-w-0">
              <div className="font-medium truncate hover:text-indigo-300">{c.title}</div>
              <div className="text-xs text-slate-400 mt-1">
                {c.scope === 'all' ? 'All documents' : `${(c.document_ids || []).length} selected docs`} · {c.message_count} messages ·{' '}
                {new Date(c.updated_at).toLocaleString()}
              </div>
            </Link>
            <button
              type="button"
              onClick={() => exportMd(c.id, c.title)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-sm"
            >
              <Download size={14} /> Export
            </button>
          </div>
        ))}
        {!isLoading && data.length === 0 && (
          <p className="text-sm text-slate-400">No conversations yet.</p>
        )}
      </div>
    </div>
  )
}
