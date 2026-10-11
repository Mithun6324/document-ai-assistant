import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { FileText, MessageSquare, Upload } from 'lucide-react'
import { chatApi } from '../services/api'

function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-semibold">{value}</div>
    </div>
  )
}

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => (await chatApi.dashboard()).data,
  })

  if (isLoading) return <div className="text-slate-400">Loading dashboard…</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-slate-400 text-sm">Overview of your documents and chats</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Documents" value={data?.total_documents ?? 0} />
        <Stat label="Ready" value={data?.ready_documents ?? 0} />
        <Stat label="Processing" value={data?.processing_documents ?? 0} />
        <Stat label="Queries" value={data?.total_queries ?? 0} />
      </div>

      <div className="flex flex-wrap gap-3">
        <Link to="/upload" className="inline-flex items-center gap-2 rounded-lg bg-indigo-500/90 px-4 py-2 text-sm">
          <Upload size={16} /> Upload Document
        </Link>
        <Link to="/chat" className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm">
          <MessageSquare size={16} /> Start Chat
        </Link>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="font-medium mb-3 flex items-center gap-2"><FileText size={16} /> Recent Documents</h2>
          <div className="space-y-2">
            {(data?.recent_documents || []).length === 0 && (
              <p className="text-sm text-slate-400">No documents yet.</p>
            )}
            {(data?.recent_documents || []).map((d) => (
              <Link key={d.id} to={`/documents/${d.id}`} className="block rounded-lg border border-slate-800 px-3 py-2 hover:bg-slate-800/50">
                <div className="text-sm">{d.original_filename}</div>
                <div className="text-xs text-slate-400 capitalize">{d.status}</div>
              </Link>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="font-medium mb-3 flex items-center gap-2"><MessageSquare size={16} /> Recent Conversations</h2>
          <div className="space-y-2">
            {(data?.recent_conversations || []).length === 0 && (
              <p className="text-sm text-slate-400">No chats yet.</p>
            )}
            {(data?.recent_conversations || []).map((c) => (
              <Link key={c.id} to={`/chat?c=${c.id}`} className="block rounded-lg border border-slate-800 px-3 py-2 hover:bg-slate-800/50">
                <div className="text-sm truncate">{c.title}</div>
                <div className="text-xs text-slate-400">{c.message_count} messages</div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
