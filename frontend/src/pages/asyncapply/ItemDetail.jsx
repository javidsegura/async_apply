import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Download, FileText, ExternalLink, ImagePlus, Timer, MapPin, ShieldCheck,
  GraduationCap, Building2, Gauge, Coins, ThumbsUp, ThumbsDown, Users,
  ChevronRight, ChevronDown,
} from 'lucide-react'
import { openAsyncApplyAsset, uploadAsyncApplyLogo, getAsyncApplyMe } from '../../api.js'
import { duration, countryFlag } from './lib/format.js'

export { duration }

// cost_usd/total_tokens are filtered out for non-admins in FactGrid below --
// "tokens spend should be admin only," regular users can't act on this
// figure anyway since only the admin sets budgets.
const FACTS = [
  { key: 'work_auth_tier', icon: ShieldCheck, label: 'Work auth', iconColor: 'text-indigo-500' },
  { key: 'min_years_required', icon: GraduationCap, label: 'Min years', iconColor: 'text-stone-400' },
  { key: 'company_type', icon: Building2, label: 'Type', iconColor: 'text-stone-400' },
  { key: 'legitimacy', icon: Gauge, label: 'Signal', iconColor: 'text-stone-400' },
  { key: 'cost_usd', icon: Coins, label: 'Cost', iconColor: 'text-emerald-500', fmt: (v) => `$${v.toFixed(4)}`, adminOnly: true },
  { key: 'total_tokens', icon: Coins, label: 'Tokens', iconColor: 'text-stone-400', fmt: (v) => v.toLocaleString(), adminOnly: true },
]

/**
 * Everything known about one application: the verdict, the grounded facts,
 * strengths and gaps, outreach drafts and the generated documents. Sections
 * that can get long start collapsed, each with its own reveal, so opening an
 * item never dumps a wall of text.
 *
 * @param {{item: object, onLogoUploaded?: () => void}} props
 */
