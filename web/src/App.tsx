import { lazy, Suspense } from 'react'
import { ErrorBoundary } from './components/ErrorBoundary'
import {
  SkeletonModelMonitoring,
  SkeletonLoyaltyDashboard,
  SkeletonTransactionHistory,
} from './components/Skeletons'
import './styles/skeleton.css'

// Lazy-load each dashboard section so the initial bundle is smaller and the
// browser can start rendering the first panel before the others are parsed.
const ModelMonitoringDashboard = lazy(() =>
  import('./components/ModelMonitoringDashboard/ModelMonitoringDashboard').then((m) => ({
    default: m.ModelMonitoringDashboard,
  }))
)

const LoyaltyDashboard = lazy(() =>
  import('./components/LoyaltyDashboard').then((m) => ({ default: m.LoyaltyDashboard }))
)

const TransactionHistoryPage = lazy(() =>
  import('./components/TransactionHistory').then((m) => ({ default: m.TransactionHistoryPage }))
)

export default function App() {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <h1>Model Performance Monitoring</h1>
      <ErrorBoundary boundary="Model Monitoring">
        <Suspense fallback={<SkeletonModelMonitoring />}>
          <ModelMonitoringDashboard />
        </Suspense>
      </ErrorBoundary>

      <hr style={{ margin: '40px 0', borderColor: '#ddd' }} />

      <h1>Loyalty Dashboard</h1>
      <ErrorBoundary boundary="Loyalty Dashboard">
        <Suspense fallback={<SkeletonLoyaltyDashboard />}>
          <LoyaltyDashboard />
        </Suspense>
      </ErrorBoundary>

      <hr style={{ margin: '40px 0', borderColor: '#ddd' }} />

      <h1>Transaction History</h1>
      <ErrorBoundary boundary="Transaction History">
        <Suspense fallback={<SkeletonTransactionHistory />}>
          <TransactionHistoryPage />
        </Suspense>
      </ErrorBoundary>
    </div>
  )
}