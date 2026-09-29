import MarketingNav from './MarketingNav.jsx'
import MarketingFooter from './MarketingFooter.jsx'

export default function Terms() {
  return (
    <div className="min-h-screen bg-[#05060a] text-white">
      <MarketingNav />
      <main className="mx-auto max-w-2xl px-6 pb-24 pt-8">
        <h1 className="text-3xl font-semibold tracking-tight">Terms of service</h1>
        <p className="mt-2 text-sm text-white/40">Last updated 2026-09-28</p>

        <div className="mt-10 space-y-8 text-sm leading-relaxed text-white/70">
          <p>
            AsyncApply is an early-stage, solo-built project offered on an as-is basis. By using it,
            you agree to the following.
          </p>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">The service</h2>
            <p>
              AsyncApply reads job postings, scores your fit against them, and drafts a CV, cover
              letter, and outreach message on your behalf. It's provided as-is, without warranty of
              any kind, and may change, break, or be discontinued without notice -- this is a
              nights-and-weekends project, not a funded company with an SLA.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">No guarantee of outcomes</h2>
            <p>
              AsyncApply does not guarantee interviews, offers, or any particular job-search outcome.
              It's a tool to save you time drafting applications, not a promise of results.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">Review before you send</h2>
            <p>
              Every CV, cover letter, and outreach message is a draft. You are responsible for
              reviewing generated content for accuracy before sending it to an employer or a
              recruiter -- treat it as a strong first pass, not a final copy.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">Billing</h2>
            <p>
              There is no automated payment processor yet. Billing for paid plans is handled
              manually, person to person (Zelle/PayPal), based on the plan you choose on the{' '}
              pricing page. Access can be adjusted or revoked at the founder's discretion if payment
              isn't kept current.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">Changes</h2>
            <p>
              These terms may be updated as the project evolves. Continued use after a change means
              you accept the updated terms.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">Contact</h2>
            <p>
              Questions: {' '}
              <a href="mailto:hello@asyncapply.dev" className="text-sky-300 underline underline-offset-2">
                hello@asyncapply.dev
              </a>
              .
            </p>
          </section>
        </div>
      </main>
      <MarketingFooter />
    </div>
  )
}
