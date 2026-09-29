import { useState } from 'react'
import { Check, Loader2 } from 'lucide-react'
import MarketingNav from './MarketingNav.jsx'
import MarketingFooter from './MarketingFooter.jsx'
import { submitPricingLead } from '../../api.js'

const PLANS = [
  {
    id: 'trial',
    name: 'Free trial',
    price: '$0',
    period: '',
    tagline: 'Try the full pipeline on a handful of postings',
    features: ['5 job applications', 'Full fit scoring + hard-stop checks', 'CV + cover letter drafts'],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$15',
    period: '/mo',
    tagline: 'For an active job search',
    features: [
      'Unlimited job applications',
      'Contact discovery + outreach drafts',
      'Priority processing',
      'Direct line to the founder for feedback',
    ],
    highlighted: true,
  },
  {
    id: 'teams',
    name: 'Small group',
    price: '$40',
    period: '/mo',
    tagline: 'A few friends sharing one workspace',
    features: ['Everything in Pro', 'Up to 5 people', 'Shared usage budget'],
  },
]

export default function Pricing() {
  const [selectedPlan, setSelectedPlan] = useState(null)
  const [form, setForm] = useState({ name: '', email: '' })
  const [status, setStatus] = useState('idle') // idle | submitting | done | error

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus('submitting')
    try {
      await submitPricingLead({ name: form.name, email: form.email, plan: selectedPlan.id })
      setStatus('done')
    } catch {
      setStatus('error')
    }
  }

  return (
    <div className="min-h-screen bg-[#05060a] text-white">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-indigo-600/25 blur-[120px]" />
      </div>

      <div className="relative">
        <MarketingNav />

        <section className="mx-auto max-w-4xl px-6 pb-12 pt-10 text-center">
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Simple pricing</h1>
          <p className="mx-auto mt-4 max-w-xl text-white/60">
            No payment processor yet -- this is a solo project, so plans are handled personally.
            Pick one below and I'll follow up directly.
          </p>
        </section>

        <section className="mx-auto max-w-6xl px-6 pb-16">
          <div className="grid gap-6 sm:grid-cols-3">
            {PLANS.map((plan) => (
              <div
                key={plan.id}
                className={`flex flex-col rounded-2xl border p-6 ${
                  plan.highlighted
                    ? 'border-sky-400/40 bg-gradient-to-b from-sky-400/10 to-indigo-500/5'
                    : 'border-white/10 bg-white/[0.03]'
                }`}
              >
                {plan.highlighted && (
                  <div className="mb-3 inline-flex w-fit items-center rounded-full bg-sky-400/20 px-2.5 py-0.5 text-[11px] font-semibold text-sky-300">
                    Most popular
                  </div>
                )}
                <h3 className="text-lg font-semibold text-white">{plan.name}</h3>
                <p className="mt-1 text-sm text-white/50">{plan.tagline}</p>
                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-3xl font-semibold text-white">{plan.price}</span>
                  <span className="text-sm text-white/40">{plan.period}</span>
                </div>
                <ul className="mt-6 flex-1 space-y-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-white/65">
                      <Check size={15} className="mt-0.5 shrink-0 text-sky-400" />
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => {
                    setSelectedPlan(plan)
                    setStatus('idle')
                  }}
                  className={`mt-6 rounded-full px-4 py-2.5 text-sm font-semibold transition-colors ${
                    plan.highlighted
                      ? 'bg-gradient-to-r from-sky-400 to-indigo-500 text-white hover:opacity-90'
                      : 'border border-white/15 text-white/85 hover:bg-white/5'
                  }`}
                >
                  Choose {plan.name}
                </button>
              </div>
            ))}
          </div>
        </section>

        {selectedPlan && (
          <section className="mx-auto max-w-md px-6 pb-24">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              {status === 'done' ? (
                <div className="py-4 text-center">
                  <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-400/15">
                    <Check size={18} className="text-emerald-300" />
                  </div>
                  <h3 className="font-semibold text-white">Thanks, {form.name.split(' ')[0] || 'there'}!</h3>
                  <p className="mt-2 text-sm leading-relaxed text-white/60">
                    I'll reach out personally to sort out payment (Zelle/PayPal) for the{' '}
                    <span className="text-white/85">{selectedPlan.name}</span> plan -- this isn't
                    automated yet, and that's on purpose: early access here means a real person on the
                    other end.
                  </p>
                </div>
              ) : (
                <form onSubmit={handleSubmit}>
                  <h3 className="font-semibold text-white">
                    You picked <span className="text-sky-300">{selectedPlan.name}</span>
                  </h3>
                  <p className="mt-1 text-sm text-white/50">
                    Leave your details and I'll set you up by hand.
                  </p>
                  <div className="mt-5 space-y-3">
                    <input
                      required
                      type="text"
                      placeholder="Your name"
                      value={form.name}
                      onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                      className="w-full rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-white/30 outline-none focus:border-sky-400/50"
                    />
                    <input
                      required
                      type="email"
                      placeholder="you@email.com"
                      value={form.email}
                      onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                      className="w-full rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-white/30 outline-none focus:border-sky-400/50"
                    />
                  </div>
                  {status === 'error' && (
                    <p className="mt-3 text-xs text-rose-400">
                      Something went wrong submitting that. Try again in a moment.
                    </p>
                  )}
                  <button
                    type="submit"
                    disabled={status === 'submitting'}
                    className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-sky-400 to-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
                  >
                    {status === 'submitting' && <Loader2 size={14} className="animate-spin" />}
                    Request access
                  </button>
                </form>
              )}
            </div>
          </section>
        )}

        <MarketingFooter />
      </div>
    </div>
  )
}
