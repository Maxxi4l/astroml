import type { BlockchainTransaction, TransactionHistoryResponse } from '../lib/types'

// Mock transaction data for demonstration
const mockTransactions: BlockchainTransaction[] = Array.from({ length: 250 }).map((_, i) => {
  const operationTypes = ['payment', 'create_account', 'change_trust', 'path_payment', 'manage_buy_offer']
  const assetCodes = ['XLM', 'USDC', 'EURC', 'BTC', 'ETH']
  const baseTime = Date.now() - i * 3600000 // One hour apart
  
  return {
    hash: `tx_${'a'.repeat(56)}${i.toString().padStart(8, '0')}`,
    ledgerSequence: 50000 + i,
    sourceAccount: `G${'A'.repeat(28)}${'B'.repeat(27)}`,
    destinationAccount: i % 3 === 0 ? undefined : `G${'C'.repeat(28)}${'D'.repeat(27)}`,
    amount: i % 4 === 0 ? undefined : Math.floor(Math.random() * 10000) + 100,
    assetCode: assetCodes[i % assetCodes.length],
    assetIssuer: i % 2 === 0 ? undefined : `G${'E'.repeat(28)}${'F'.repeat(27)}`,
    operationType: operationTypes[i % operationTypes.length],
    createdAt: new Date(baseTime).toISOString(),
    fee: 100 + (i % 5) * 50,
    successful: i % 10 !== 0, // 10% failure rate
    memoType: i % 7 === 0 ? 'text' : undefined,
  }
})

export async function getTransactionHistory(
  page: number,
  pageSize: number,
  filters?: {
    sourceAccount?: string
    operationType?: string
    startDate?: string
    endDate?: string
  }
): Promise<TransactionHistoryResponse> {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 300))
  
  let filtered = [...mockTransactions]
  
  // Apply filters if provided
  if (filters?.sourceAccount) {
    filtered = filtered.filter((tx) => 
      tx.sourceAccount.toLowerCase().includes(filters.sourceAccount!.toLowerCase())
    )
  }
  
  if (filters?.operationType) {
    filtered = filtered.filter((tx) => tx.operationType === filters.operationType)
  }
  
  if (filters?.startDate) {
    filtered = filtered.filter((tx) => new Date(tx.createdAt) >= new Date(filters.startDate!))
  }
  
  if (filters?.endDate) {
    filtered = filtered.filter((tx) => new Date(tx.createdAt) <= new Date(filters.endDate!))
  }
  
  const start = page * pageSize
  const end = start + pageSize
  const data = filtered.slice(start, end)
  
  return {
    data,
    page,
    pageSize,
    total: filtered.length,
  }
}

export async function getTransactionByHash(hash: string): Promise<BlockchainTransaction | null> {
  await new Promise((resolve) => setTimeout(resolve, 200))
  return mockTransactions.find((tx) => tx.hash === hash) || null
}
