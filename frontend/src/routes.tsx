import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ConnectScreen from './screens/ConnectScreen'
import CommitteeScreen from './screens/CommitteeScreen'

const RunScreen = lazy(() => import('./screens/RunScreen'))
const ReportScreen = lazy(() => import('./screens/ReportScreen'))
const CommitteeRunScreen = lazy(() => import('./screens/CommitteeRunScreen'))
const CommitteeReportScreen = lazy(() => import('./screens/CommitteeReportScreen'))

function RouteFallback() {
  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#05070B',
        color: '#9AA4B2',
        fontFamily: 'Inter, sans-serif',
        fontSize: 13,
      }}
    >
      Loading…
    </div>
  )
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<ConnectScreen />} />
        <Route path="/committee" element={<CommitteeScreen />} />
        <Route path="/run/:runId" element={<RunScreen />} />
        <Route path="/report/:runId" element={<ReportScreen />} />
        <Route path="/committee/run/:runId" element={<CommitteeRunScreen />} />
        <Route path="/committee/report/:runId" element={<CommitteeReportScreen />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
