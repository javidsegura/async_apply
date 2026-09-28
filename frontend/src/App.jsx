import { Routes, Route } from 'react-router-dom'
import RequireAuth from './auth/RequireAuth.jsx'
import Login from './pages/Login.jsx'
import AsyncApplyLayout from './pages/asyncapply/AsyncApplyLayout.jsx'
import Hub from './pages/asyncapply/Hub.jsx'
import Pipeline from './pages/asyncapply/Pipeline.jsx'
import History from './pages/asyncapply/History.jsx'
import Metrics from './pages/asyncapply/Metrics.jsx'
import Config from './pages/asyncapply/Config.jsx'
import Admin from './pages/asyncapply/Admin.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<AsyncApplyLayout />}>
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
