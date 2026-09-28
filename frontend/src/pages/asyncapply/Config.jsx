import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { FileText, Mic, MessageSquare, SlidersHorizontal, Check } from 'lucide-react'
import {
  getAsyncApplyProfile,
  updateAsyncApplyProfile,
  getAsyncApplyVoiceDna,
  updateAsyncApplyVoiceDna,
  getAsyncApplyModes,
  getAsyncApplyMode,
  updateAsyncApplyMode,
  getAsyncApplySettings,
  updateAsyncApplySettings,
  getAsyncApplyAvailableModels,
} from '../../api.js'

const SECTIONS = [
  { key: 'profile', label: 'Profile', icon: FileText },
  { key: 'voice_dna', label: 'Voice DNA', icon: Mic },
  { key: 'modes', label: 'Modes', icon: MessageSquare },
  { key: 'settings', label: 'Settings', icon: SlidersHorizontal },
]

/**
 * Editors for everything that shapes the pipeline's behaviour: identity and
 * CV (profile.yml), writing voice, the per-stage prompts, and the models and
 * tuning knobs the pipeline actually runs with.
 */
export default function Config() {
  const [section, setSection] = useState('profile')

  return (
    <div className="space-y-4">
      <div className="flex gap-1 rounded-xl bg-stone-100/70 p-1">
        {SECTIONS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setSection(key)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
              section === key ? 'bg-white text-stone-700 shadow-sm' : 'text-stone-400 hover:text-stone-600'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {section === 'profile' && (
        <TextFileEditor
          title="profile.yml"
          hint="Identity, CV, and targeting rules. Must stay valid YAML or the save is rejected before it reaches disk."
          load={() => getAsyncApplyProfile().then((r) => r.content)}
          save={updateAsyncApplyProfile}
        />
      )}
      {section === 'voice_dna' && (
        <TextFileEditor
          title="voice_dna.md"
          hint="Writing style rules applied to every generated cover letter and message."
          load={() => getAsyncApplyVoiceDna().then((r) => r.content)}
          save={updateAsyncApplyVoiceDna}
        />
      )}
      {section === 'modes' && <ModesEditor />}
      {section === 'settings' && <PipelineSettings />}
    </div>
  )
}

function TextFileEditor({ title, hint, load, save }) {
  const [content, setContent] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    setLoaded(false)
    load().then((c) => {
      setContent(c)
      setLoaded(true)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title])

  async function handleSave() {
    setSaving(true)
    setStatus(null)
    try {
      await save(content)
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
        <h3 className="font-medium text-stone-800">{title}</h3>
        {status && (
          <span className={`text-xs ${status.ok ? 'text-emerald-600' : 'text-rose-600'}`}>
            {status.message}
          </span>
        )}
      </div>
      <p className="text-xs text-stone-500">{hint}</p>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={20}
        spellCheck={false}
        className="w-full rounded-xl border border-stone-200/70 bg-white px-3 py-2 font-mono text-[13px] leading-relaxed focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
      />
      <SaveButton onClick={handleSave} saving={saving} />
    </div>
  )
}

function ModesEditor() {
  const [names, setNames] = useState([])
  const [active, setActive] = useState(null)

  useEffect(() => {
    getAsyncApplyModes().then((list) => {
      setNames(list)
      setActive(list[0] ?? null)
    })
  }, [])

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {names.map((name) => (
          <button
            key={name}
            onClick={() => setActive(name)}
            className={`rounded-lg px-3 py-1.5 font-mono text-[11px] transition-colors ${
              active === name ? 'bg-stone-800 text-white' : 'bg-stone-100/70 text-stone-500 hover:bg-stone-200/70'
            }`}
          >
            {name}.md
          </button>
        ))}
      </div>
      {active && (
        <TextFileEditor
          key={active}
          title={`modes/${active}.md`}
          hint="The instructions this stage receives. Prose and format changes only -- fields it must answer with come from the code's schema, not this file."
          load={() => getAsyncApplyMode(active).then((r) => r.content)}
          save={(content) => updateAsyncApplyMode(active, content)}
        />
      )}
    </div>
  )
}

const STAGE_LABELS = {
  model_extract_jd: 'Extract JD',
  model_evaluate_job: 'Evaluate job',
  model_find_contact: 'Find contact',
}

const NUMBER_FIELDS = [
  { key: 'parallelism', label: 'Parallelism', hint: 'Items processed at once per batch.' },
  { key: 'max_attempts', label: 'Max attempts', hint: 'Retries per stage before it fails.' },
  { key: 'stage_timeout', label: 'Stage timeout (s)', hint: 'Seconds before one model call is abandoned.' },
  { key: 'fetch_timeout', label: 'Fetch timeout (s)', hint: 'Seconds a page fetch may take.' },
  { key: 'cv_max_pages', label: 'CV max pages', hint: 'The CV is trimmed until it fits this many pages.' },
]

function PipelineSettings() {
  const [settings, setSettings] = useState(null)
  const [models, setModels] = useState([])
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    Promise.all([getAsyncApplySettings(), getAsyncApplyAvailableModels()]).then(([s, m]) => {
      setSettings(s)
      setModels(m)
    })
  }, [])

  function update(key, value) {
    setSettings((s) => ({ ...s, [key]: value }))
  }

  async function handleSave() {
    setSaving(true)
    setStatus(null)
    try {
      const saved = await updateAsyncApplySettings(settings)
      setSettings(saved)
      setStatus({ ok: true, message: 'Saved. Takes effect on the next batch, no restart needed.' })
    } catch (err) {
      setStatus({ ok: false, message: err.message })
    } finally {
      setSaving(false)
    }
  }

  if (!settings) return <p className="text-sm text-stone-400">Loading...</p>

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-stone-200/70 bg-white/80 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <h3 className="mb-1 font-medium text-stone-800">Models per stage</h3>
        <p className="mb-3 text-xs text-stone-500">
          A curated set: each option is verified to support tool calls, strict JSON schema and
          OpenRouter's require_parameters routing, which the pipeline depends on.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {Object.keys(STAGE_LABELS).map((field) => (
            <div key={field}>
              <label className="mb-1 block text-xs font-medium text-stone-600">{STAGE_LABELS[field]}</label>
              <div className="flex flex-wrap gap-1.5">
                {models.map((model) => (
                  <button
                    key={model}
                    onClick={() => update(field, model)}
                    className={`flex items-center gap-1 rounded-full border px-2.5 py-1 font-mono text-[11px] transition-colors ${
                      settings[field] === model
                        ? 'border-sky-200 bg-sky-50 text-sky-700'
                        : 'border-stone-200/70 text-stone-400 hover:border-stone-300 hover:text-stone-600'
                    }`}
                  >
                    {settings[field] === model && <Check size={11} />}
                    {model.split('/')[1] || model}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-stone-200/70 bg-white/80 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <h3 className="mb-3 font-medium text-stone-800">Tuning</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {NUMBER_FIELDS.map(({ key, label, hint }) => (
            <div key={key}>
              <label className="mb-1 block text-xs font-medium text-stone-600">{label}</label>
              <input
                type="number"
                value={settings[key]}
                onChange={(e) => update(key, Number(e.target.value))}
                className="w-full rounded-xl border border-stone-200/70 bg-white px-2.5 py-1.5 text-sm focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
              />
              <p className="mt-0.5 text-[11px] text-stone-400">{hint}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <SaveButton onClick={handleSave} saving={saving} />
        {status && (
          <span className={`text-xs ${status.ok ? 'text-emerald-600' : 'text-rose-600'}`}>{status.message}</span>
        )}
      </div>
    </div>
  )
}

function SaveButton({ onClick, saving }) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      disabled={saving}
      className="rounded-xl bg-stone-800 px-4 py-2 text-sm font-medium text-white shadow-sm transition-opacity disabled:opacity-30"
    >
      {saving ? 'Saving...' : 'Save'}
    </motion.button>
  )
}
