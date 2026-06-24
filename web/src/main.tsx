import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { initErrorReporting } from './lib/errorReporting'
import { ThemeProvider } from './contexts/ThemeContext'

// Initialise Sentry (no-op when VITE_SENTRY_DSN is absent)
initErrorReporting()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Surface errors to the nearest ErrorBoundary instead of swallowing them
      throwOnError: true,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* Top-level boundary — catches errors that escape section-level boundaries */}
    <ErrorBoundary boundary="Application">
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <App />
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
)
