import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { MessageSquare, Trash2 } from 'lucide-react'
import { documentsApi } from '../services/api'

function StatusBadge({ status }) {
  const map = {
    ready: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    processing: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    failed: 'bg-red-500/15 text-red-300 border-red-500/30',
  }
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs capitalize ${map[status] || 'border-slate-700 text-slate-300'}`}>
      {status}
    </span>
  )
}

export default function Documents() {
  const qc = useQueryClient()
  const { data = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: async () => (await documentsApi.list()).data,
    refetchInterval: (query) => {
      const docs = query.state.data || []
      return docs.some((d) => ['pending', 'processing'].includes(d.status)) ? 3000 : false
    },
  })

  const del = useMutation({
    mutationFn: (id) => documentsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">My Documents</h1>
          <p className="text-sm text-slate-400">All uploads and their questions</p>
        </div>
        <Link to="/upload" className="rounded-lg bg-indigo-500/90 px-3 py-2 text-sm">+ Upload</Link>
      </div>

      {isLoading && <div className="text-slate-400">Loading…</div>}

      <div className="space-y-2">
        {data.map((d) => (
          <div key={d.id} className="rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 flex flex-col md:flex-row md:items-center gap-3 justify-between">
            <div>
              <Link to={`/documents/${d.id}`} className="font-medium hover:text-indigo-300">
                {d.original_filename}
              </Link>
              <div className="text-xs text-slate-400 mt-1 flex flex-wrap gap-2 items-center">
                <StatusBadge status={d.status} />
                <span>{d.page_count} pages</span>
                <span>{d.chunk_count} chunks</span>
                <span>{d.question_count} questions</span>
                {d.status === 'processing' && <span>{d.progress_percent}%</span>}
              </div>
            </div>
            <div className="flex gap-2">
              <Link
                to={`/chat?doc=${d.id}`}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-sm"
              >
                <MessageSquare size={14} /> Chat
              </Link>
              <button
                onClick={() => {
                  if (confirm('Soft-delete this document?')) del.mutate(d.id)
                }}
                className="inline-flex items-center gap-1 rounded-lg border border-red-500/30 px-3 py-1.5 text-sm text-red-300"
              >
                <Trash2 size={14} /> Delete
              </button>
            </div>
          </div>
        ))}
        {!isLoading && data.length === 0 && (
          <div className="rounded-xl border border-slate-800 p-8 text-center text-slate-400">
            No documents yet. <Link className="text-indigo-300 underline" to="/upload">Upload one</Link>
          </div>
        )}
      </div>
    </div>
  )
}
