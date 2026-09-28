import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { getAsyncApplyAgentDna, updateAsyncApplyAgentDna } from '../../api.js'

/**
 * Free-form writing-voice rules applied to every generated cover letter and
 * outreach message. Still a text editor for now -- the multiple-choice
 * "vibe" questionnaire is a later redesign, not part of this pass.
 */
export default function AgentDnaForm() {
  const [content, setContent] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    getAsyncApplyAgentDna().then((r) => {
      setContent(r.content)
      setLoaded(true)
    })
  }, [])

  async function handleSave() {
    setSaving(true)
    setStatus(null)
    try {
      await updateAsyncApplyAgentDna(content)
      setStatus({ ok: true, message: 'Saved.' })
    } catch (err) {
      setStatus({ ok: false, message: err.message })
    } finally {
      setSaving(false)
    }
  }

  if (!loaded) return <p className="text-sm text-stone-400">Loading...</p>

  return (
    <div className="space-y-2 rounded-2xl border border-stone-200/70 bg-white/80 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <div className="flex items-baseline justify-between">
        <h3 className="font-medium text-stone-800">Agent DNA</h3>
        {status && (
          <span className={`text-xs ${status.ok ? 'text-emerald-600' : 'text-rose-600'}`}>
            {status.message}
          </span>
        )}
      </div>
      <p className="text-xs text-stone-500">
        Writing style rules applied to every generated cover letter and outreach message.
      </p>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={20}
        spellCheck={false}
        className="w-full rounded-xl border border-stone-200/70 bg-white px-3 py-2 font-mono text-[13px] leading-relaxed focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
      />
      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={handleSave}
        disabled={saving}
        className="rounded-xl bg-stone-800 px-4 py-2 text-sm font-medium text-white shadow-sm transition-opacity disabled:opacity-30"
      >
        {saving ? 'Saving...' : 'Save'}
      </motion.button>
    </div>
  )
}
