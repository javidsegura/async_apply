import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, Plus, X, Loader2 } from 'lucide-react'
import { getAsyncApplyProfile, updateAsyncApplyProfile, fillAsyncApplyProfileFromCv } from '../../api.js'
import { COUNTRIES, COUNTRY_BY_CODE } from './lib/countries.js'

const EMPTY_ENTRY = { heading: '', location: '', subheading: '', dates: '', bullets: [], text: null }

const CV_SECTIONS = [
  { key: 'education', label: 'Education', mode: 'bullets' },
  { key: 'experience', label: 'Experience', mode: 'bullets' },
  { key: 'projects', label: 'Projects', mode: 'bullets' },
  { key: 'awards', label: 'Awards', mode: 'text' },
  { key: 'activities', label: 'Activities', mode: 'bullets' },
]

/**
 * The candidate's whole profile as a real form: identity, job-search
 * targeting (the small part a CV can never state), and the CV content
 * itself. A CV upload can best-effort fill most of it -- see handleCvUpload.
 */
export default function ProfileForm() {
  const [profile, setProfile] = useState(null)
  const [saving, setSaving] = useState(false)
  const [filling, setFilling] = useState(false)
  const [status, setStatus] = useState(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    getAsyncApplyProfile().then(setProfile)
  }, [])

  function set(path, value) {
    setProfile((p) => {
      const next = structuredClone(p)
      let obj = next
      const keys = path.split('.')
      for (let i = 0; i < keys.length - 1; i++) obj = obj[keys[i]]
      obj[keys[keys.length - 1]] = value
      return next
    })
  }

  async function handleCvUpload(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    setFilling(true)
    setStatus(null)
    try {
      const extracted = await fillAsyncApplyProfileFromCv(file)
      setProfile((p) => mergeExtraction(p, extracted))
      setStatus({ ok: true, message: 'Filled from your CV. Review before saving -- nothing was invented, but check it over.' })
    } catch (err) {
      setStatus({ ok: false, message: err.message })
    } finally {
      setFilling(false)
    }
  }

  async function handleSave() {
    setSaving(true)
    setStatus(null)
    try {
      const saved = await updateAsyncApplyProfile(profile)
      setProfile(saved)
      setStatus({ ok: true, message: 'Saved.' })
    } catch (err) {
      setStatus({ ok: false, message: err.message })
    } finally {
      setSaving(false)
    }
  }

  if (!profile) return <p className="text-sm text-stone-400">Loading...</p>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-2xl border border-sky-200/60 bg-sky-50/50 px-5 py-3.5">
        <div>
          <h3 className="text-sm font-medium text-stone-800">Fill in as little as possible</h3>
          <p className="text-xs text-stone-500">Upload your CV and AI does its best. You review and fill in the rest.</p>
        </div>
        <input ref={fileInputRef} type="file" accept="application/pdf" className="hidden" onChange={handleCvUpload} />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={filling}
          className="flex items-center gap-1.5 rounded-xl bg-sky-600 px-3.5 py-2 text-xs font-medium text-white shadow-sm transition-opacity hover:bg-sky-700 disabled:opacity-60"
        >
          {filling ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
          {filling ? 'Reading your CV...' : 'Fill with AI'}
        </button>
      </div>

      <Section title="Identity">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Full name" required value={profile.candidate.full_name} onChange={(v) => set('candidate.full_name', v)} />
          <Field label="Location" value={profile.candidate.location} onChange={(v) => set('candidate.location', v)} placeholder="Madrid, Spain" />
          <Field label="Phone" value={profile.candidate.phone} onChange={(v) => set('candidate.phone', v)} />
          <Field label="Email" value={profile.candidate.email} onChange={(v) => set('candidate.email', v)} />
          <Field label="LinkedIn" value={profile.candidate.linkedin} onChange={(v) => set('candidate.linkedin', v)} />
          <Field label="GitHub" value={profile.candidate.github} onChange={(v) => set('candidate.github', v)} />
          <Field label="Portfolio" value={profile.candidate.portfolio_url} onChange={(v) => set('candidate.portfolio_url', v)} />
        </div>
      </Section>

      <Section title="Job search targeting" hint="Not on any CV -- only you know this.">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <CountryField
            label="Authorized to work in"
            values={profile.location.authorized_in}
            onChange={(v) => set('location.authorized_in', v)}
          />
          <ChipField
            label="Target roles"
            values={profile.target_roles}
            onChange={(v) => set('target_roles', v)}
            placeholder="Backend Engineer..."
          />
        </div>
        <label className="mt-3 flex items-center gap-2 text-xs text-stone-600">
          <input
            type="checkbox"
            checked={profile.location.needs_sponsorship}
            onChange={(e) => set('location.needs_sponsorship', e.target.checked)}
            className="rounded border-stone-300"
          />
          Would need visa sponsorship outside those countries
        </label>
        <Field
          label="Anything else for the CV's work-authorization line"
          value={profile.location.work_auth_note}
          onChange={(v) => set('location.work_auth_note', v)}
          placeholder="e.g. Eligible to sign an internship agreement via IE University"
          className="mt-3"
        />
        <Field
          label="House rules (optional)"
          value={profile.custom_house_rules}
          onChange={(v) => set('custom_house_rules', v)}
          placeholder="No crypto or gambling companies."
          textarea
          className="mt-3"
        />
      </Section>

      <Section title="CV content">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Languages" value={profile.cv.languages} onChange={(v) => set('cv.languages', v)} placeholder="Spanish (Native). English (Fluent)." />
          <ChipField label="Technologies" values={profile.cv.technologies} onChange={(v) => set('cv.technologies', v)} placeholder="Python, SQL..." />
        </div>
        <Field
          label="Summary (optional, used only for outreach)"
          value={profile.cv.summary}
          onChange={(v) => set('cv.summary', v)}
          textarea
          className="mt-3"
        />
      </Section>

      {CV_SECTIONS.map(({ key, label, mode }) => (
        <Section key={key} title={label}>
          <EntryList
            entries={profile.cv[key]}
            mode={mode}
            onChange={(entries) => set(`cv.${key}`, entries)}
          />
        </Section>
      ))}

      <div className="flex items-center gap-3 pb-4">
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
    </div>
  )
}

