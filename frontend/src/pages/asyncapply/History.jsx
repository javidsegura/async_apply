import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, ChevronDown, LayoutGrid, Rows3, Hash, Trash2, Ban } from 'lucide-react'
import {
  getAsyncApplyItems, updateAsyncApplyItem, deleteAsyncApplyItem, asyncApplyLogoUrl,
} from '../../api.js'
import ItemDetail from './ItemDetail.jsx'
import { Panel, Stars, StatusSelect, SectionHead } from './lib/ui.jsx'
import {
  formatDate, formatRelative, countryFlag, STATUS_META, PIPELINE_STATUSES,
} from './lib/format.js'

const SORTERS = {
  newest: (a, b) => new Date(b.created_at) - new Date(a.created_at),
  oldest: (a, b) => new Date(a.created_at) - new Date(b.created_at),
  score: (a, b) => (b.score ?? -1) - (a.score ?? -1),
  cost: (a, b) => (b.cost_usd ?? 0) - (a.cost_usd ?? 0),
}

/**
 * Every application ever run. Two views over the same rows: a board grouped
 * by where each application stands (the default, since that is the question
 * you actually open this page to answer), and a dense table for searching
 * and sorting the raw record.
 */
export default function History() {
  const [items, setItems] = useState([])
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sort, setSort] = useState('newest')
  const [view, setView] = useState('board')

  useEffect(() => {
    getAsyncApplyItems().then(setItems)
  }, [])

  function handleStatusChange(item, status) {
    if (item.status === status) return
    setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, status } : i)))
    updateAsyncApplyItem(item.id, { status })
  }

  async function handleDelete(item) {
    const name = item.company || item.raw_input
    if (!window.confirm(`Delete ${name}? This removes the row and its generated PDFs.`)) return
    setItems((prev) => prev.filter((i) => i.id !== item.id))
    await deleteAsyncApplyItem(item.id)
  }

  const visible = useMemo(() => {
    let rows = items
    if (statusFilter !== 'all') rows = rows.filter((i) => i.status === statusFilter)
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      rows = rows.filter((i) =>
        [i.company, i.role, i.location, i.verdict].some((f) => f?.toLowerCase().includes(q)),
      )
    }
    return [...rows].sort(SORTERS[sort])
  }, [items, query, statusFilter, sort])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-stone-800">Applications</h1>
          <p className="text-sm text-stone-400">
            {items.length} application{items.length === 1 ? '' : 's'} tracked end to end.
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-xl bg-stone-100/80 p-1">
          {[
            { key: 'board', label: 'Board', icon: LayoutGrid },
            { key: 'table', label: 'Table', icon: Rows3 },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setView(key)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                view === key ? 'bg-white text-stone-700 shadow-sm' : 'text-stone-400 hover:text-stone-600'
              }`}
            >
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto_auto_auto]">
        <div className="relative">
          <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stone-300" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search company, role, location, verdict…"
            className="w-full rounded-xl border border-stone-200/70 bg-white/80 py-2 pl-9 pr-3 text-sm placeholder:text-stone-300 focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-xl border border-stone-200/70 bg-white/80 px-3 py-2 text-xs text-stone-600 focus:outline-none"
        >
          <option value="all">All statuses</option>
          {Object.entries(STATUS_META).map(([key, meta]) => (
            <option key={key} value={key}>{meta.label}</option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded-xl border border-stone-200/70 bg-white/80 px-3 py-2 text-xs text-stone-600 focus:outline-none"
        >
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
          <option value="score">Best fit</option>
          <option value="cost">Priciest</option>
        </select>
        <span className="flex items-center justify-center rounded-xl bg-stone-100/70 px-3 text-[11px] text-stone-400">
          {visible.length} shown
        </span>
      </div>

      {view === 'board' ? (
        <BoardView items={visible} onStatusChange={handleStatusChange} onDelete={handleDelete} />
      ) : (
        <TableView items={visible} onStatusChange={handleStatusChange} onDelete={handleDelete} />
      )}
    </div>
  )
}

function BoardView({ items, onStatusChange, onDelete }) {
  const [dragId, setDragId] = useState(null)
  const [overStatus, setOverStatus] = useState(null)

  const { byStatus, filtered } = useMemo(() => {
    const grouped = Object.fromEntries(PIPELINE_STATUSES.map((s) => [s, []]))
    const out = []
    for (const item of items) {
      if (item.status === 'hard_stopped') out.push(item)
      else if (grouped[item.status]) grouped[item.status].push(item)
    }
    return { byStatus: grouped, filtered: out }
  }, [items])

  function handleDrop(e, status) {
    e.preventDefault()
    const carried = Number(e.dataTransfer.getData('text/plain'))
    const id = Number.isFinite(carried) && carried ? carried : dragId
    const item = items.find((i) => i.id === id)
    if (item) onStatusChange(item, status)
    setDragId(null)
    setOverStatus(null)
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-7">
        {PIPELINE_STATUSES.map((status) => {
          const meta = STATUS_META[status]
          const rows = byStatus[status]
          const isTarget = overStatus === status && dragId != null
          return (
            <div
              key={status}
              onDragOver={(e) => {
                e.preventDefault()
                e.dataTransfer.dropEffect = 'move'
                setOverStatus(status)
              }}
              onDragLeave={() => setOverStatus((s) => (s === status ? null : s))}
              onDrop={(e) => handleDrop(e, status)}
              className={`min-w-0 rounded-xl p-1 transition-colors ${
                isTarget ? 'bg-sky-50/80 ring-1 ring-sky-200' : ''
              }`}
            >
              <div className="mb-2 flex items-center gap-1.5 px-1">
                <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                <span className="text-xs font-medium text-stone-600">{meta.label}</span>
                <span className="ml-auto text-[11px] text-stone-300">{rows.length}</span>
              </div>
              <div className="max-h-[520px] space-y-2 overflow-y-auto pr-0.5">
                {rows.map((item) => (
                  <BoardCard
                    key={item.id}
                    item={item}
                    dragging={dragId === item.id}
                    onDragStart={() => setDragId(item.id)}
                    onDragEnd={() => {
                      setDragId(null)
                      setOverStatus(null)
                    }}
                    onStatusChange={onStatusChange}
                    onDelete={onDelete}
                  />
                ))}
                {!rows.length && (
                  <div className={`rounded-xl border border-dashed px-2 py-5 text-center text-[11px] transition-colors ${
                    isTarget ? 'border-sky-300 text-sky-500' : 'border-stone-200/80 text-stone-300'
                  }`}>
                    {isTarget ? 'drop here' : 'empty'}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {filtered.length > 0 && <FilteredOut items={filtered} onDelete={onDelete} />}
    </div>
  )
}

/**
 * The postings the pipeline refused to write documents for. Grouped by the
 * rule that stopped them, since "five were filtered" is only useful once you
 * can see it was four sponsorship refusals and one clearance requirement.
 */
function FilteredOut({ items, onDelete }) {
  const [open, setOpen] = useState(false)

  const groups = useMemo(() => {
    const byRule = new Map()
    for (const item of items) {
      const reason = item.hard_stop_reason || ''
      const rule = /sponsor/i.test(reason)
        ? 'No sponsorship'
        : /citizen|clearance/i.test(reason)
          ? 'Citizenship or clearance'
          : 'Other rule'
      if (!byRule.has(rule)) byRule.set(rule, [])
      byRule.get(rule).push(item)
    }
    return [...byRule.entries()].sort((a, b) => b[1].length - a[1].length)
  }, [items])

  return (
    <div>
      <SectionHead
        title={`Filtered out (${items.length})`}
        hint="Stopped by a rule before a CV was written — no action to take."
        right={
          <button
            onClick={() => setOpen((v) => !v)}
            className="text-[11px] text-stone-400 hover:text-stone-600"
          >
            {open ? 'Hide' : 'Show reasons'}
          </button>
        }
      />
      <div className="flex flex-wrap gap-2">
        {groups.map(([rule, rows]) => (
          <span key={rule} className="flex items-center gap-1.5 rounded-full bg-amber-50/70 px-3 py-1.5 text-[11px] font-medium text-amber-800">
            <Ban size={11} />
            {rule}
            <span className="rounded-full bg-white/70 px-1.5 text-[10px]">{rows.length}</span>
          </span>
        ))}
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-3">
              {groups.map(([rule, rows]) => (
                <div key={rule}>
                  <div className="mb-1.5 text-[11px] font-medium text-stone-500">{rule}</div>
                  <Panel className="divide-y divide-stone-100">
                    {rows.map((item) => (
                      <div key={item.id} className="flex items-start gap-3 px-3.5 py-2.5">
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-xs font-medium text-stone-700">
                            {countryFlag(item.location)} {item.company || item.raw_input}
                          </div>
                          <p className="mt-0.5 text-[11px] leading-relaxed text-stone-400">
                            {item.hard_stop_reason || 'No reason recorded.'}
                          </p>
                        </div>
                        <button
                          onClick={() => onDelete(item)}
                          title="Delete"
                          className="shrink-0 rounded-lg p-1.5 text-stone-300 transition-colors hover:bg-rose-50 hover:text-rose-500"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))}
                  </Panel>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function BoardCard({ item, dragging, onDragStart, onDragEnd, onStatusChange, onDelete }) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <div
        draggable
        onDragStart={(e) => {
          e.dataTransfer.setData('text/plain', String(item.id))
          e.dataTransfer.effectAllowed = 'move'
          onDragStart()
        }}
        onDragEnd={onDragEnd}
        onClick={() => setOpen(true)}
        className={`group relative w-full cursor-grab rounded-xl border border-stone-200/70 bg-white p-2.5 text-left shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-all active:cursor-grabbing ${
          dragging ? 'opacity-40' : 'hover:shadow-md'
        }`}
      >
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(item)
          }}
          title="Delete"
          className="absolute right-1 top-1 rounded-md bg-white/90 p-1 text-stone-300 opacity-0 transition-opacity hover:text-rose-500 group-hover:opacity-100"
        >
          <Trash2 size={11} />
        </button>
        <div className="flex items-start gap-2">
          <CompanyMark company={item.company} />
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium text-stone-800">
              {item.company || item.raw_input}
            </div>
            <div className="truncate text-[11px] text-stone-400">{item.role || '—'}</div>
          </div>
        </div>
        <div className="mt-2 flex items-center justify-between">
          <Stars score={item.score} size={11} />
          <span className="text-[10px] text-stone-300">
            {countryFlag(item.location)} {formatDate(item.created_at)}
          </span>
        </div>
      </div>

      <DetailModal
        item={item}
        open={open}
        onClose={() => setOpen(false)}
        onStatusChange={onStatusChange}
        onDelete={onDelete}
      />
    </>
  )
}

function DetailModal({ item, open, onClose, onStatusChange, onDelete }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-stone-900/25 p-6 backdrop-blur-[2px]"
        >
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ type: 'spring', bounce: 0.15, duration: 0.35 }}
            onClick={(e) => e.stopPropagation()}
            className="my-8 w-full max-w-2xl rounded-2xl bg-white p-5 shadow-2xl"
          >
            <div className="mb-3 flex items-start gap-3">
              <CompanyMark company={item.company} size={38} />
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold text-stone-800">
                  {item.company || item.raw_input}
                </div>
                <div className="truncate text-xs text-stone-400">{item.role || '—'}</div>
              </div>
              <Stars score={item.score} />
              <StatusSelect status={item.status} onChange={(s) => onStatusChange(item, s)} />
              <button
                onClick={() => {
                  onClose()
                  onDelete(item)
                }}
                title="Delete this application"
                className="rounded-lg p-1.5 text-stone-300 transition-colors hover:bg-rose-50 hover:text-rose-500"
              >
                <Trash2 size={14} />
              </button>
            </div>
            <ItemDetail item={item} />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

const COLUMNS = '[grid-template-columns:34px_minmax(0,1.7fr)_minmax(0,1fr)_92px_86px_120px_70px_46px]'

function TableView({ items, onStatusChange, onDelete }) {
  return (
    <Panel className="overflow-hidden">
      <div className={`hidden gap-3 border-b border-stone-100 px-4 py-2 text-[10px] font-medium uppercase tracking-wide text-stone-400 sm:grid ${COLUMNS}`}>
        <span />
        <span>Company / role</span>
        <span>Location</span>
        <span>Work auth</span>
        <span>Fit</span>
        <span>Status</span>
        <span className="text-right">Added</span>
        <span />
      </div>
      <div className="divide-y divide-stone-100">
        {items.map((item) => (
          <TableRow key={item.id} item={item} onStatusChange={onStatusChange} onDelete={onDelete} />
        ))}
        {items.length === 0 && (
          <p className="py-10 text-center text-sm text-stone-400">No applications match.</p>
        )}
      </div>
    </Panel>
  )
}

function TableRow({ item, onStatusChange, onDelete }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="transition-colors hover:bg-stone-50/50">
      {/* A div, not a button: the status control is itself a button, and
          nesting one inside another is invalid HTML -- the browser then
          routes the click to the outer row instead of opening the menu. */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setExpanded((v) => !v)
          }
        }}
        className={`grid w-full cursor-pointer items-center gap-3 px-4 py-2.5 text-left ${COLUMNS}`}
      >
        <CompanyMark company={item.company} />
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-sm font-medium text-stone-800">
              {item.company || item.raw_input}
            </span>
            <span className="flex shrink-0 items-center gap-0.5 rounded-full bg-stone-100 px-1.5 text-[9px] font-medium text-stone-400">
              <Hash size={8} />{item.batch_id}
            </span>
          </div>
          <div className="truncate text-[11px] text-stone-400">{item.role || '—'}</div>
        </div>
        <div className="hidden truncate text-[11px] text-stone-400 sm:block">
          {countryFlag(item.location)} {item.location || ''}
        </div>
        <div className="hidden truncate text-[11px] text-stone-400 md:block">{item.work_auth_tier || ''}</div>
        <Stars score={item.score} />
        <StatusSelect status={item.status} onChange={(s) => onStatusChange(item, s)} />
        <span className="text-right text-[11px] text-stone-400" title={item.created_at}>
          {formatRelative(item.created_at)}
        </span>
        <span className="flex items-center gap-0.5">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete(item)
            }}
            title="Delete"
            className="rounded-md p-1 text-stone-200 transition-colors hover:bg-rose-50 hover:text-rose-500"
          >
            <Trash2 size={12} />
          </button>
          <ChevronDown size={14} className={`text-stone-300 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </span>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="border-t border-stone-100 bg-stone-50/40 px-4 pb-4 pt-3">
              <ItemDetail item={item} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function CompanyMark({ company, size = 30 }) {
  const [broken, setBroken] = useState(false)
  const style = { width: size, height: size }

  if (!company || broken) {
    return (
      <div
        style={style}
        className="flex shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-stone-100 to-stone-200/70 text-[11px] font-semibold text-stone-400"
      >
        {company?.[0]?.toUpperCase() || '?'}
      </div>
    )
  }
  return (
    <img
      src={asyncApplyLogoUrl(company)}
      onError={() => setBroken(true)}
      alt=""
      style={style}
      className="shrink-0 rounded-lg bg-white object-contain ring-1 ring-stone-100"
    />
  )
}
