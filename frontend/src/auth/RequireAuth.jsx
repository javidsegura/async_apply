import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthProvider.jsx'

/**
 * Gate for every route that needs a signed-in user. Renders nothing but a
 * blank screen while Firebase is still resolving the session on first
 * load -- that resolution is usually sub-second, so a spinner would just
 * flash.
 */
export default function RequireAuth() {
  const { user, loading } = useAuth()

  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
