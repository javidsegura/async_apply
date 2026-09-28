import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Star, Check, ChevronDown } from 'lucide-react'
import { STATUS_META, PIPELINE_STATUSES } from './format.js'

/**
 * A fit score as five stars, halves included.
 *
 * Replaces the bare number: "4.5" makes you do the mental conversion every
 * time, where a row of stars reads at a glance and sorts visually down a
 * column.
 *
 * @param {{score: number|null, size?: number}} props
 */
export function Stars({ score, size = 13 }) {
  if (score == null) return <span className="text-stone-300">—</span>

  return (
    <span className="flex items-center gap-[1px]" title={`${score.toFixed(1)} / 5`}>
      {[0, 1, 2, 3, 4].map((i) => {
        const fill = Math.max(0, Math.min(1, score - i))
        return (
          <span key={i} className="relative inline-block" style={{ width: size, height: size }}>
            <Star size={size} className="absolute inset-0 text-stone-200" fill="currentColor" />
            {fill > 0 && (
              <span
                className="absolute inset-0 overflow-hidden"
                style={{ width: `${fill * 100}%` }}
              >
                <Star size={size} className="text-amber-300" fill="currentColor" />
              </span>
            )}
          </span>
        )
      })}
    </span>
  )
}

/**
 * The current application status, as a labeled pill that opens a menu.
 *
 * Deliberately verbose rather than clever: an earlier version showed the
 * status as a stack of unlabeled colour slivers, which was unreadable
 * without a legend. A word plus a colour dot needs no legend.
 *
 * @param {{status: string, onChange: (status: string) => void, compact?: boolean}} props
 */
export function StatusSelect({ status, onChange, compact = false }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    function onDocClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  const meta = STATUS_META[status] || STATUS_META.evaluated
  const locked = status === 'hard_stopped'

  if (locked) {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${meta.chip}`}>
        <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
        {meta.label}
      </span>
    )
  }

  return (
    <div className="relative" ref={ref} onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex w-full items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors ${meta.chip} hover:brightness-95`}
      >
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${meta.dot}`} />
        <span className="truncate">{meta.label}</span>
        {!compact && <ChevronDown size={11} className="ml-auto shrink-0 opacity-50" />}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.12 }}
            className="absolute right-0 z-30 mt-1 w-40 overflow-hidden rounded-xl border border-stone-200/80 bg-white/95 p-1 shadow-lg backdrop-blur"
          >
            {PIPELINE_STATUSES.map((key) => {
              const option = STATUS_META[key]
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    onChange(key)
                    setOpen(false)
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs text-stone-600 hover:bg-stone-50"
                >
                  <span className={`h-2 w-2 shrink-0 rounded-full ${option.dot}`} />
                  {option.label}
                  {key === status && <Check size={12} className="ml-auto text-stone-400" />}
                </button>
              )
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * The standard surface: soft white card, hairline border, generous radius.
 *
 * @param {{className?: string, children: React.ReactNode}} props
 */
export function Panel({ className = '', children, ...rest }) {
  return (
    <div
      className={`rounded-2xl border border-stone-200/70 bg-white/80 shadow-[0_1px_2px_rgba(0,0,0,0.03)] backdrop-blur-sm ${className}`}
      {...rest}
    >
      {children}
    </div>
  )
}

/**
 * A small labelled statistic, for the dashboard-style grids.
 *
 * @param {{label: string, value: React.ReactNode, sub?: string, tint?: string, icon?: Function}} props
 */
export function Stat({ label, value, sub, tint = 'from-sky-100 to-sky-50', icon: Icon }) {
  return (
    <Panel className="p-4">
      {Icon && (
        <div className={`mb-2.5 flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br ${tint}`}>
          <Icon size={15} className="text-stone-600" strokeWidth={2} />
        </div>
      )}
      <div className="text-[11px] uppercase tracking-wide text-stone-400">{label}</div>
      <div className="mt-0.5 text-xl font-semibold tracking-tight text-stone-800">{value}</div>
      {sub && <div className="text-[11px] text-stone-400">{sub}</div>}
    </Panel>
  )
}

/**
 * Section heading with an optional trailing control.
 *
 * @param {{title: string, hint?: string, right?: React.ReactNode}} props
 */
export function SectionHead({ title, hint, right }) {
  return (
    <div className="mb-2.5 flex items-end justify-between gap-3">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-stone-700">{title}</h3>
        {hint && <p className="text-[11px] text-stone-400">{hint}</p>}
      </div>
      {right}
    </div>
  )
}