/**
 * Merge a CV extraction into the current form -- only into fields that are
 * still empty, so a deliberate "Fill with AI" click after manual edits can
 * never silently clobber something the user already typed.
 *
 * @param {object} profile
 * @param {object} extracted - ExtractedProfile from the backend.
 */
function mergeExtraction(profile, extracted) {
  const next = structuredClone(profile)
  const candidateMap = {
    full_name: 'full_name', location: 'location', phone: 'phone', email: 'email',
    linkedin: 'linkedin', github: 'github', portfolio_url: 'portfolio_url',
  }
  for (const [from, to] of Object.entries(candidateMap)) {
    if (!next.candidate[to] && extracted[from]) next.candidate[to] = extracted[from]
  }
  if (!next.cv.summary && extracted.summary) next.cv.summary = extracted.summary
  if (!next.cv.languages && extracted.languages) next.cv.languages = extracted.languages
  if (!next.cv.technologies?.length && extracted.technologies?.length) next.cv.technologies = extracted.technologies
  for (const key of ['education', 'experience', 'projects', 'awards', 'activities']) {
    if (!next.cv[key]?.length && extracted[key]?.length) next.cv[key] = extracted[key]
  }
  return next
}

function Section({ title, hint, children }) {
  return (
    <div className="rounded-2xl border border-stone-200/70 bg-white/80 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <div className="mb-3 flex items-baseline gap-2">
        <h3 className="font-medium text-stone-800">{title}</h3>
        {hint && <span className="text-[11px] text-stone-400">{hint}</span>}
      </div>
      {children}
    </div>
  )
}

function Field({ label, value, onChange, placeholder, required, textarea, className = '' }) {
  const Tag = textarea ? 'textarea' : 'input'
  return (
    <div className={className}>
      <label className="mb-1 block text-xs font-medium text-stone-600">
        {label}
        {required && <span className="text-rose-400"> *</span>}
      </label>
      <Tag
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={textarea ? 3 : undefined}
        className="w-full rounded-xl border border-stone-200/70 bg-white px-2.5 py-1.5 text-sm focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
      />
    </div>
  )
}

function ChipField({ label, values, onChange, placeholder }) {
  const [draft, setDraft] = useState('')

  function commit() {
    const v = draft.trim()
    if (v && !values.includes(v)) onChange([...values, v])
    setDraft('')
  }

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-stone-600">{label}</label>
      <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-stone-200/70 bg-white px-2 py-1.5">
        {values.map((v) => (
          <span key={v} className="flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 text-[11px] text-stone-600">
            {v}
            <button onClick={() => onChange(values.filter((x) => x !== v))}>
              <X size={10} />
            </button>
          </span>
        ))}
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') {
              e.preventDefault()
              commit()
            }
          }}
          onBlur={commit}
          placeholder={placeholder}
          className="min-w-[6rem] flex-1 border-none px-1 py-0.5 text-sm outline-none"
        />
      </div>
    </div>
  )
}

