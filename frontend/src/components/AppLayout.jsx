import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  FileText,
  History,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Upload,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/history', label: 'History', icon: History },
]

export default function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 shrink-0 border-r border-slate-800 bg-slate-950/70 backdrop-blur p-4 hidden md:flex md:flex-col">
        <div className="mb-8">
          <div className="text-lg font-semibold tracking-tight">Document AI</div>
          <div className="text-xs text-slate-400">Assistant</div>
        </div>
        <nav className="flex flex-col gap-1 flex-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-indigo-500/20 text-indigo-200'
                    : 'text-slate-300 hover:bg-slate-800/80'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="pt-4 border-t border-slate-800">
          <div className="text-xs text-slate-400 mb-2 truncate">{user?.email}</div>
          <button
            onClick={() => {
              logout()
              navigate('/login')
            }}
            className="flex items-center gap-2 text-sm text-slate-300 hover:text-white"
          >
            <LogOut size={16} /> Logout
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="md:hidden flex items-center gap-2 overflow-x-auto border-b border-slate-800 px-3 py-2 bg-slate-950/80">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-1 rounded-md px-2 py-1 text-xs whitespace-nowrap ${
                  isActive ? 'bg-indigo-500/20 text-indigo-200' : 'text-slate-300'
                }`
              }
            >
              <Icon size={14} /> {label}
            </NavLink>
          ))}
        </header>
        <main className="flex-1 p-4 md:p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
