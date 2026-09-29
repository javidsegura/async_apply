import { Link } from 'react-router-dom'
import Logo from '../../components/Logo.jsx'

/**
 * Shared footer for the public marketing pages: wordmark, legal links,
 * and a note that this is a one-person project, not a company.
 */
export default function MarketingFooter() {
  return (
    <footer className="mx-auto w-full max-w-6xl border-t border-white/10 px-6 py-10">
      <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
        <Logo textClassName="text-sm text-white/70" markClassName="opacity-80" />
        <div className="flex items-center gap-6 text-sm text-white/50">
          <Link to="/privacy" className="hover:text-white/80">
            Privacy
          </Link>
          <Link to="/terms" className="hover:text-white/80">
            Terms
          </Link>
          <a href="mailto:hello@asyncapply.dev" className="hover:text-white/80">
            hello@asyncapply.dev
          </a>
        </div>
      </div>
    </footer>
  )
}
