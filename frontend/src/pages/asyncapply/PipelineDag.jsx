import { motion } from 'framer-motion'
import { FileSearch, ClipboardCheck, Users, Check, X, Minus } from 'lucide-react'

const STAGES = [
  { key: 'extract', label: 'Extract', icon: FileSearch },
  { key: 'evaluate', label: 'Evaluate', icon: ClipboardCheck },
  { key: 'contact', label: 'Outreach', icon: Users },
]

/**
 * Work out each stage's status from what the worker actually recorded.
 *
 * There is no per-stage progress field in the backend, so "running" can only
 * honestly be shown as "somewhere in here" -- not which exact stage, since
 * that isn't tracked. Failure messages are prefixed by stage ("extraction
 * failed: …", "evaluation failed: …", "contact lookup failed: …"), which is
 * what makes the failed/done split accurate rather than guessed.
 *
 * @param {object} item
 * @returns {Array<'pending'|'active'|'done'|'failed'|'skipped'>}
 */
export function deriveStages(item) {
  const err = item.error || ''
  if (item.state === 'queued') return ['pending', 'pending', 'pending']
  if (item.state === 'running') return ['active', 'active', 'active']
  if (item.state === 'failed') {
    if (err.includes('evaluation failed')) return ['done', 'failed', 'pending']
    return ['failed', 'pending', 'pending']
  }
  if (item.hard_stop_reason) return ['done', 'done', 'skipped']
  if (err.includes('contact lookup failed')) return ['done', 'done', 'failed']
  return ['done', 'done', 'done']
}

const NODE = {
  pending: 'bg-stone-50 text-stone-300 ring-stone-200',
  active: 'bg-sky-50 text-sky-500 ring-sky-200',
  done: 'bg-emerald-50 text-emerald-500 ring-emerald-200',
  failed: 'bg-rose-50 text-rose-500 ring-rose-200',
  skipped: 'bg-stone-50 text-stone-300 ring-stone-200 ring-dashed',
}
const LINK = {
  pending: 'bg-stone-200',
  active: 'bg-sky-200',
  done: 'bg-emerald-200',
  failed: 'bg-rose-200',
  skipped: 'bg-stone-200',
}

/**
 * The three pipeline stages as a compact chain of nodes.
 *
 * @param {{item?: object, statuses?: string[], size?: 'sm'|'lg'}} props
 */
export default function PipelineDag({ item, statuses, size = 'sm' }) {
  const states = statuses || deriveStages(item)
  const lg = size === 'lg'

  return (
    <div className="flex items-center">
      {STAGES.map((stage, i) => {
        const state = states[i]
        const Icon = stage.icon
        return (
          <div key={stage.key} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <motion.div
                animate={state === 'active' ? { opacity: [0.5, 1, 0.5] } : { opacity: 1 }}
                transition={
                  state === 'active'
                    ? { duration: 2.4, repeat: Infinity, ease: 'easeInOut', delay: i * 0.35 }
                    : { duration: 0 }
                }
                title={stage.label}
                className={`flex items-center justify-center rounded-full ring-1 transition-colors ${NODE[state]} ${lg ? 'h-8 w-8' : 'h-5 w-5'}`}
              >
                {state === 'done' && <Check size={lg ? 14 : 10} strokeWidth={3} />}
                {state === 'failed' && <X size={lg ? 14 : 10} strokeWidth={3} />}
                {state === 'skipped' && <Minus size={lg ? 14 : 10} strokeWidth={3} />}
                {(state === 'pending' || state === 'active') && <Icon size={lg ? 14 : 10} />}
              </motion.div>
              {lg && <span className="text-[10px] text-stone-400">{stage.label}</span>}
            </div>
            {i < STAGES.length - 1 && (
              <div className={`${lg ? 'mb-4 h-[2px] w-7' : 'h-[2px] w-3'} mx-1 rounded-full ${LINK[state]}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
