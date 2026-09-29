import { Routes, Route, Navigate } from 'react-router-dom'
import RequireAuth from './auth/RequireAuth.jsx'
import Login from './pages/Login.jsx'
import Onboarding from './pages/Onboarding.jsx'
import AsyncApplyLayout from './pages/asyncapply/AsyncApplyLayout.jsx'
import Hub from './pages/asyncapply/Hub.jsx'
import Pipeline from './pages/asyncapply/Pipeline.jsx'
import History from './pages/asyncapply/History.jsx'
import Metrics from './pages/asyncapply/Metrics.jsx'
import Config from './pages/asyncapply/Config.jsx'
import Admin from './pages/asyncapply/Admin.jsx'
import Welcome from './pages/marketing/Welcome.jsx'
import Pricing from './pages/marketing/Pricing.jsx'
import Privacy from './pages/marketing/Privacy.jsx'
import Terms from './pages/marketing/Terms.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/welcome" element={<Navigate to="/" replace />} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/app" element={<AsyncApplyLayout />}>
          <Route index element={<Hub />} />
          <Route path="apply" element={<Pipeline />} />
          <Route path="history" element={<History />} />
          <Route path="metrics" element={<Metrics />} />
          <Route path="config" element={<Config />} />
          <Route path="admin" element={<Admin />} />
        </Route>
      </Route>
    </Routes>
  )
}
