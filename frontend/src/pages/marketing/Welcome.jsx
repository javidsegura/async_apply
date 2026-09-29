import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileSearch, Target, UserSearch, ArrowRight, Layers, Gauge, MousePointerClick } from 'lucide-react'
import MarketingNav from './MarketingNav.jsx'
import MarketingFooter from './MarketingFooter.jsx'

const VALUE_PROPS = [
  {
    icon: Layers,
    title: '10x the volume',
    body: 'Run dozens of postings through the pipeline at once instead of writing one application at a time.',
  },
  {
    icon: Target,
    title: 'Better ATS matching',
    body: "Technologies and project picks are reordered per posting, so the keywords an ATS actually scans for come first -- not a static CV pasted everywhere.",
  },
  {
    icon: Gauge,
    title: 'Parallel and fast',
    body: 'Postings are evaluated concurrently, not one after another -- a whole batch finishes in the time one used to take by hand.',
  },
  {
    icon: MousePointerClick,
    title: 'Minimal input',
    body: 'Drop in a link. The agent reads it, scores it, and writes the documents -- you review, you don\'t draft.',
  },
]

const STEPS = [
  {
    icon: FileSearch,
    title: 'Drop in a posting',
    body:
      'Paste a job URL or the raw text. The agent fetches and reads the actual posting -- not a summary, not a guess.',
  },
  {
    icon: Target,
    title: 'Real fit, not a vibe check',
    body:
      "Every score comes with a quote from the posting behind it. Work authorization and clearance requirements are checked against the JD's own words, so a hard stop is never the model just asserting one.",
  },
  {
    icon: FileSearch,
    title: 'A CV and cover letter grounded in your profile',
    body:
      'Drafted from your real background against this specific posting -- nothing invented, nothing generic.',
  },
  {
    icon: UserSearch,
    title: 'A contact worth messaging',
    body:
      'The agent searches for a real recruiter or engineering manager at the company and drafts outreach with its reasoning for why that person, not a form-letter blast.',
  },
]

