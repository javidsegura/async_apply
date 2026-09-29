import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { LayoutGrid, Send, Database, BarChart3, SlidersHorizontal, LogOut, Crown } from 'lucide-react'
import { useAuth } from '../../auth/AuthProvider.jsx'
import { getAsyncApplyMe } from '../../api.js'
import Logo from '../../components/Logo.jsx'

const TABS = [
  { to: '/', label: 'Hub', icon: LayoutGrid, end: true, adminOnly: false },
  { to: '/apply', label: 'Apply', icon: Send, adminOnly: false },
  { to: '/history', label: 'Applications', icon: Database, adminOnly: false },
  { to: '/metrics', label: 'Metrics', icon: BarChart3, adminOnly: false },
  { to: '/config', label: 'Config', icon: SlidersHorizontal, adminOnly: false },
  { to: '/admin', label: 'Admin', icon: Crown, adminOnly: true },
]

/**
 * Shell for the AsyncApply section: one pill-style tab bar over a soft
 * gradient ground, so every view inside shares the same frame.
 */
export default function AsyncApplyLayout() {
  const { user, signOutUser } = useAuth()
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    getAsyncApplyMe().then((me) => setIsAdmin(me.role === 'admin'))
  }, [])

  const visibleTabs = TABS.filter((t) => !t.adminOnly || isAdmin)

  return (
    <div className="min-h-screen bg-gradient-to-b from-stone-50 via-white to-stone-50/50 px-3 py-5 sm:px-4">
      <nav className="mb-5 flex flex-wrap items-center gap-1 rounded-2xl border border-stone-200/60 bg-white/70 p-1 backdrop-blur-sm">
        <Logo className="mx-2 hidden sm:inline-flex" textClassName="text-xs text-stone-500" />
        {visibleTabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-medium transition-all ${
                isActive
                  ? 'bg-stone-800 text-white shadow-sm'
                  : 'text-stone-500 hover:bg-stone-100/70 hover:text-stone-700'
              }`
            }
          >
            <tab.icon size={14} />
            {tab.label}
          </NavLink>
        ))}
        <div className="ml-auto flex items-center gap-2 pr-2">
          {user?.email && <span className="hidden text-[11px] text-stone-400 sm:inline">{user.email}</span>}
          <button
            onClick={signOutUser}
            title="Sign out"
            className="flex items-center gap-1 rounded-xl px-2.5 py-2 text-xs font-medium text-stone-400 transition-colors hover:bg-stone-100/70 hover:text-stone-700"
          >
            <LogOut size={13} />
          </button>
        </div>
      </nav>
      <Outlet />
    </div>
  )
}