export default function ItemDetail({ item, onLogoUploaded }) {
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    getAsyncApplyMe().then((me) => setIsAdmin(me.role === 'admin'))
  }, [])

  async function uploadLogo(e) {
    const file = e.target.files?.[0]
    if (!file || !item.company) return
    await uploadAsyncApplyLogo(item.company, file)
    onLogoUploaded?.()
  }

  const took = duration(item.started_at, item.ended_at)
  const canApply = item.url && !item.hard_stop_reason

  return (
    <div className="space-y-3.5">
      {item.verdict && (
        <p className="rounded-xl bg-gradient-to-br from-sky-50/80 to-violet-50/50 px-4 py-3 text-[13px] leading-relaxed text-stone-600">
          {item.verdict}
        </p>
      )}

      <FactGrid item={item} took={took} isAdmin={isAdmin} />

      {item.hard_stop_reason && (
        <p className="rounded-xl bg-amber-50/70 px-4 py-2.5 text-xs text-amber-800">
          <b className="font-semibold">Filtered out.</b> {item.hard_stop_reason}
        </p>
      )}
      {item.error && (
        <p className="rounded-xl bg-rose-50/70 px-4 py-2.5 text-xs text-rose-700">{item.error}</p>
      )}

      {(item.strengths?.length > 0 || item.gaps?.length > 0) && (
        <Reveal
          label="Strengths & gaps"
          icon={ThumbsUp}
          count={(item.strengths?.length || 0) + (item.gaps?.length || 0)}
          variant="accordion"
        >
          <div className="grid grid-cols-1 gap-4 pt-2 sm:grid-cols-2">
            <div>
              <div className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
                <ThumbsUp size={11} /> Strengths
              </div>
              <ul className="space-y-1.5 text-xs leading-relaxed text-stone-600">
                {item.strengths?.map((s, i) => (
                  <li key={i} className="flex gap-1.5"><span className="text-emerald-300">▸</span>{s}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold text-rose-500">
                <ThumbsDown size={11} /> Gaps
              </div>
              <ul className="space-y-1.5 text-xs leading-relaxed text-stone-600">
                {item.gaps?.map((g, i) => (
                  <li key={i} className="flex gap-1.5"><span className="text-rose-300">▸</span>{g}</li>
                ))}
              </ul>
            </div>
          </div>
        </Reveal>
      )}

      {item.contacts?.length > 0 && (
        <Reveal label="Outreach" icon={Users} count={item.contacts.length} variant="slide">
          <ul className="space-y-2 pt-2">
            {item.contacts.map((c, i) => (
              <li key={i} className="rounded-xl bg-stone-50/70 px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <a
                    href={c.contact_linkedin}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-medium text-sky-700 hover:underline"
                  >
                    {c.contact_name}
                  </a>
                  <span className="rounded-full bg-white px-1.5 py-0.5 text-[10px] text-stone-400">
                    {c.contact_type}
                  </span>
                  {c.fit_score != null && (
                    <span className="ml-auto text-[10px] text-stone-400">fit {c.fit_score.toFixed(1)}</span>
                  )}
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-stone-500">{c.message}</p>
              </li>
            ))}
          </ul>
        </Reveal>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {item.cv_pdf_path && (
          <Pill onOpen={() => openAsyncApplyAsset(item.id, 'cv')} icon={FileText}>CV</Pill>
        )}
        {item.cover_letter_pdf_path && (
          <Pill onOpen={() => openAsyncApplyAsset(item.id, 'cover-letter')} icon={Download}>
            Cover letter
          </Pill>
        )}
        {item.company && (
          <label className="flex cursor-pointer items-center gap-1.5 rounded-full border border-stone-200/80 px-3 py-1.5 text-[11px] font-medium text-stone-500 transition-colors hover:bg-stone-50">
            <ImagePlus size={12} /> Logo
            <input type="file" accept="image/*" onChange={uploadLogo} className="hidden" />
          </label>
        )}
      </div>

      {canApply && (
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-sky-600 to-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-transform hover:scale-[1.01] active:scale-[0.99]"
        >
          Apply on {item.company ? `${item.company}'s` : "the company's"} site
          <ExternalLink size={15} />
        </a>
      )}
    </div>
  )
}

/**
 * The item's key facts as a clean grid of cells -- label above, value
 * below, one icon per cell -- instead of a wrapping row of small pills
 * that crammed an icon, a label word and a value into one badge each.
 */
function FactGrid({ item, took, isAdmin }) {
  const cells = []
  if (item.location) {
    cells.push({
      key: 'location', icon: MapPin, label: 'Location', iconColor: 'text-sky-500',
      value: `${countryFlag(item.location)} ${item.location}`,
    })
  }
  for (const f of FACTS) {
    if (item[f.key] == null) continue
    if (f.adminOnly && !isAdmin) continue
    cells.push({ ...f, value: f.fmt ? f.fmt(item[f.key]) : item[f.key] })
  }
  if (took) cells.push({ key: 'took', icon: Timer, label: 'Took', iconColor: 'text-violet-500', value: took })

  if (!cells.length) return null

  return (
    <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-4">
      {cells.map((c) => (
        <FactCell key={c.key} {...c} />
      ))}
    </div>
  )
}

function FactCell({ icon: Icon, label, iconColor, value }) {
  return (
    <div className="min-w-0 rounded-xl bg-stone-50/70 px-2.5 py-2">
      <div className="flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide text-stone-400">
        <Icon size={11} className={iconColor} />
        {label}
      </div>
      <div className="mt-0.5 truncate text-[13px] font-medium text-stone-700">{value}</div>
    </div>
  )
}

function Reveal({ label, icon: Icon, count, variant, children }) {
  const [open, setOpen] = useState(false)
  const anim = {
    accordion: {
      initial: { height: 0, opacity: 0 },
      animate: { height: 'auto', opacity: 1 },
      exit: { height: 0, opacity: 0 },
      transition: { duration: 0.25, ease: 'easeInOut' },
    },
    slide: {
      initial: { opacity: 0, x: -10 },
      animate: { opacity: 1, x: 0 },
      exit: { opacity: 0, x: -10 },
      transition: { duration: 0.2 },
    },
  }[variant]

  return (
    <div className="rounded-xl border border-stone-100 bg-white/70">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3.5 py-2.5 text-left text-xs font-medium text-stone-600"
      >
        <Icon size={13} className="text-stone-300" />
        {label}
        <span className="rounded-full bg-stone-100 px-1.5 text-[10px] font-normal text-stone-400">{count}</span>
        <span className="flex-1" />
        {open ? <ChevronDown size={13} className="text-stone-300" /> : <ChevronRight size={13} className="text-stone-300" />}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div {...anim} className="overflow-hidden">
            <div className="px-3.5 pb-3.5">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Pill({ href, onOpen, icon: Icon, children, muted }) {
  const className = `flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-medium transition-colors ${
    muted ? 'text-stone-400 hover:bg-stone-50' : 'bg-sky-50/80 text-sky-700 hover:bg-sky-100'
  }`

  // onOpen: an authenticated asset, fetched by hand and opened as a blob URL
  // (a plain <a href> can't carry the auth header the endpoint now needs).
  // href: an ordinary external link, e.g. the original posting.
  if (onOpen) {
    return (
      <button onClick={onOpen} className={className}>
        <Icon size={12} />
        {children}
      </button>
    )
  }

  return (
    <a href={href} target="_blank" rel="noreferrer" className={className}>
      <Icon size={12} />
      {children}
    </a>
  )
}
