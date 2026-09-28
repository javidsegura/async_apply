import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import {
  getAsyncApplyAgentDna,
  updateAsyncApplyAgentDna,
  getAsyncApplyAgentDnaAdminNote,
  updateAsyncApplyAgentDnaAdminNote,
  getAsyncApplyMe,
} from '../../api.js'

/**
 * The agent's writing voice: a handful of predefined vibe questions
 * (pill choices, always resolving to a sensible default) plus a free-text
 * box for anything the questions don't cover. Admins additionally see a
 * global rule block appended to every user's voice, regardless of their
 * own answers.
 */
export default function AgentDnaForm() {
  const [questions, setQuestions] = useState([])
  const [choices, setChoices] = useState({})
  const [notes, setNotes] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState(null)
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    getAsyncApplyAgentDna().then((r) => {
      setQuestions(r.questions)
      setChoices(r.choices)
      setNotes(r.notes)
      setLoaded(true)
    })
    getAsyncApplyMe().then((me) => setIsAdmin(me.role === 'admin'))
  }, [])

  function choose(key, value) {
    setChoices((c) => ({ ...c, [key]: value }))
  }

  async function handleSave() {
    setSaving(true)
    setStatus(null)
    try {
      const saved = await updateAsyncApplyAgentDna(choices, notes)
      setChoices(saved.choices)
      setNotes(saved.notes)
      setStatus({ ok: true, message: 'Saved.' })
    } catch (err) {
      setStatus({ ok: false, message: err.message })
    } finally {
      setSaving(false)
    }
  }

  if (!loaded) return <p className="text-sm text-stone-400">Loading...</p>

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-stone-200/70 bg-white/80 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <h3 className="mb-1 font-medium text-stone-800">🎭 Agent DNA</h3>
        <p className="mb-4 text-xs text-stone-500">
          Pick the vibe for every generated cover letter and outreach message. Leave a question
          untouched and it uses a sensible default -- nothing here is required.
        </p>

        <div className="space-y-4">
          {questions.map((q) => (
            <div key={q.key}>
              <label className="mb-1.5 block text-xs font-medium text-stone-600">{q.label}</label>
              <div className="flex flex-wrap gap-1.5">
                {q.options.map((opt, i) => {
                  const selected = (choices[q.key] || q.options[0].value) === opt.value
                  return (
                    <button
                      key={opt.value}
                      onClick={() => choose(q.key, opt.value)}
                      className={`flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors ${
                        selected
                          ? 'border-sky-200 bg-sky-50 text-sky-700'
                          : 'border-stone-200/70 text-stone-400 hover:border-stone-300 hover:text-stone-600'
                      }`}
                    >
                      {selected && <Check size={11} />}
                      {opt.label}
                      {i === 0 && !choices[q.key] && (
                        <span className="text-stone-300">(default)</span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-stone-200/70 bg-white/80 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <label className="mb-1 block text-sm font-medium text-stone-800">
          ✍️ Anything else? Write it in your own words
        </label>
        <p className="mb-2 text-xs text-stone-500">
          Free-form. e.g. "Always mention I'm open to relocating" or "Never open with 'I'm excited to...'"
        </p>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={4}
          placeholder="Anything the questions above didn't cover..."
          className="w-full rounded-xl border border-stone-200/70 bg-white px-3 py-2 text-sm placeholder:text-stone-300 focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
        />
      </div>

      <div className="flex items-center gap-3">
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={handleSave}
          disabled={saving}
          className="rounded-xl bg-stone-800 px-4 py-2 text-sm font-medium text-white shadow-sm transition-opacity disabled:opacity-30"
        >
          {saving ? 'Saving...' : 'Save'}
        </motion.button>
        {status && (
          <span className={`text-xs ${status.ok ? 'text-emerald-600' : 'text-rose-600'}`}>{status.message}</span>
        )}
      </div>

      {isAdmin && <AdminNote />}
    </div>
  )
}

/**
 * The fixed rule block only the admin can see or edit, appended to every
 * user's agent DNA regardless of their own choices -- workspace-wide
 * house style, not a personal preference.
 */
function AdminNote() {
  const [content, setContent] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    getAsyncApplyAgentDnaAdminNote().then((r) => {
      setContent(r.content)
      setLoaded(true)
    })
  }, [])

  async function handleSave() {
    setSaving(true)
    setStatus(null)
    try {
      await updateAsyncApplyAgentDnaAdminNote(content)
      setStatus({ ok: true, message: 'Saved.' })
    } catch (err) {
      setStatus({ ok: false, message: err.message })
    } finally {
      setSaving(false)
    }
  }

  if (!loaded) return null

  return (
    <div className="rounded-2xl border border-amber-200/70 bg-amber-50/40 p-5">
      <h3 className="mb-1 text-sm font-medium text-amber-800">🔒 Global rules (admin only)</h3>
      <p className="mb-2 text-xs text-amber-700/80">
        Applies to every user's generated writing, on top of their own choices above.
      </p>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={3}
        placeholder="e.g. Never mention salary expectations first."
        className="w-full rounded-xl border border-amber-200/70 bg-white px-3 py-2 text-sm placeholder:text-stone-300 focus:border-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-100"
      />
      <div className="mt-2 flex items-center gap-3">
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={handleSave}
          disabled={saving}
          className="rounded-xl bg-amber-700 px-3.5 py-1.5 text-xs font-medium text-white shadow-sm transition-opacity disabled:opacity-30"
        >
          {saving ? 'Saving...' : 'Save'}
        </motion.button>
        {status && (
          <span className={`text-xs ${status.ok ? 'text-emerald-600' : 'text-rose-600'}`}>{status.message}</span>
        )}
      </div>
    </div>
  )
}
