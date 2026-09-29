import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Users, Send, Inbox, DollarSign, TrendingUp, ChevronDown, ChevronRight,
  Check, Trash2,
} from 'lucide-react'
import {
  getAsyncApplyAdminUsers, getAsyncApplyAdminUserDetail, updateAsyncApplyAdminBudget,
  getAsyncApplyAdminStats, deleteAsyncApplyAdminUser,
} from '../../api.js'
import { Panel, Stat, SectionHead } from './lib/ui.jsx'
import { formatRelative, formatDateTime } from './lib/format.js'

const WINDOWS = [
  { key: '7d', label: '7d' },
  { key: '30d', label: '30d' },
  { key: '90d', label: '90d' },
  { key: 'all', label: 'All' },
]

/**
 * 👑 The admin's view of everyone using AsyncApply: headline usage for a
 * chosen window, every user's own numbers with an inline budget editor,
 * and a plain-language report generated from the same underlying stats.
 */
export default function Admin() {
  const [window_, setWindow] = useState('30d')
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])

  function refreshUsers() {
    getAsyncApplyAdminUsers().then(setUsers)
  }

  useEffect(() => {
    getAsyncApplyAdminStats(window_).then(setStats)
  }, [window_])

  useEffect(refreshUsers, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionHead title="👑 Admin" hint="Who's using AsyncApply, and how much it's costing." />
        <div className="flex gap-1 rounded-xl bg-stone-100/70 p-1">
          {WINDOWS.map((w) => (
            <button
              key={w.key}
              onClick={() => setWindow(w.key)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                window_ === w.key ? 'bg-white text-stone-700 shadow-sm' : 'text-stone-400 hover:text-stone-600'
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <Stat label="Active users" value={stats.active_users} icon={Users} tint="from-violet-100 to-violet-50" />
          <Stat label="Batches" value={stats.total_batches} icon={Send} tint="from-sky-100 to-sky-50" />
          <Stat label="Items" value={stats.total_items} icon={Inbox} tint="from-emerald-100 to-emerald-50" />
          <Stat label="Spend" value={`$${stats.total_spend_usd.toFixed(3)}`} icon={DollarSign} tint="from-rose-100 to-rose-50" />
          <Stat label="Avg cost/item" value={`$${stats.avg_cost_per_item_usd.toFixed(4)}`} icon={TrendingUp} tint="from-amber-100 to-amber-50" />
        </div>
      )}

      <div>
        <SectionHead title="Users" hint={`${users.length} total`} />
        <Panel className="divide-y divide-stone-100">
          {users.map((u) => (
            <UserRow key={u.id} user={u} onBudgetSaved={refreshUsers} onUserDeleted={refreshUsers} />
          ))}
          {!users.length && <p className="px-4 py-8 text-center text-xs text-stone-300">No users yet.</p>}
        </Panel>
      </div>
    </div>
  )
}

function UserRow({ user, onBudgetSaved, onUserDeleted }) {
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState(null)
  const [budget, setBudget] = useState(user.token_budget_usd)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState(null)

  function toggle() {
    setOpen((v) => !v)
    if (!detail) getAsyncApplyAdminUserDetail(user.id).then(setDetail)
  }

  async function saveBudget(e) {
    e.stopPropagation()
    setSaving(true)
    try {
      await updateAsyncApplyAdminBudget(user.id, Number(budget))
      setSaved(true)
      onBudgetSaved()
      setTimeout(() => setSaved(false), 1500)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(e) {
    e.stopPropagation()
    if (!confirmingDelete) {
      setConfirmingDelete(true)
      return
    }
    setDeleting(true)
    setDeleteError(null)
    try {
      await deleteAsyncApplyAdminUser(user.id)
      onUserDeleted()
    } catch (err) {
      setDeleteError(err.message)
      setConfirmingDelete(false)
    } finally {
      setDeleting(false)
    }
  }

  const overBudget = user.spent_usd >= user.token_budget_usd

  return (
    <div>
      <div onClick={toggle} className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-stone-50/60">
        {open ? <ChevronDown size={14} className="shrink-0 text-stone-300" /> : <ChevronRight size={14} className="shrink-0 text-stone-300" />}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 truncate text-sm font-medium text-stone-800">
            {user.email}
            {user.role === 'admin' && (
              <span className="rounded-full bg-stone-100 px-1.5 py-0.5 text-[9px] font-medium text-stone-500">admin</span>
            )}
          </div>
          <div className="text-[11px] text-stone-400">
            {user.batch_count} batch{user.batch_count === 1 ? '' : 'es'} · {user.item_count} item{user.item_count === 1 ? '' : 's'}
            {user.last_active_at && ` · last active ${formatRelative(user.last_active_at)}`}
          </div>
        </div>
        <div className={`shrink-0 text-right text-xs ${overBudget ? 'text-rose-500' : 'text-stone-500'}`}>
          ${user.spent_usd.toFixed(3)} / ${user.token_budget_usd.toFixed(2)}
        </div>
        <div className="flex shrink-0 items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
          <input
            type="number"
            step="0.5"
            min="0"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            className="w-20 rounded-lg border border-stone-200/70 bg-white px-2 py-1 text-xs focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
          />
          <button
            onClick={saveBudget}
            disabled={saving}
            className="flex items-center gap-1 rounded-lg bg-stone-800 px-2 py-1 text-[11px] font-medium text-white transition-opacity disabled:opacity-40"
          >
            {saved ? <Check size={11} /> : 'Set'}
          </button>
          <button
            onClick={handleDelete}
            onBlur={() => setConfirmingDelete(false)}
            disabled={deleting}
            title={confirmingDelete ? 'Click again to permanently delete' : 'Delete user'}
            className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium transition-colors disabled:opacity-40 ${
              confirmingDelete
                ? 'bg-rose-600 text-white'
                : 'text-stone-300 hover:bg-rose-50 hover:text-rose-500'
            }`}
          >
            <Trash2 size={12} />
            {confirmingDelete && 'Confirm'}
          </button>
        </div>
      </div>
      {deleteError && (
        <p className="px-4 pb-2 text-[11px] text-rose-500">{deleteError}</p>
      )}

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-stone-100 bg-stone-50/50 px-4 py-2.5">
              {!detail && <p className="text-xs text-stone-300">Loading...</p>}
              {detail && !detail.batches.length && (
                <p className="text-xs text-stone-300">No batches yet.</p>
              )}
              {detail?.batches.map((b) => (
                <div key={b.id} className="flex items-center gap-3 py-1 text-[11px] text-stone-500">
                  <span className="w-16 shrink-0">Run {b.id}</span>
                  <span className="w-16 shrink-0">{b.state}</span>
                  <span className="w-20 shrink-0">{b.item_count} item{b.item_count === 1 ? '' : 's'}</span>
                  <span className="w-20 shrink-0">${b.cost_usd.toFixed(4)}</span>
                  <span className="text-stone-400">{formatDateTime(b.created_at)}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
