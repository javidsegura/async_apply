import { NavLink, Outlet } from 'react-router-dom'
import { LayoutGrid, Send, Database, BarChart3, SlidersHorizontal } from 'lucide-react'

const TABS = [
  { to: '/', label: 'Hub', icon: LayoutGrid, end: true },
  { to: '/apply', label: 'Apply', icon: Send },
  { to: '/history', label: 'Applications', icon: Database },
  { to: '/metrics', label: 'Metrics', icon: BarChart3 },
  { to: '/config', label: 'Config', icon: SlidersHorizontal },
]

/**
 * Shell for the AsyncApply section: one pill-style tab bar over a soft
 * gradient ground, so every view inside shares the same frame.
 */
export default function AsyncApplyLayout() {
  return (
    <div className="-mx-6 -my-6 min-h-[calc(100vh-3.5rem)] bg-gradient-to-b from-stone-50 via-white to-stone-50/50 px-6 py-6">
      <nav className="mb-5 flex flex-wrap gap-1 rounded-2xl border border-stone-200/60 bg-white/70 p-1 backdrop-blur-sm">
        {TABS.map((tab) => (
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
      </nav>
      <Outlet />
    </div>
  )
}
