import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, Plus, X, Loader2, ChevronDown } from 'lucide-react'
import { getAsyncApplyProfile, updateAsyncApplyProfile, fillAsyncApplyProfileFromCv } from '../../api.js'
import { COUNTRIES, COUNTRY_BY_CODE, DIAL_CODES } from './lib/countries.js'

const EMPTY_ENTRY = { heading: '', location: '', subheading: '', dates: '', bullets: [], text: null }

const CV_SECTIONS = [
  { key: 'education', label: 'Education', emoji: '🎓', mode: 'bullets', dateField: 'education' },
  { key: 'experience', label: 'Experience', emoji: '💼', mode: 'bullets' },
  { key: 'projects', label: 'Projects', emoji: '🚀', mode: 'bullets' },
  { key: 'awards', label: 'Awards', emoji: '🏆', mode: 'text' },
  { key: 'activities', label: 'Activities', emoji: '🤝', mode: 'bullets' },
]

const SUGGESTED_ROLES = [
  'Software Engineer', 'Backend Engineer', 'Frontend Engineer', 'Full Stack Engineer',
  'Data Scientist', 'Machine Learning Engineer', 'DevOps Engineer', 'Product Manager',
  'Data Engineer', 'Platform Engineer',
]

const SUGGESTED_TECHNOLOGIES = [
  'Python', 'JavaScript', 'TypeScript', 'React', 'SQL', 'Java', 'Docker', 'AWS', 'Git', 'Linux',
]

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]
const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 20 }, (_, i) => CURRENT_YEAR + 6 - i)

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
          <h3 className="text-sm font-medium text-stone-800">🪄 Fill in as little as possible</h3>
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

      <Section title="Identity" emoji="🪪">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Full name" required value={profile.candidate.full_name} onChange={(v) => set('candidate.full_name', v)} placeholder="Ada Lovelace" />
          <Field label="Location" value={profile.candidate.location} onChange={(v) => set('candidate.location', v)} placeholder="Madrid, Spain" />
          <PhoneField value={profile.candidate.phone} onChange={(v) => set('candidate.phone', v)} />
          <Field label="Email" value={profile.candidate.email} onChange={(v) => set('candidate.email', v)} placeholder="ada@example.com" />
          <Field label="LinkedIn" value={profile.candidate.linkedin} onChange={(v) => set('candidate.linkedin', v)} placeholder="linkedin.com/in/ada" />
          <Field label="GitHub" value={profile.candidate.github} onChange={(v) => set('candidate.github', v)} placeholder="github.com/ada" />
          <Field label="Portfolio" value={profile.candidate.portfolio_url} onChange={(v) => set('candidate.portfolio_url', v)} placeholder="ada.dev" />
        </div>
      </Section>

      <Section title="Job search targeting" emoji="🎯" hint="Not on any CV -- only you know this.">
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
            placeholder="Type your own..."
            suggestions={SUGGESTED_ROLES}
          />
        </div>
        <Field
          label="Anything else for the CV's work-authorization line (optional)"
          value={profile.location.work_auth_note}
          onChange={(v) => set('location.work_auth_note', v)}
          placeholder="e.g. Eligible to sign an internship agreement via IE University"
          className="mt-3"
        />
        <Field
          label="House rules (optional) -- write your own, in your own words"
          value={profile.custom_house_rules}
          onChange={(v) => set('custom_house_rules', v)}
          placeholder="e.g. No crypto or gambling companies. Nothing fully remote. Skip agencies."
          textarea
          className="mt-3"
        />
      </Section>

      <Section title="CV content" emoji="📝">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Languages" value={profile.cv.languages} onChange={(v) => set('cv.languages', v)} placeholder="Spanish (Native). English (Fluent)." />
          <ChipField
            label="Technologies"
            values={profile.cv.technologies}
            onChange={(v) => set('cv.technologies', v)}
            placeholder="Type your own..."
            suggestions={SUGGESTED_TECHNOLOGIES}
          />
        </div>
        <Field
          label="Summary (optional, used only for outreach) -- write it in your own words"
          value={profile.cv.summary}
          onChange={(v) => set('cv.summary', v)}
          placeholder="e.g. CS student who builds fast, well-tested backend systems and ships them."
          textarea
          className="mt-3"
        />
      </Section>

      {CV_SECTIONS.map(({ key, label, emoji, mode, dateField }) => (
        <Section key={key} title={label} emoji={emoji}>
          <EntryList
            entries={profile.cv[key]}
            mode={mode}
            dateField={dateField}
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

function Section({ title, emoji, hint, children }) {
  return (
    <div className="rounded-2xl border border-stone-200/70 bg-white/80 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <div className="mb-3 flex items-baseline gap-2">
        <h3 className="font-medium text-stone-800">
          {emoji && <span className="mr-1.5">{emoji}</span>}
          {title}
        </h3>
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
        className="w-full rounded-xl border border-stone-200/70 bg-white px-2.5 py-1.5 text-sm placeholder:text-stone-300 focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
      />
    </div>
  )
}

function ChipField({ label, values, onChange, placeholder, suggestions = [] }) {
  const [draft, setDraft] = useState('')

  function commit(value) {
    const v = (value ?? draft).trim()
    if (v && !values.includes(v)) onChange([...values, v])
    setDraft('')
  }

  const availableSuggestions = suggestions.filter((s) => !values.includes(s))

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
          onBlur={() => commit()}
          placeholder={placeholder}
          className="min-w-[6rem] flex-1 border-none px-1 py-0.5 text-sm placeholder:text-stone-300 outline-none"
        />
      </div>
      {availableSuggestions.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {availableSuggestions.map((s) => (
            <button
              key={s}
              onClick={() => commit(s)}
              className="flex items-center gap-0.5 rounded-full border border-dashed border-stone-200 px-2 py-0.5 text-[10px] text-stone-400 hover:border-sky-300 hover:text-sky-600"
            >
              <Plus size={9} /> {s}
            </button>
          ))}
        </div>
      )}
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
          className="min-w-[8rem] flex-1 border-none px-1 py-0.5 text-sm placeholder:text-stone-300 outline-none"
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

/**
 * A phone number as a dial-code picker (type-ahead by country name, same
 * pattern as CountryField) plus the local number -- combined into one
 * "+34 608 362 377" string for storage, so the schema stays a single string.
 */
function PhoneField({ value, onChange }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const boxRef = useRef(null)

  const dial = DIAL_CODES.find((d) => value?.startsWith(d.dial))?.dial || ''
  const rest = dial ? value.slice(dial.length).trim() : (value || '')

  useEffect(() => {
    function onClickOutside(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const matches = DIAL_CODES.filter((c) => c.name.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 8)

  function pickDial(newDial) {
    onChange(`${newDial} ${rest}`.trim())
    setQuery('')
    setOpen(false)
  }

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-stone-600">Phone</label>
      <div className="flex gap-1.5">
        <div ref={boxRef} className="relative">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex h-full items-center gap-1 rounded-xl border border-stone-200/70 bg-white px-2.5 py-1.5 text-sm text-stone-600 hover:border-stone-300"
          >
            {dial || 'Code'} <ChevronDown size={12} className="text-stone-400" />
          </button>
          {open && (
            <div className="absolute z-10 mt-1 w-56 overflow-hidden rounded-xl border border-stone-200/70 bg-white shadow-lg">
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search country..."
                className="w-full border-b border-stone-100 px-3 py-1.5 text-sm placeholder:text-stone-300 outline-none"
              />
              <div className="max-h-48 overflow-y-auto">
                {matches.map((c) => (
                  <button
                    key={c.code}
                    onClick={() => pickDial(c.dial)}
                    className="flex w-full items-center justify-between px-3 py-1.5 text-left text-sm text-stone-700 hover:bg-sky-50"
                  >
                    <span className="truncate">{c.name}</span>
                    <span className="text-stone-400">{c.dial}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
        <input
          value={rest}
          onChange={(e) => onChange(`${dial} ${e.target.value}`.trim())}
          placeholder="608 362 377"
          className="w-full min-w-0 flex-1 rounded-xl border border-stone-200/70 bg-white px-2.5 py-1.5 text-sm placeholder:text-stone-300 focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
        />
      </div>
    </div>
  )
}

/**
 * Parse an education `dates` string back into {status, month, year} so the
 * toggle+dropdowns reflect whatever was already there (typed by hand or
 * filled by the CV extraction), best effort -- an unparseable string just
 * starts the picker blank rather than blocking on it.
 */
function parseEducationDate(value) {
  const text = value || ''
  const status = /expected/i.test(text) ? 'Expected' : 'Graduated'
  const month = MONTHS.find((m) => text.includes(m)) || ''
  const yearMatch = text.match(/\b(19|20)\d{2}\b/)
  return { status, month, year: yearMatch ? yearMatch[0] : '' }
}

function EducationDateField({ value, onChange }) {
  const { status, month, year } = parseEducationDate(value)

  function commit(nextStatus, nextMonth, nextYear) {
    const datePart = [nextMonth, nextYear].filter(Boolean).join(' ')
    onChange(datePart ? `${nextStatus}: ${datePart}` : nextStatus)
  }

  return (
    <div>
      <label className="mb-0.5 block text-[10px] font-medium uppercase tracking-wide text-stone-400">Dates</label>
      <div className="flex flex-wrap gap-1.5">
        <div className="flex overflow-hidden rounded-lg border border-stone-200/70">
          {['Graduated', 'Expected'].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => commit(s, month, year)}
              className={`px-2 py-1 text-[11px] font-medium transition-colors ${
                status === s ? 'bg-stone-800 text-white' : 'bg-white text-stone-500 hover:bg-stone-50'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <select
          value={month}
          onChange={(e) => commit(status, e.target.value, year)}
          className="rounded-lg border border-stone-200/70 bg-white px-1.5 py-1 text-[13px] text-stone-600"
        >
          <option value="">Month</option>
          {MONTHS.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select
          value={year}
          onChange={(e) => commit(status, month, e.target.value)}
          className="rounded-lg border border-stone-200/70 bg-white px-1.5 py-1 text-[13px] text-stone-600"
        >
          <option value="">Year</option>
          {YEARS.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>
    </div>
  )
}

function EntryList({ entries, mode, dateField, onChange }) {
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
                {dateField === 'education' ? (
                  <EducationDateField value={entry.dates} onChange={(v) => update(i, { dates: v })} />
                ) : (
                  <MiniField label="Dates" value={entry.dates} onChange={(v) => update(i, { dates: v })} />
                )}
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
