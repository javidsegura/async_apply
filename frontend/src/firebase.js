import { initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider } from 'firebase/auth'

// This config is not secret -- Firebase's actual security boundary is the
// server verifying the ID token (see backend/services/asyncapply/auth.py),
// not hiding this object. Safe to ship in frontend code.
const firebaseConfig = {
  apiKey: 'AIzaSyBhYTZGUMZ6_I5G5yTYS8-Pf9Icjo4pGXo',
  authDomain: 'async-apply.firebaseapp.com',
  projectId: 'async-apply',
  storageBucket: 'async-apply.firebasestorage.app',
  messagingSenderId: '472104121376',
  appId: '1:472104121376:web:7254e7542cbed564ccb845',
}

const app = initializeApp(firebaseConfig)

export const auth = getAuth(app)
export const googleProvider = new GoogleAuthProvider()