function CountryField({ label, values, onChange }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const boxRef = useRef(null)

  useEffect(() => {
    function onClickOutside(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const matches = query.trim()
    ? COUNTRIES.filter(
        (c) => c.name.toLowerCase().includes(query.trim().toLowerCase()) && !values.includes(c.code),
      ).slice(0, 8)
    : []

  function add(code) {
    if (!values.includes(code)) onChange([...values, code])
    setQuery('')
    setOpen(false)
  }

  return (
    <div ref={boxRef} className="relative">
      <label className="mb-1 block text-xs font-medium text-stone-600">{label}</label>
      <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-stone-200/70 bg-white px-2 py-1.5">
        {values.map((code) => (
          <span key={code} className="flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 text-[11px] text-stone-600">
            {COUNTRY_BY_CODE[code] || code}
            <button onClick={() => onChange(values.filter((x) => x !== code))}>
              <X size={10} />
            </button>
          </span>
        ))}
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          placeholder="Type a country name..."
          className="min-w-[8rem] flex-1 border-none px-1 py-0.5 text-sm outline-none"
        />
      </div>
      {open && matches.length > 0 && (
        <div className="absolute z-10 mt-1 w-full overflow-hidden rounded-xl border border-stone-200/70 bg-white shadow-lg">
          {matches.map((c) => (
            <button
              key={c.code}
              onClick={() => add(c.code)}
              className="block w-full px-3 py-1.5 text-left text-sm text-stone-700 hover:bg-sky-50"
            >
              {c.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function EntryList({ entries, mode, onChange }) {
  function update(i, patch) {
    onChange(entries.map((e, idx) => (idx === i ? { ...e, ...patch } : e)))
  }
  function remove(i) {
    onChange(entries.filter((_, idx) => idx !== i))
  }
  function add() {
    onChange([...entries, { ...EMPTY_ENTRY, text: mode === 'text' ? '' : null }])
  }

  return (
    <div className="space-y-3">
      {entries.map((entry, i) => (
        <div key={i} className="relative rounded-xl border border-stone-200/70 bg-stone-50/40 p-3">
          <button
            onClick={() => remove(i)}
            className="absolute right-2 top-2 rounded-full p-1 text-stone-300 hover:bg-stone-100 hover:text-stone-500"
          >
            <X size={13} />
          </button>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <MiniField label="Heading" value={entry.heading} onChange={(v) => update(i, { heading: v })} />
            <MiniField label="Location" value={entry.location} onChange={(v) => update(i, { location: v })} />
            {mode === 'bullets' && (
              <>
                <MiniField label="Subheading" value={entry.subheading} onChange={(v) => update(i, { subheading: v })} />
                <MiniField label="Dates" value={entry.dates} onChange={(v) => update(i, { dates: v })} />
              </>
            )}
          </div>
          {mode === 'text' ? (
            <MiniField
              label="Description"
              value={entry.text}
              onChange={(v) => update(i, { text: v })}
              textarea
              className="mt-2"
            />
          ) : (
            <MiniField
              label="Bullets (one per line)"
              value={(entry.bullets || []).join('\n')}
              onChange={(v) => update(i, { bullets: v.split('\n').filter(Boolean) })}
              textarea
              className="mt-2"
            />
          )}
        </div>
      ))}
      <button
        onClick={add}
        className="flex items-center gap-1 rounded-xl border border-dashed border-stone-300 px-3 py-1.5 text-xs font-medium text-stone-400 hover:border-stone-400 hover:text-stone-600"
      >
        <Plus size={12} /> Add
      </button>
    </div>
  )
}

function MiniField({ label, value, onChange, textarea, className = '' }) {
  const Tag = textarea ? 'textarea' : 'input'
  return (
    <div className={className}>
      <label className="mb-0.5 block text-[10px] font-medium uppercase tracking-wide text-stone-400">{label}</label>
      <Tag
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        rows={textarea ? 3 : undefined}
        className="w-full rounded-lg border border-stone-200/70 bg-white px-2 py-1 text-[13px] focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
      />
    </div>
  )
}