export default function Welcome() {
  return (
    <div className="min-h-screen bg-[#05060a] text-white">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-indigo-600/25 blur-[120px]" />
        <div className="absolute top-1/3 right-0 h-[28rem] w-[28rem] rounded-full bg-sky-500/15 blur-[120px]" />
      </div>

      <div className="relative">
        <MarketingNav />

        {/* Hero */}
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-24 pt-16 sm:pt-24 lg:grid-cols-[1.1fr_0.9fr] lg:gap-8">
          <div className="text-center lg:text-left">
            <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium text-white/60 lg:mx-0">
              Built for the AI-agent era of job hunting
            </div>
            <h1 className="text-4xl font-semibold tracking-tight sm:text-6xl">
              The AI agent that actually{' '}
              <span className="bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">
                applies for you
              </span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-white/60 lg:mx-0">
              Not another cover-letter generator that free-associates off a job title. AsyncApply reads
              the actual posting, scores your real fit against it, and drafts a tailored CV, cover
              letter, and recruiter outreach -- grounded in your profile, not fabricated.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row lg:justify-start">
              <Link
                to="/login"
                className="flex items-center gap-2 rounded-full bg-gradient-to-r from-sky-400 to-indigo-500 px-7 py-3.5 text-base font-semibold text-white shadow-lg shadow-indigo-500/25 transition-transform hover:scale-[1.02]"
              >
                Start applying <ArrowRight size={18} />
              </Link>
              <a
                href="#how-it-works"
                className="rounded-full border border-white/15 px-7 py-3.5 text-base font-medium text-white/80 transition-colors hover:bg-white/5"
              >
                See how it works
              </a>
            </div>
          </div>
          <HeroObject />
        </section>

        {/* Value */}
        <section className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="text-center text-sm font-semibold uppercase tracking-widest text-white/40">
            What you actually get
          </h2>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {VALUE_PROPS.map((v) => (
              <div
                key={v.title}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-sm"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400/20 to-sky-500/20">
                  <v.icon size={18} className="text-emerald-300" />
                </div>
                <h3 className="mb-2 text-base font-semibold text-white">{v.title}</h3>
                <p className="text-sm leading-relaxed text-white/55">{v.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="text-center text-sm font-semibold uppercase tracking-widest text-white/40">
            How it works
          </h2>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, i) => (
              <div
                key={step.title}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-sm"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-sky-400/20 to-indigo-500/20">
                  <step.icon size={18} className="text-sky-300" />
                </div>
                <div className="mb-1 text-xs font-semibold text-white/30">Step {i + 1}</div>
                <h3 className="mb-2 text-base font-semibold text-white">{step.title}</h3>
                <p className="text-sm leading-relaxed text-white/55">{step.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Differentiation */}
        <section className="mx-auto max-w-5xl px-6 py-20">
          <h2 className="text-center text-3xl font-semibold tracking-tight sm:text-4xl">
            Not "generate a cover letter." <br className="hidden sm:block" />
            An agent that reads before it writes.
          </h2>
          <div className="mt-12 grid gap-6 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <h3 className="mb-2 font-semibold text-white">JD-grounded scoring</h3>
              <p className="text-sm leading-relaxed text-white/55">
                Fit scores, strengths, and gaps are tied to quotes lifted straight from the posting --
                not a model's paraphrase of what it thinks a job like this usually wants.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <h3 className="mb-2 font-semibold text-white">Hard stops you can trust</h3>
              <p className="text-sm leading-relaxed text-white/55">
                Work-authorization and clearance requirements are verified against the posting's own
                wording in code, not left to the model to remember. If it can't quote it, it can't
                disqualify you on it.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <h3 className="mb-2 font-semibold text-white">Real contact discovery</h3>
              <p className="text-sm leading-relaxed text-white/55">
                Finds an actual recruiter or engineering manager at the company and explains why they
                were picked -- not "reach out to someone on LinkedIn."
              </p>
            </div>
          </div>
        </section>

        {/* STEM framing */}
        <section className="mx-auto max-w-4xl px-6 py-20 text-center">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Built for technical job seekers
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-white/55">
            AsyncApply started as a personal tool for one engineering student's own job search. It
            understands technical roles, CVs full of stacks and systems instead of buzzwords, and the
            unglamorous reality of applying to dozens of postings a week.
          </p>
        </section>

        {/* Final CTA */}
        <section className="mx-auto max-w-4xl px-6 py-24 text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Stop rewriting the same cover letter
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-white/55">
            Drop in a posting and see what the agent comes back with.
          </p>
          <Link
            to="/login"
            className="mt-8 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-sky-400 to-indigo-500 px-7 py-3.5 text-base font-semibold text-white shadow-lg shadow-indigo-500/25 transition-transform hover:scale-[1.02]"
          >
            Start applying <ArrowRight size={18} />
          </Link>
        </section>

        <MarketingFooter />
      </div>
    </div>
  )
}

/**
 * Abstract floating geometric mark: three offset, gradient-filled planes in
 * a perspective container, each rotating on its own axis and orbit -- pure
 * CSS 3D transforms via framer-motion, no rendering library. Purely
 * decorative, so it's hidden on small screens rather than fighting the
 * hero text for space.
 */
function HeroObject() {
  return (
    <div
      className="relative hidden h-80 w-full items-center justify-center lg:flex"
      style={{ perspective: '1200px' }}
    >
      <motion.div
        className="absolute h-56 w-56 rounded-[2rem]"
        style={{
          background: 'linear-gradient(135deg, rgba(56,189,248,0.55), rgba(99,102,241,0.35))',
          boxShadow: '0 30px 80px -20px rgba(56,189,248,0.35)',
        }}
        animate={{ rotateX: [15, 45, 15], rotateY: [0, 360], y: [0, -14, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute h-40 w-40 rounded-[1.75rem] border border-white/20"
        style={{
          background: 'linear-gradient(135deg, rgba(129,140,248,0.5), rgba(56,189,248,0.15))',
        }}
        animate={{ rotateX: [-20, 20, -20], rotateY: [360, 0], x: [0, 18, 0] }}
        transition={{ duration: 11, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute h-24 w-24 rounded-2xl bg-white/10 backdrop-blur-sm"
        style={{ border: '1px solid rgba(255,255,255,0.25)' }}
        animate={{ rotateZ: [0, 360], rotateX: [10, -10, 10] }}
        transition={{ duration: 9, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  )
}
