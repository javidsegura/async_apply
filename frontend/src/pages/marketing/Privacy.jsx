import MarketingNav from './MarketingNav.jsx'
import MarketingFooter from './MarketingFooter.jsx'

export default function Privacy() {
  return (
    <div className="min-h-screen bg-[#05060a] text-white">
      <MarketingNav />
      <main className="mx-auto max-w-2xl px-6 pb-24 pt-8">
        <h1 className="text-3xl font-semibold tracking-tight">Privacy policy</h1>
        <p className="mt-2 text-sm text-white/40">Last updated 2026-09-28</p>

        <div className="mt-10 space-y-8 text-sm leading-relaxed text-white/70">
          <p>
            AsyncApply is a solo, early-stage project, not a company. This page explains what's
            collected and how it's used in plain terms -- there's no legal team behind it, just an
            honest account of what the app does.
          </p>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">What's collected</h2>
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Your email address, via Firebase authentication, to identify your account.</li>
              <li>Your CV and profile information, which you provide directly to build your applications.</li>
              <li>The job posting URLs or text you submit for the pipeline to process.</li>
              <li>Basic usage data (how many applications you've run) to manage costs and budgets.</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">How it's used</h2>
            <p>
              Your data is used only to run your own job-application pipeline: extracting job
              postings, scoring fit, and drafting documents and outreach on your behalf. Your CV and
              the job postings you submit are sent to the LLM providers (via OpenRouter) needed to
              actually do that work -- nothing is sent anywhere else.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">What's not done</h2>
            <p>
              Your data is not sold, not shared with advertisers, and not used to train any model
              beyond the ordinary processing needed to answer a single request. There is no ad
              network and no data broker involved anywhere in this app.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">Storage and deletion</h2>
            <p>
              Data is stored in a private database for as long as your account is active. If you'd
              like your data deleted, email the address below and it will be removed by hand -- there
              isn't a self-serve delete button yet.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-white">Contact</h2>
            <p>
              Questions about any of this: {' '}
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
