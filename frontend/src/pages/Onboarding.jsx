import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Sparkles, Check } from 'lucide-react'
import { completeAsyncApplyOnboarding } from '../api.js'

const FIELDS_OF_STUDY = ['Computer Science', 'Data Science', 'Business', 'Engineering', 'Other']
const TARGET_AREAS = ['Software Engineering', 'Data / ML', 'Product', 'Design', 'Other']
const REFERRAL_SOURCES = ['Friend', 'LinkedIn', 'Twitter / X', 'Other']

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 10 }, (_, i) => CURRENT_YEAR + 3 - i)

/**
 * A short, one-time screen right after first sign-in: who this person is,
 * for the admin usage panel -- not the pipeline, so nothing here blocks or
 * even requires filling anything in. Every field is optional, and "Skip
 * for now" is always right there next to "Continue."
 */
export default function Onboarding() {
  const navigate = useNavigate()
  const [school, setSchool] = useState('')
  const [fieldOfStudy, setFieldOfStudy] = useState('')
  const [gradYear, setGradYear] = useState('')
  const [targetArea, setTargetArea] = useState('')
  const [referralSource, setReferralSource] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(fields) {
    setBusy(true)
    try {
      await completeAsyncApplyOnboarding(fields)
      navigate('/', { replace: true })
    } finally {
      setBusy(false)
    }
  }

  function handleContinue() {
    submit({
      school: school || undefined,
      field_of_study: fieldOfStudy || undefined,
      grad_year: gradYear ? Number(gradYear) : undefined,
      target_roles: targetArea || undefined,
      referral_source: referralSource || undefined,
    })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-stone-50 via-white to-stone-50/50 px-6 py-10">
      <div className="w-full max-w-lg rounded-2xl border border-stone-200/70 bg-white/80 p-8 shadow-sm backdrop-blur-sm">
        <div className="mb-1 flex items-center gap-2">
          <Sparkles size={18} className="text-sky-500" />
          <h1 className="text-lg font-semibold tracking-tight text-stone-800">A couple quick things</h1>
        </div>
        <p className="mb-6 text-sm text-stone-400">
          Nothing here is required. It just helps us understand who's using this.
        </p>

        <div className="space-y-5">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-stone-600">School</label>
            <input
              value={school}
              onChange={(e) => setSchool(e.target.value)}
              placeholder="IE University"
              className="w-full rounded-xl border border-stone-200/70 bg-white px-3 py-2 text-sm placeholder:text-stone-300 focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
            />
          </div>

          <PillGroup
            label="Field of study"
            options={FIELDS_OF_STUDY}
            value={fieldOfStudy}
            onChange={setFieldOfStudy}
            allowCustom
          />

          <div>
            <label className="mb-1.5 block text-xs font-medium text-stone-600">Graduation year</label>
            <div className="flex flex-wrap gap-1.5">
              {YEARS.map((y) => (
                <PillButton key={y} selected={gradYear === String(y)} onClick={() => setGradYear(String(y))}>
                  {y}
                </PillButton>
              ))}
            </div>
          </div>

          <PillGroup
            label="What are you job-hunting for?"
            options={TARGET_AREAS}
            value={targetArea}
            onChange={setTargetArea}
            allowCustom
          />

          <PillGroup
            label="How'd you hear about this?"
            options={REFERRAL_SOURCES}
            value={referralSource}
            onChange={setReferralSource}
            allowCustom
          />
        </div>

        <div className="mt-7 flex items-center gap-3">
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={handleContinue}
            disabled={busy}
            className="rounded-xl bg-stone-800 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-opacity disabled:opacity-40"
          >
            {busy ? 'Saving...' : 'Continue'}
          </motion.button>
          <button
            onClick={() => submit({})}
            disabled={busy}
            className="text-sm font-medium text-stone-400 hover:text-stone-600 disabled:opacity-40"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  )
}

function PillGroup({ label, options, value, onChange, allowCustom }) {
  const [customOpen, setCustomOpen] = useState(false)
  const isCustomValue = value && !options.includes(value)

  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-stone-600">{label}</label>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt) => (
          <PillButton
            key={opt}
            selected={value === opt || (opt === 'Other' && (isCustomValue || customOpen))}
            onClick={() => {
              if (opt === 'Other' && allowCustom) {
                setCustomOpen(true)
                onChange('')
              } else {
                setCustomOpen(false)
                onChange(opt)
              }
            }}
          >
            {opt}
          </PillButton>
        ))}
      </div>
      {(customOpen || isCustomValue) && (
        <input
          autoFocus
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Type your own..."
          className="mt-1.5 w-full rounded-xl border border-stone-200/70 bg-white px-3 py-1.5 text-sm placeholder:text-stone-300 focus:border-sky-200 focus:outline-none focus:ring-2 focus:ring-sky-100"
        />
      )}
    </div>
  )
}

function PillButton({ selected, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors ${
        selected
          ? 'border-sky-200 bg-sky-50 text-sky-700'
          : 'border-stone-200/70 text-stone-400 hover:border-stone-300 hover:text-stone-600'
      }`}
    >
      {selected && <Check size={11} />}
      {children}
    </button>
  )
}
