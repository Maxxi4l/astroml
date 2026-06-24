import React from 'react'
import type { BlockchainTransaction, TransactionHistoryResponse } from '../../lib/types'

export function TransactionHistoryTable({
  response,
  loading,
  page,
  pageSize,
  onPageChange,
}: {
  response: TransactionHistoryResponse | undefined
  loading: boolean
  page: number
  pageSize: number
  onPageChange: (p: number) => void
}) {
  const total = response?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const formatHash = (hash: string) => {
    return `${hash.slice(0, 8)}...${hash.slice(-8)}`
  }

  const formatAddress = (address: string) => {
    return `${address.slice(0, 4)}...${address.slice(-4)}`
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: '8px 0' }}>Transaction History</h2>
        <div>
          <button 
            disabled={page === 0 || loading} 
            onClick={() => onPageChange(page - 1)}
            style={{ padding: '6px 12px', marginRight: '8px', cursor: page === 0 || loading ? 'not-allowed' : 'pointer' }}
          >
            Prev
          </button>
          <span style={{ margin: '0 8px' }}>Page {page + 1} / {totalPages}</span>
          <button 
            disabled={page + 1 >= totalPages || loading} 
            onClick={() => onPageChange(page + 1)}
            style={{ padding: '6px 12px', marginLeft: '8px', cursor: page + 1 >= totalPages || loading ? 'not-allowed' : 'pointer' }}
          >
            Next
          </button>
        </div>
      </div>
      <div style={{ overflowX: 'auto', marginTop: '16px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={th}>Hash</th>
              <th style={th}>Ledger</th>
              <th style={th}>Source</th>
              <th style={th}>Destination</th>
              <th style={th}>Type</th>
              <th style={th}>Amount</th>
              <th style={th}>Asset</th>
              <th style={th}>Fee</th>
              <th style={th}>Status</th>
              <th style={th}>Date</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={10} style={{ padding: 12, textAlign: 'center' }}>Loading...</td></tr>
            )}
            {!loading && response?.data.length === 0 && (
              <tr><td colSpan={10} style={{ padding: 12, textAlign: 'center' }}>No transactions found</td></tr>
            )}
            {!loading && response?.data.map((tx) => (
              <tr key={tx.hash}>
                <td style={td}>
                  <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                    {formatHash(tx.hash)}
                  </span>
                </td>
                <td style={td}>{tx.ledgerSequence}</td>
                <td style={td}>
                  <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                    {formatAddress(tx.sourceAccount)}
                  </span>
                </td>
                <td style={td}>
                  {tx.destinationAccount ? (
                    <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                      {formatAddress(tx.destinationAccount)}
                    </span>
                  ) : (
                    <span style={{ color: 'var(--text-muted, #999)' }}>-</span>
                  )}
                </td>
                <td style={td}>{tx.operationType}</td>
                <td style={td}>
                  {tx.amount !== undefined ? tx.amount.toLocaleString() : '-'}
                </td>
                <td style={td}>{tx.assetCode || 'XLM'}</td>
                <td style={td}>{tx.fee} stroops</td>
                <td style={td}>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    backgroundColor: tx.successful ? '#d4edda' : '#f8d7da',
                    color: tx.successful ? '#155724' : '#721c24',
                    border: '1px solid transparent',
                  }}>
                    {tx.successful ? 'Success' : 'Failed'}
                  </span>
                </td>
                <td style={td}>
                  {new Date(tx.createdAt).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const th: React.CSSProperties = { 
  textAlign: 'left', 
  borderBottom: '2px solid var(--border-color, #ddd)', 
  padding: 12,
  fontWeight: 600,
  fontSize: '13px',
  color: 'var(--text-secondary, #555)'
}
const td: React.CSSProperties = { 
  borderBottom: '1px solid var(--border-light, #f1f1f1)', 
  padding: 10,
  fontSize: '13px'
}
