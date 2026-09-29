import { Link } from 'react-router-dom'
import Logo from '../../components/Logo.jsx'

/**
 * Shared header for the public marketing pages: logo on the left, a plain
 * sign-in link on the right. Deliberately not AsyncApplyLayout -- that's
 * the authenticated shell with its own tab bar.
 */
export default function MarketingNav() {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
      <Link to="/welcome">
        <Logo textClassName="text-lg text-white" />
      </Link>
      <Link
        to="/login"
        className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-white/90 backdrop-blur-sm transition-colors hover:bg-white/10"
      >
        Sign in
      </Link>
    </header>
  )
}
