import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Loader2, RotateCcw, Plus, X, Sparkles, Inbox } from 'lucide-react'
import {
  createAsyncApplyBatch, getAsyncApplyBatches, retryAsyncApplyBatch, updateAsyncApplyItem,
} from '../../api.js'
import ItemDetail from './ItemDetail.jsx'
import PipelineDag from './PipelineDag.jsx'
import ProcessingHint from './ProcessingHint.jsx'
import { Panel, Stars, StatusSelect } from './lib/ui.jsx'
import { duration, formatRelative, countryFlag } from './lib/format.js'

const ACTIVE = new Set(['queued', 'running'])

const BATCH_TINT = {
  queued: 'bg-stone-100 text-stone-500',
  running: 'bg-sky-50 text-sky-600',
  done: 'bg-emerald-50 text-emerald-600',
  failed: 'bg-rose-50 text-rose-600',
  partial: 'bg-amber-50 text-amber-700',
}

/**
 * Submit postings and watch one batch at a time move through the pipeline:
 * a composer across the top, a rail of batches down the left, and the
 * selected batch's items as a grid filling the rest.
 */
export default function Pipeline() {
  const [batches, setBatches] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [pending, setPending] = useState([])
  const [draft, setDraft] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)
  const picked = useRef(false)

  async function refresh() {
    const data = await getAsyncApplyBatches()
    setBatches(data)
    return data
  }

  useEffect(() => {
    refresh()
    return () => clearInterval(pollRef.current)
  }, [])

  useEffect(() => {
    if (!picked.current && batches.length) {
      setSelectedId(batches[0].id)
      picked.current = true
    }
  }, [batches])

  useEffect(() => {
    const live = batches.some((b) => ACTIVE.has(b.state) || b.items.some((i) => ACTIVE.has(i.state)))
    clearInterval(pollRef.current)
    if (live) pollRef.current = setInterval(refresh, 4000)
    return () => clearInterval(pollRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batches])

  const selected = batches.find((b) => b.id === selectedId) || null

  function addDraft(text) {
    const lines = text.split('\n').map((s) => s.trim()).filter(Boolean)
    if (lines.length) setPending((p) => [...p, ...lines])
    setDraft('')
  }

  async function submit(e) {
    e.preventDefault()
    if (!pending.length) return
    setSubmitting(true)
    setError(null)
    try {
      const created = await createAsyncApplyBatch(pending)
      setPending([])
      setSelectedId(created.id)
      picked.current = true
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  function setStatus(item, status) {
    setBatches((prev) =>
      prev.map((b) => ({ ...b, items: b.items.map((i) => (i.id === item.id ? { ...i, status } : i)) })),
    )
    updateAsyncApplyItem(item.id, { status })
  }

  return (
    <div className="space-y-4">
      <Composer
        draft={draft}
        setDraft={setDraft}
        pending={pending}
        onAdd={addDraft}
        onRemove={(i) => setPending((p) => p.filter((_, idx) => idx !== i))}
        onSubmit={submit}
        submitting={submitting}
        error={error}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[210px_minmax(0,1fr)]">
        <BatchRail batches={batches} selectedId={selectedId} onSelect={setSelectedId} />
        {selected ? (
          <BatchPanel
            key={selected.id}
            batch={selected}
            onRetry={() => retryAsyncApplyBatch(selected.id).then(refresh)}
            onStatusChange={setStatus}
          />
        ) : (
          <Empty />
        )}
      </div>
    </div>
  )
}

function Composer({ draft, setDraft, pending, onAdd, onRemove, onSubmit, submitting, error }) {
  return (
    <Panel className="overflow-hidden">
      <div className="h-[3px] bg-gradient-to-r from-sky-200 via-violet-200 to-rose-200" />
      <form onSubmit={onSubmit} className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[260px] flex-1">
            <Plus size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stone-300" />
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  if (draft.trim()) onAdd(draft)
                }
              }}
              onPaste={(e) => {
                const text = e.clipboardData.getData('text')
                if (text.includes('\n')) {
                  e.preventDefault()
                  onAdd(text)
                }
              }}
              placeholder="Paste a job URL or description, press Enter"
              className="w-full rounded-xl border border-stone-200/70 bg-white py-2 pl-9 pr-3 text-sm placeholder:text-stone-300 focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
            />
          </div>
          <motion.button
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={submitting || !pending.length}
            className="flex items-center gap-2 rounded-xl bg-stone-800 px-4 py-2 text-sm font-medium text-white shadow-sm transition-opacity disabled:opacity-25"
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {submitting ? 'Sending' : `Run ${pending.length || ''}`}
          </motion.button>
        </div>

        <AnimatePresence initial={false}>
          {pending.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="flex flex-wrap gap-1.5 pt-2.5">
                {pending.map((item, i) => (
                  <motion.span
                    key={`${item}-${i}`}
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex max-w-[280px] items-center gap-1.5 rounded-full bg-sky-50/80 py-1 pl-3 pr-1.5 text-[11px] text-sky-700"
                  >
                    <span className="truncate">{item}</span>
                    <button
                      type="button"
                      onClick={() => onRemove(i)}
                      className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-sky-400 hover:bg-sky-100"
                    >
                      <X size={10} />
                    </button>
                  </motion.span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {error && <p className="pt-2 text-xs text-rose-600">{error}</p>}
        {!pending.length && !error && (
          <p className="flex items-center gap-1.5 pt-2 text-[11px] text-stone-300">
            <Sparkles size={11} /> Paste several lines at once to queue a whole batch.
          </p>
        )}
      </form>
    </Panel>
  )
}

function BatchRail({ batches, selectedId, onSelect }) {
  return (
    <div>
      <div className="mb-2 px-1 text-[10px] font-medium uppercase tracking-wide text-stone-400">
        Runs
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1 lg:max-h-[600px] lg:flex-col lg:overflow-y-auto lg:pr-1">
        {batches.map((batch) => {
          const live = ACTIVE.has(batch.state)
          const failed = batch.items.filter((i) => i.state === 'failed').length
          const cost = batch.items.reduce((s, i) => s + (i.cost_usd || 0), 0)
          return (
            <button
              key={batch.id}
              onClick={() => onSelect(batch.id)}
              className={`min-w-[150px] shrink-0 rounded-xl border px-3 py-2 text-left transition-all lg:min-w-0 ${
                selectedId === batch.id
                  ? 'border-stone-300 bg-white shadow-sm'
                  : 'border-transparent bg-white/50 hover:bg-white'
              }`}
            >
              <div className="flex items-center gap-1.5">
                {live && <motion.span
                  className="h-1.5 w-1.5 rounded-full bg-sky-400"
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />}
                <span className="text-xs font-medium text-stone-700">Run {batch.id}</span>
                <span className={`ml-auto rounded px-1.5 text-[9px] font-medium ${BATCH_TINT[batch.state] || BATCH_TINT.queued}`}>
                  {batch.state}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-2 text-[10px] text-stone-400">
                <span>{batch.items.length} job{batch.items.length === 1 ? '' : 's'}</span>
                {failed > 0 && <span className="text-rose-400">{failed} failed</span>}
                {cost > 0 && <span>${cost.toFixed(3)}</span>}
                <span className="ml-auto">{formatRelative(batch.created_at)}</span>
              </div>
            </button>
          )
        })}
        {!batches.length && <p className="px-1 text-[11px] text-stone-300">Nothing run yet.</p>}
      </div>
    </div>
  )
}

function BatchPanel({ batch, onRetry, onStatusChange }) {
  const failed = batch.items.filter((i) => i.state === 'failed').length
  const cost = batch.items.reduce((s, i) => s + (i.cost_usd || 0), 0)
  const took = duration(batch.started_at, batch.ended_at)
  const done = batch.items.filter((i) => !ACTIVE.has(i.state)).length
  const progress = batch.items.length ? done / batch.items.length : 0

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="min-w-0 space-y-3">
      <Panel className="overflow-hidden">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
          <span className="text-sm font-semibold text-stone-800">Run {batch.id}</span>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${BATCH_TINT[batch.state] || BATCH_TINT.queued}`}>
            {batch.state}
          </span>
          <span className="text-[11px] text-stone-400">{formatRelative(batch.created_at)}</span>
          {took && <span className="text-[11px] text-stone-400">· {took}</span>}
          <div className="ml-auto flex items-center gap-3 text-[11px] text-stone-400">
            <span>{done}/{batch.items.length}</span>
            {cost > 0 && <span>${cost.toFixed(4)}</span>}
            {failed > 0 && (
              <button onClick={onRetry} className="flex items-center gap-1 font-medium text-amber-600 hover:underline">
                <RotateCcw size={11} /> Retry {failed}
              </button>
            )}
          </div>
        </div>
        <div className="h-[2px] bg-stone-100">
          <motion.div
            className="h-full bg-gradient-to-r from-sky-300 to-emerald-300"
            animate={{ width: `${progress * 100}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        {batch.items.map((item) => (
          <ItemCard key={item.id} item={item} onStatusChange={onStatusChange} />
        ))}
      </div>
    </motion.div>
  )
}

function ItemCard({ item, onStatusChange }) {
  const [open, setOpen] = useState(false)
  const settled = item.state === 'done' || item.state === 'failed'

  return (
    <Panel className="overflow-hidden">
      <button
        onClick={() => settled && setOpen((v) => !v)}
        className={`w-full p-3.5 text-left ${settled ? '' : 'cursor-default'}`}
      >
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-stone-800">
              {item.company || item.raw_input}
            </div>
            <div className="truncate text-[11px] text-stone-400">
              {countryFlag(item.location)} {item.role || (item.state === 'running' ? '' : '—')}
            </div>
          </div>
          {item.score != null && <Stars score={item.score} size={12} />}
        </div>

        <div className="mt-3 flex items-center justify-between gap-3">
          <PipelineDag item={item} />
          {item.hard_stop_reason ? (
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">filtered</span>
          ) : item.error ? (
            <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-medium text-rose-600">error</span>
          ) : null}
        </div>

        {item.state === 'running' && (
          <div className="mt-2"><ProcessingHint /></div>
        )}
      </button>

      <AnimatePresence initial={false}>
        {open && settled && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="border-t border-stone-100 bg-stone-50/40 px-3.5 pb-3.5 pt-3">
              <ItemDetail item={item} />
              <div className="mt-3 flex items-center gap-2">
                <span className="text-[11px] text-stone-400">Status</span>
                <StatusSelect status={item.status} onChange={(s) => onStatusChange(item, s)} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Panel>
  )
}

function Empty() {
  return (
    <Panel className="flex flex-col items-center justify-center gap-4 border-dashed px-6 py-16 text-center">
      <Inbox size={26} className="text-stone-200" />
      <p className="text-sm text-stone-400">Queue a posting above to watch it run.</p>
      <div className="flex items-center gap-3 rounded-xl bg-stone-50/80 px-5 py-3">
        <span className="text-[11px] text-stone-400">Each job flows through</span>
        <PipelineDag statuses={['done', 'done', 'done']} size="lg" />
      </div>
    </Panel>
  )
}
