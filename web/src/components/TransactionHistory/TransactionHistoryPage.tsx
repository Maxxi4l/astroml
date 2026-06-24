import { useState } from 'react'
import { useTransactionHistory } from '../../hooks/useTransactionHistory'
import { TransactionHistoryTable } from './TransactionHistoryTable'
import { SkeletonTransactionHistory } from '../Skeletons'

export function TransactionHistoryPage() {
  const [page, setPage] = useState(0)
  const pageSize = 20
  
  const [filters, setFilters] = useState<{
    sourceAccount?: string
    operationType?: string
    startDate?: string
    endDate?: string
  }>({})

  const { data: history, isLoading: loading } = useTransactionHistory(page, pageSize, filters)

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value || undefined,
    }))
    setPage(0) // Reset to first page when filters change
  }

  if (loading) return <SkeletonTransactionHistory />

  return (
    <div style={{ display: 'grid', gap: 24 }}>
      <div>
        <h1 style={{ margin: '0 0 16px 0', fontSize: 28, fontWeight: 700 }}>Transaction History</h1>
        <p style={{ margin: 0, color: '#666' }}>
          View and search Stellar blockchain transactions
        </p>
      </div>

      <div style={{
        padding: 16,
        backgroundColor: '#f9f9f9',
        borderRadius: 8,
        border: '1px solid #e0e0e0',
      }}>
        <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 600, color: '#555' }}>
              Source Account
            </label>
            <input
              type="text"
              placeholder="G..."
              value={filters.sourceAccount || ''}
              onChange={(e) => handleFilterChange('sourceAccount', e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 4,
                fontSize: 14,
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 600, color: '#555' }}>
              Operation Type
            </label>
            <select
              value={filters.operationType || ''}
              onChange={(e) => handleFilterChange('operationType', e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 4,
                fontSize: 14,
              }}
            >
              <option value="">All Types</option>
              <option value="payment">Payment</option>
              <option value="create_account">Create Account</option>
              <option value="change_trust">Change Trust</option>
              <option value="path_payment">Path Payment</option>
              <option value="manage_buy_offer">Manage Buy Offer</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 600, color: '#555' }}>
              Start Date
            </label>
            <input
              type="date"
              value={filters.startDate || ''}
              onChange={(e) => handleFilterChange('startDate', e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 4,
                fontSize: 14,
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 600, color: '#555' }}>
              End Date
            </label>
            <input
              type="date"
              value={filters.endDate || ''}
              onChange={(e) => handleFilterChange('endDate', e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 4,
                fontSize: 14,
              }}
            />
          </div>
        </div>

        <div style={{ marginTop: 12 }}>
          <button
            onClick={() => setFilters({})}
            style={{
              padding: '6px 12px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            Clear Filters
          </button>
        </div>
      </div>

      <TransactionHistoryTable
        response={history}
        loading={loading}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
      />

      {history && (
        <div style={{ fontSize: 13, color: '#666', textAlign: 'center' }}>
          Showing {Math.min((page + 1) * pageSize, history.total)} of {history.total} transactions
        </div>
      )}
    </div>
  )
}