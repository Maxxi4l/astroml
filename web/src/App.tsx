import { lazy, Suspense, useState } from 'react'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ThemeToggle } from './components/ThemeToggle'
import { useMediaQuery } from './hooks/useMediaQuery'

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

function SectionFallback({ label }: { label: string }) {
  return (
    <div style={{ padding: 24, color: 'var(--text-muted, #888)', fontSize: 14 }}>
      Loading {label}…
    </div>
  )
}

const sections = [
  { id: 'model-monitoring', label: 'Model Performance' },
  { id: 'loyalty', label: 'Loyalty Dashboard' },
  { id: 'transactions', label: 'Transaction History' },
]

function NavBar() {
  const isMobile = useMediaQuery('(max-width: 640px)')
  const [menuOpen, setMenuOpen] = useState(false)

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
    setMenuOpen(false)
  }

  return (
    <nav style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 24,
      paddingBottom: 16,
      borderBottom: '1px solid var(--border-color, #ddd)',
      position: 'relative',
    }}>
      <h1 style={{ margin: 0, fontSize: isMobile ? 18 : 24, fontWeight: 700 }}>
        AstroML Dashboard
      </h1>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isMobile ? (
          <>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label="Toggle navigation menu"
              style={{
                background: 'none',
                border: '1px solid var(--border-color, #ddd)',
                borderRadius: 6,
                padding: '6px 10px',
                cursor: 'pointer',
                color: 'var(--text-primary, #1a202c)',
                fontSize: 18,
              }}
            >
              {menuOpen ? '✕' : '☰'}
            </button>
            <ThemeToggle />
            {menuOpen && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                left: 0,
                background: 'var(--bg-card, #fff)',
                border: '1px solid var(--border-color, #ddd)',
                borderRadius: 8,
                padding: 8,
                zIndex: 100,
                boxShadow: 'var(--shadow-md, 0 2px 14px rgba(0,0,0,0.1))',
              }}>
                {sections.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => scrollTo(s.id)}
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: '10px 12px',
                      background: 'none',
                      border: 'none',
                      textAlign: 'left',
                      cursor: 'pointer',
                      color: 'var(--text-primary, #1a202c)',
                      fontSize: 14,
                      fontWeight: 600,
                      borderRadius: 4,
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}
          </>
        ) : (
          <>
            <div style={{ display: 'flex', gap: 8 }}>
              {sections.map((s) => (
                <button
                  key={s.id}
                  onClick={() => scrollTo(s.id)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border-color, #ddd)',
                    background: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-primary, #1a202c)',
                    fontSize: 13,
                    fontWeight: 600,
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <ThemeToggle />
          </>
        )}
      </div>
    </nav>
  )
}

export default function App() {
  const isMobile = useMediaQuery('(max-width: 640px)')

  return (
    <div style={{
      fontFamily: 'system-ui, sans-serif',
      padding: isMobile ? 12 : 16,
      maxWidth: 1200,
      margin: '0 auto',
    }}>
      <NavBar />
      <h1 id="model-monitoring">Model Performance Monitoring</h1>
      <ErrorBoundary boundary="Model Monitoring">
        <Suspense fallback={<SectionFallback label="Model Monitoring" />}>
          <ModelMonitoringDashboard />
        </Suspense>
      </ErrorBoundary>

      <hr style={{ margin: isMobile ? '24px 0' : '40px 0', borderColor: 'var(--border-color, #ddd)' }} />

      <h1 id="loyalty">Loyalty Dashboard</h1>
      <ErrorBoundary boundary="Loyalty Dashboard">
        <Suspense fallback={<SectionFallback label="Loyalty Dashboard" />}>
          <LoyaltyDashboard />
        </Suspense>
      </ErrorBoundary>

      <hr style={{ margin: isMobile ? '24px 0' : '40px 0', borderColor: 'var(--border-color, #ddd)' }} />

      <h1 id="transactions">Transaction History</h1>
      <ErrorBoundary boundary="Transaction History">
        <Suspense fallback={<SectionFallback label="Transaction History" />}>
          <TransactionHistoryPage />
        </Suspense>
      </ErrorBoundary>
    </div>
  )
}
