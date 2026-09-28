import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, CheckCircle2, Star, DollarSign, Maximize2, X, Timer } from 'lucide-react'
import { getAsyncApplyItems } from '../../api.js'
import Sankey from './Sankey.jsx'
import { Panel, Stat, Stars, SectionHead } from './lib/ui.jsx'
import { duration, formatDateTime, parseUtc, countryFlag, STATUS_META } from './lib/format.js'

const SPANS = [
  { key: '7', label: '7d', days: 7 },
  { key: '30', label: '30d', days: 30 },
  { key: '90', label: '90d', days: 90 },
  { key: 'all', label: 'All', days: null },
]

/**
 * Group items by ISO week (YYYY-Www), for the weekly volume chart.
 *
 * @param {Date} date
 * @returns {string}
 */
function isoWeekKey(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const dayNum = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum)
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  const week = Math.ceil(((d - yearStart) / 86400000 + 1) / 7)
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, '0')}`
}

/** Mean of a numeric list, or null when empty. */
function mean(values) {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null
}

/**
 * Throughput, outcomes and real spend over a chosen window -- every cost
 * figure is what OpenRouter actually billed, not an estimate.
 */
export default function Metrics() {
  const [items, setItems] = useState([])
  const [span, setSpan] = useState('30')

  useEffect(() => {
    getAsyncApplyItems().then(setItems)
  }, [])

  const scoped = useMemo(() => {
    const def = SPANS.find((s) => s.key === span)
    if (!def.days) return items
    const cutoff = Date.now() - def.days * 86400000
    return items.filter((i) => (parseUtc(i.created_at)?.getTime() ?? 0) >= cutoff)
  }, [items, span])

  const stats = useMemo(() => {
    const runtimes = scoped
      .map((i) => {
        const from = parseUtc(i.started_at)
        const to = parseUtc(i.ended_at)
        return from && to ? (to - from) / 1000 : null
      })
      .filter((s) => s != null && s >= 0)
    return {
      total: scoped.length,
      applied: scoped.filter((i) => ['applied', 'oa', 'interviewing', 'offer'].includes(i.status)).length,
      avgScore: mean(scoped.map((i) => i.score).filter((s) => s != null)),
      totalCost: scoped.reduce((s, i) => s + (i.cost_usd || 0), 0),
      totalTokens: scoped.reduce((s, i) => s + (i.total_tokens || 0), 0),
      avgCost: mean(scoped.map((i) => i.cost_usd).filter((c) => c != null)),
      avgRuntime: mean(runtimes),
    }
  }, [scoped])

  const byWeek = useMemo(() => {
    const buckets = new Map()
    for (const item of scoped) {
      const date = parseUtc(item.created_at)
      if (!date) continue
      const key = isoWeekKey(date)
      const entry = buckets.get(key) || { key, count: 0, cost: 0 }
      entry.count += 1
      entry.cost += item.cost_usd || 0
      buckets.set(key, entry)
    }
    return [...buckets.values()].sort((a, b) => a.key.localeCompare(b.key))
  }, [scoped])

  const byStatus = useMemo(() => {
    const counts = {}
    for (const item of scoped) counts[item.status] = (counts[item.status] || 0) + 1
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }, [scoped])

  const funnel = useMemo(() => buildFunnel(scoped), [scoped])

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-stone-800">Metrics</h1>
          <p className="text-sm text-stone-400">Throughput, outcomes and real spend.</p>
        </div>
        <div className="flex gap-1 rounded-xl bg-stone-100/80 p-1">
          {SPANS.map((s) => (
            <button
              key={s.key}
              onClick={() => setSpan(s.key)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                span === s.key ? 'bg-white text-stone-700 shadow-sm' : 'text-stone-400 hover:text-stone-600'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat icon={Send} label="Submitted" value={stats.total} tint="from-sky-100 to-sky-50" />
        <Stat icon={CheckCircle2} label="In play" value={stats.applied} tint="from-emerald-100 to-emerald-50" />
        <Stat
          icon={Star}
          label="Avg fit"
          value={stats.avgScore != null ? <Stars score={stats.avgScore} /> : '—'}
          tint="from-amber-100 to-amber-50"
        />
        <Stat
          icon={Timer}
          label="Avg runtime"
          value={stats.avgRuntime != null ? `${Math.round(stats.avgRuntime)}s` : '—'}
          tint="from-violet-100 to-violet-50"
        />
        <Stat
          icon={DollarSign}
          label="Spend"
          value={`$${stats.totalCost.toFixed(3)}`}
          sub={
            stats.avgCost != null
              ? `$${stats.avgCost.toFixed(4)} avg · ${stats.totalTokens.toLocaleString()} tokens`
              : `${stats.totalTokens.toLocaleString()} tokens`
          }
          tint="from-rose-100 to-rose-50"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel className="p-4">
          <SectionHead title="Volume & cost" hint="Per ISO week" />
          <WeeklyChart data={byWeek} />
        </Panel>
        <Panel className="p-4">
          <SectionHead title="Where they stand" />
          <StatusChart data={byStatus} total={stats.total} />
        </Panel>
      </div>

      <FunnelSection funnel={funnel} />

      <div>
        <SectionHead title="Raw data" hint="Every application in the window" />
        <RawTable items={scoped} />
      </div>
    </div>
  )
}

function WeeklyChart({ data }) {
  if (!data.length) return <p className="py-6 text-center text-xs text-stone-300">No data in this window.</p>
  const max = Math.max(1, ...data.map((d) => d.count))

  return (
    <div className="space-y-1.5">
      {data.map((d) => (
        <div key={d.key} className="flex items-center gap-2 text-[11px]">
          <span className="w-16 shrink-0 text-stone-400">{d.key.slice(5)}</span>
          <div className="h-3.5 flex-1 overflow-hidden rounded-full bg-stone-100">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-sky-200 to-sky-300"
              initial={{ width: 0 }}
              animate={{ width: `${(d.count / max) * 100}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>
          <span className="w-7 text-right text-stone-500">{d.count}</span>
          <span className="w-14 text-right text-stone-300">${d.cost.toFixed(3)}</span>
        </div>
      ))}
    </div>
  )
}

