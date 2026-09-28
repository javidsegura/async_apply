import { Routes, Route } from 'react-router-dom'
import AsyncApplyLayout from './pages/asyncapply/AsyncApplyLayout.jsx'
import Hub from './pages/asyncapply/Hub.jsx'
import Pipeline from './pages/asyncapply/Pipeline.jsx'
import History from './pages/asyncapply/History.jsx'
import Metrics from './pages/asyncapply/Metrics.jsx'
import Config from './pages/asyncapply/Config.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AsyncApplyLayout />}>
        <Route index element={<Hub />} />
        <Route path="apply" element={<Pipeline />} />
        <Route path="history" element={<History />} />
        <Route path="metrics" element={<Metrics />} />
        <Route path="config" element={<Config />} />
      </Route>
    </Routes>
  )
}
