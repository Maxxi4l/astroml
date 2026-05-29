import { LoyaltyDashboard } from './components/LoyaltyDashboard'
import { ModelMonitoringDashboard } from './components/ModelMonitoringDashboard'
import { TransactionHistoryPage } from './components/TransactionHistory'

export default function App() {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <h1>Model Performance Monitoring</h1>
      <ModelMonitoringDashboard />
      <hr style={{ margin: '40px 0', borderColor: '#ddd' }} />
      <h1>Loyalty Dashboard</h1>
      <LoyaltyDashboard />
      <hr style={{ margin: '40px 0', borderColor: '#ddd' }} />
      <h1>Transaction History</h1>
      <TransactionHistoryPage />
    </div>
  )
}