function StatusChart({ data, total }) {
  if (!total) return <p className="py-6 text-center text-xs text-stone-300">No data in this window.</p>
  return (
    <div className="space-y-1.5">
      {data.map(([status, count]) => {
        const meta = STATUS_META[status] || STATUS_META.evaluated
        return (
          <div key={status} className="flex items-center gap-2 text-[11px]">
            <span className="flex w-24 shrink-0 items-center gap-1.5 text-stone-500">
              <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
              {meta.label}
            </span>
            <div className="h-3.5 flex-1 overflow-hidden rounded-full bg-stone-100">
              <motion.div
                className={`h-full rounded-full ${meta.dot} opacity-70`}
                initial={{ width: 0 }}
                animate={{ width: `${(count / total) * 100}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
            <span className="w-7 text-right text-stone-500">{count}</span>
          </div>
        )
      })}
    </div>
  )
}

function RawTable({ items }) {
  return (
    <Panel className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead className="bg-stone-50/70 text-left text-[10px] uppercase tracking-wide text-stone-400">
            <tr>
              <th className="px-3 py-2 font-medium">When</th>
              <th className="px-3 py-2 font-medium">Company</th>
              <th className="px-3 py-2 font-medium">Location</th>
              <th className="px-3 py-2 font-medium">Fit</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Runtime</th>
              <th className="px-3 py-2 font-medium">Tokens</th>
              <th className="px-3 py-2 font-medium">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {items.map((item) => {
              const meta = STATUS_META[item.status] || STATUS_META.evaluated
              return (
                <tr key={item.id} className="hover:bg-stone-50/50">
                  <td className="whitespace-nowrap px-3 py-2 text-stone-400">{formatDateTime(item.created_at)}</td>
                  <td className="px-3 py-2 text-stone-700">{item.company || '—'}</td>
                  <td className="px-3 py-2 text-stone-400">
                    {countryFlag(item.location)} {item.location || '—'}
                  </td>
                  <td className="px-3 py-2"><Stars score={item.score} size={10} /></td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] ${meta.chip}`}>{meta.label}</span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-stone-400">
                    {duration(item.started_at, item.ended_at) || '—'}
                  </td>
                  <td className="px-3 py-2 text-stone-400">{item.total_tokens?.toLocaleString() ?? '—'}</td>
                  <td className="px-3 py-2 text-stone-400">
                    {item.cost_usd != null ? `$${item.cost_usd.toFixed(4)}` : '—'}
                  </td>
                </tr>
              )
            })}
            {!items.length && (
              <tr><td colSpan={8} className="px-3 py-8 text-center text-stone-300">Nothing in this window.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

/**
 * Build the application funnel as a value tree: submitted -> hard-stopped or
 * evaluated -> not-yet-applied or applied+ -> outcomes. Each level strictly
 * partitions its parent, since every item holds exactly one status.
 *
 * @param {object[]} items
 * @returns {object}
 */
function buildFunnel(items) {
  const count = (pred) => items.filter(pred).length
  const hardStopped = count((i) => !!i.hard_stop_reason)
  const notApplied = count((i) => i.status === 'evaluated')
  const inProcess = count((i) => ['oa', 'interviewing'].includes(i.status))
  const stillApplied = count((i) => i.status === 'applied')
  const offer = count((i) => i.status === 'offer')
  const rejected = count((i) => i.status === 'rejected')
  const withdrawn = count((i) => i.status === 'withdrawn')
  const appliedPlus = inProcess + stillApplied + offer + rejected + withdrawn
  const evaluated = notApplied + appliedPlus

  return {
    id: 'submitted', label: 'Submitted', value: items.length, color: '#a8a29e',
    children: [
      { id: 'hardstop', label: 'Filtered out', value: hardStopped, color: '#fcd34d' },
      {
        id: 'evaluated', label: 'Evaluated', value: evaluated, color: '#7dd3fc',
        children: [
          { id: 'notapplied', label: 'Not applied', value: notApplied, color: '#e7e5e4' },
          {
            id: 'appliedplus', label: 'Applied', value: appliedPlus, color: '#38bdf8',
            children: [
              { id: 'stillapplied', label: 'Waiting', value: stillApplied, color: '#38bdf8' },
              { id: 'inprocess', label: 'OA / interviewing', value: inProcess, color: '#818cf8' },
              { id: 'offer', label: 'Offer', value: offer, color: '#6ee7b7' },
              { id: 'rejected', label: 'Rejected', value: rejected, color: '#fda4af' },
              { id: 'withdrawn', label: 'Withdrawn', value: withdrawn, color: '#d6d3d1' },
            ].filter((n) => n.value > 0),
          },
        ].filter((n) => n.value > 0),
      },
    ].filter((n) => n.value > 0),
  }
}

function FunnelSection({ funnel }) {
  const [open, setOpen] = useState(false)
  if (!funnel.value) return null

  return (
    <div>
      <SectionHead
        title="Application funnel"
        hint="Where every submission ended up"
        right={
          <button
            onClick={() => setOpen(true)}
            className="flex items-center gap-1 text-[11px] text-stone-400 hover:text-stone-600"
          >
            <Maximize2 size={11} /> Expand
          </button>
        }
      />
      <Panel className="cursor-pointer p-4 transition-shadow hover:shadow-md" onClick={() => setOpen(true)}>
        <Sankey root={funnel} width={640} height={86} compact />
      </Panel>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/25 p-6 backdrop-blur-[2px]"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.97, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97, y: 8 }}
              transition={{ type: 'spring', bounce: 0.15, duration: 0.35 }}
              onClick={(e) => e.stopPropagation()}
              className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-2xl bg-white p-6 shadow-2xl"
            >
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-semibold tracking-tight text-stone-800">Application funnel</h3>
                <button onClick={() => setOpen(false)} className="text-stone-300 hover:text-stone-500">
                  <X size={18} />
                </button>
              </div>
              <Sankey root={funnel} width={860} height={420} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
