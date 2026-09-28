import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider.jsx'
import { getAsyncApplyMe } from '../api.js'

/**
 * Gate for every route that needs a signed-in user. Renders nothing but a
 * blank screen while Firebase is still resolving the session on first
 * load -- that resolution is usually sub-second, so a spinner would just
 * flash. Once signed in, also checks whether the one-time onboarding
 * screen still needs to be shown, redirecting there unless the user is
 * already on it (avoiding a redirect loop).
 */
export default function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()
  const [needsOnboarding, setNeedsOnboarding] = useState(null)

  useEffect(() => {
    if (!user) return
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
  if (location.pathname === '/onboarding') return <Outlet />
  if (needsOnboarding === null) return null
  if (needsOnboarding) return <Navigate to="/onboarding" replace />
  return <Outlet />
}
