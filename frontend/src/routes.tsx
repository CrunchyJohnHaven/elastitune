import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ConnectScreen from './screens/ConnectScreen'
import CommitteeScreen from './screens/CommitteeScreen'
import ErrorBoundary from './components/ui/ErrorBoundary'

const RunScreen = lazy(() => import('./screens/RunScreen'))
const ReportScreen = lazy(() => import('./screens/ReportScreen'))
const CompareScreen = lazy(() => import('./screens/CompareScreen'))
const BenchmarkDashboard = lazy(() => import('./screens/BenchmarkDashboard'))
const CommitteeRunScreen = lazy(() => import('./screens/CommitteeRunScreen'))
const CommitteeReportScreen = lazy(() => import('./screens/CommitteeReportScreen'))
const HistoryScreen = lazy(() => import('./screens/HistoryScreen'))
const CommitteeHistoryScreen = lazy(() => import('./screens/CommitteeHistoryScreen'))

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

function Guarded({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<RouteFallback />}>
        {children}
      </Suspense>
    </ErrorBoundary>
  )
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Guarded><ConnectScreen /></Guarded>} />
      <Route path="/committee" element={<Guarded><CommitteeScreen /></Guarded>} />
      <Route path="/run/:runId" element={<Guarded><RunScreen /></Guarded>} />
      <Route path="/report/:runId" element={<Guarded><ReportScreen /></Guarded>} />
      <Route path="/history" element={<Guarded><HistoryScreen /></Guarded>} />
      <Route path="/compare/:runId1/:runId2" element={<Guarded><CompareScreen /></Guarded>} />
      <Route path="/benchmarks" element={<Guarded><BenchmarkDashboard /></Guarded>} />
      <Route path="/committee/run/:runId" element={<Guarded><CommitteeRunScreen /></Guarded>} />
      <Route path="/committee/report/:runId" element={<Guarded><CommitteeReportScreen /></Guarded>} />
      <Route path="/committee/history" element={<Guarded><CommitteeHistoryScreen /></Guarded>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
