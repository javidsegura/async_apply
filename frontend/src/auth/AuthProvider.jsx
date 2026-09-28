import { createContext, useContext, useEffect, useState } from 'react'
import { onAuthStateChanged, signInWithPopup, signOut } from 'firebase/auth'
import { auth, googleProvider } from '../firebase.js'

const AuthContext = createContext(null)

/**
 * Tracks the signed-in Firebase user for the whole app.
 *
 * api.js reads auth.currentUser directly when it needs a fresh ID token, so
 * this provider's only job is UI state: who's signed in, and whether we're
 * still figuring that out on first load.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => onAuthStateChanged(auth, (u) => {
    setUser(u)
    setLoading(false)
  }), [])

  const signInWithGoogle = () => signInWithPopup(auth, googleProvider)
  const signOutUser = () => signOut(auth)

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, signOutUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
