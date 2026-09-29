import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Send, Database, BarChart3, SlidersHorizontal, ArrowUpRight,
  Sparkles, AlertTriangle, Target, Activity,
} from 'lucide-react'
import { getAsyncApplyBatches, getAsyncApplyItems, getAsyncApplyMe } from '../../api.js'
import { Panel, Stars, SectionHead } from './lib/ui.jsx'
import { formatRelative, countryFlag, STATUS_META } from './lib/format.js'

const CARDS = [
  { to: '/app/apply', icon: Send, title: 'Apply', desc: 'Queue postings, watch them run.', tint: 'from-sky-100 to-sky-50' },
  { to: '/app/history', icon: Database, title: 'Applications', desc: 'Track every application, board or table.', tint: 'from-violet-100 to-violet-50' },
  { to: '/app/metrics', icon: BarChart3, title: 'Metrics', desc: 'Volume, outcomes, real spend.', tint: 'from-emerald-100 to-emerald-50' },
  { to: '/app/config', icon: SlidersHorizontal, title: 'Config', desc: 'Profile, prompts, models.', tint: 'from-rose-100 to-rose-50' },
]

/**
 * The section's front door: a pulse of what's happening, what needs a
 * decision from you right now, and a way into every other view.
 */
export default function Hub() {
  const [items, setItems] = useState([])
  const [batches, setBatches] = useState([])
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    Promise.all([getAsyncApplyItems(), getAsyncApplyBatches()]).then(([i, b]) => {
      setItems(i)
      setBatches(b)
    })
    getAsyncApplyMe().then((me) => setIsAdmin(me.role === 'admin'))
  }, [])

  const stats = useMemo(() => {
    const live = batches.filter((b) => ['queued', 'running'].includes(b.state)).length
    const inPlay = items.filter((i) => ['applied', 'oa', 'interviewing', 'offer'].includes(i.status)).length
    return {
      total: items.length,
      live,
      inPlay,
      spend: items.reduce((s, i) => s + (i.cost_usd || 0), 0),
    }
  }, [items, batches])

  // Two things actually worth acting on: strong matches you never applied to,
  // and runs that broke. Everything else can wait for you to go looking.
  const worthApplying = useMemo(
    () =>
      items
        .filter((i) => i.status === 'evaluated' && !i.hard_stop_reason && (i.score ?? 0) >= 3.5)
        .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
        .slice(0, 5),
    [items],
  )
  const broken = useMemo(() => items.filter((i) => i.state === 'failed').slice(0, 4), [items])
  const recent = useMemo(() => items.slice(0, 6), [items])

  return (
    <div className="space-y-5">
      <div className={`grid grid-cols-2 gap-3 ${isAdmin ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}`}>
        <PulseStat label="Applications" value={stats.total} icon={Database} tint="from-sky-100 to-sky-50" />
        <PulseStat label="In play" value={stats.inPlay} icon={Target} tint="from-emerald-100 to-emerald-50" />
        <PulseStat label="Running now" value={stats.live} icon={Activity} tint="from-violet-100 to-violet-50" live={stats.live > 0} />
        {isAdmin && (
          <PulseStat label="Total spend" value={`$${stats.spend.toFixed(3)}`} icon={Sparkles} tint="from-rose-100 to-rose-50" />
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div className="space-y-4">
          <div>
            <SectionHead title="Worth applying to" hint="Strong fits you haven't acted on yet" />
            <Panel className="divide-y divide-stone-100">
              {worthApplying.map((item) => (
                <Link
                  key={item.id}
                  to="/app/history"
                  className="flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-stone-50/60"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-stone-800">{item.company}</div>
                    <div className="truncate text-[11px] text-stone-400">
                      {countryFlag(item.location)} {item.role}
                    </div>
                  </div>
                  <Stars score={item.score} size={12} />
                  <ArrowUpRight size={13} className="shrink-0 text-stone-300" />
                </Link>
              ))}
              {!worthApplying.length && (
                <p className="px-4 py-8 text-center text-xs text-stone-300">
                  Nothing above a 3.5 waiting. Queue more postings to find some.
                </p>
              )}
            </Panel>
          </div>

          {broken.length > 0 && (
            <div>
              <SectionHead title="Needs attention" hint="Runs that failed and can be retried" />
              <Panel className="divide-y divide-stone-100">
                {broken.map((item) => (
                  <Link
                    key={item.id}
                    to="/app/apply"
                    className="flex items-center gap-2.5 px-4 py-2.5 transition-colors hover:bg-stone-50/60"
                  >
                    <AlertTriangle size={13} className="shrink-0 text-amber-400" />
                    <span className="min-w-0 flex-1 truncate text-xs text-stone-600">
                      {item.company || item.raw_input}
                    </span>
                    <span className="shrink-0 text-[10px] text-stone-300">run {item.batch_id}</span>
                  </Link>
                ))}
              </Panel>
            </div>
          )}
        </div>

        <div>
          <SectionHead title="Latest" />
          <Panel className="divide-y divide-stone-100">
            {recent.map((item) => {
              const meta = STATUS_META[item.status] || STATUS_META.evaluated
              return (
                <div key={item.id} className="flex items-center gap-2.5 px-4 py-2.5">
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${meta.dot}`} />
                  <span className="min-w-0 flex-1 truncate text-xs text-stone-600">
                    {item.company || item.raw_input}
                  </span>
                  <span className="shrink-0 text-[10px] text-stone-300">{formatRelative(item.created_at)}</span>
                </div>
              )
            })}
            {!recent.length && (
              <p className="px-4 py-8 text-center text-xs text-stone-300">No applications yet.</p>
            )}
          </Panel>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
        {CARDS.map((card, i) => (
          <motion.div
            key={card.to}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
          >
            <Link
              to={card.to}
              className="group flex h-full flex-col rounded-2xl border border-stone-200/70 bg-white/80 p-3.5 transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className={`mb-2.5 flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br ${card.tint}`}>
                <card.icon size={15} className="text-stone-600" strokeWidth={2} />
              </div>
              <div className="flex items-center gap-1 text-sm font-medium text-stone-800">
                {card.title}
                <ArrowUpRight size={12} className="text-stone-300 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </div>
              <p className="mt-0.5 text-[11px] leading-snug text-stone-400">{card.desc}</p>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function PulseStat({ label, value, icon: Icon, tint, live }) {
  return (
    <Panel className="p-4">
      <div className="flex items-start justify-between">
        <div className={`flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br ${tint}`}>
          <Icon size={15} className="text-stone-600" strokeWidth={2} />
        </div>
        {live && (
          <motion.span
            className="h-1.5 w-1.5 rounded-full bg-sky-400"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        )}
      </div>
      <div className="mt-2.5 text-[11px] uppercase tracking-wide text-stone-400">{label}</div>
      <div className="text-xl font-semibold tracking-tight text-stone-800">{value}</div>
    </Panel>
  )
}
