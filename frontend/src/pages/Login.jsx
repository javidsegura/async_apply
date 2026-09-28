import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'

/**
 * The only door in: Google sign-in via Firebase. Email/password can be
 * added the same way later if it's ever needed, but Google covers this
 * app's actual first users.
 */
export default function Login() {
  const { user, loading, signInWithGoogle } = useAuth()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (!loading && user) return <Navigate to="/" replace />

  const handleSignIn = async () => {
    setError('')
    setBusy(true)
    try {
      await signInWithGoogle()
    } catch {
      setError('Sign-in failed. Try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-stone-50 via-white to-stone-50/50 px-6">
      <div className="w-full max-w-sm rounded-2xl border border-stone-200/70 bg-white/80 p-8 text-center shadow-sm backdrop-blur-sm">
        <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-sky-100 to-sky-50">
          <Sparkles size={18} className="text-stone-600" strokeWidth={2} />
        </div>
        <h1 className="text-lg font-semibold tracking-tight text-stone-800">AsyncApply</h1>
        <p className="mt-1 text-sm text-stone-400">
          An agent that reads the job before it writes the letter.
        </p>

        <button
          onClick={handleSignIn}
          disabled={busy}
          className="mt-6 flex w-full items-center justify-center gap-2.5 rounded-xl border border-stone-200 bg-white px-4 py-2.5 text-sm font-medium text-stone-700 shadow-sm transition-colors hover:bg-stone-50 disabled:opacity-60"
        >
          <GoogleIcon />
          {busy ? 'Signing in...' : 'Continue with Google'}
        </button>

        {error && <p className="mt-3 text-xs text-rose-500">{error}</p>}
      </div>
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.4 0 6.4 1.2 8.8 3.5l6.5-6.5C35.3 2.5 30 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.6 5.9C12.1 13 17.6 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.9 7.2l7.6 5.9c4.4-4.1 7.1-10.1 7.1-17.6z" />
      <path fill="#FBBC05" d="M10.2 19.1a14.5 14.5 0 0 0 0 9.8l-7.6 5.9a24 24 0 0 1 0-21.6l7.6 5.9z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.6-5.9c-2.1 1.4-4.9 2.3-8.3 2.3-6.4 0-11.9-3.5-13.8-8.7l-7.6 5.9C6.5 42.6 14.6 48 24 48z" />
    </svg>
  )
}
