import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider.jsx'
import { getAsyncApplyMe } from '../api.js'

/**
 * Gate for every route that needs a signed-in user. Renders nothing but a
 * blank screen while Firebase is still resolving the session on first
 * load -- that resolution is usually sub-second, so a spinner would just
 * flash. Once signed in, it also checks whether the one-time onboarding
 * screen still needs to be shown.
 *
 * The onboarding flag is fetched once per sign-in, not per navigation:
 * Onboarding calls the `onOnboarded` callback handed down through the
 * outlet context the moment it saves, so the gate's state is already
 * correct by the time it navigates away. Re-fetching on every path change
 * instead would race -- the redirect decision renders before the new
 * response lands, bouncing the user straight back to the screen they just
 * completed.
 */
export default function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()
  const [needsOnboarding, setNeedsOnboarding] = useState(null)

  useEffect(() => {
    if (!user) {
      setNeedsOnboarding(null)
      return
    }
    let cancelled = false
    getAsyncApplyMe().then((me) => {
      if (!cancelled) setNeedsOnboarding(!me.onboarding_completed)
    })
    return () => {
      cancelled = true
    }
  }, [user])

  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  if (needsOnboarding === null) return null
  if (needsOnboarding && location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />
  }
  return <Outlet context={{ onOnboarded: () => setNeedsOnboarding(false) }} />
}
