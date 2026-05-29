import type {
  LoyaltySummary,
  LoyaltyTier,
  PointsTransaction,
  PointsHistoryResponse,
  RedemptionRequest,
  RedemptionResponse,
  StellarTransaction,
  TierComparisonDatum,
  FraudStats,
} from '../lib/types'

// For demo purposes, use in-memory mock data. Replace with real HTTP calls later.
let pointsBalance = 3250
let currentTier: LoyaltyTier = { id: 'gold', name: 'Gold', threshold: 3000, multiplier: 1.25, color: '#d4af37' }
const silver: LoyaltyTier = { id: 'silver', name: 'Silver', threshold: 1500, multiplier: 1.1, color: '#c0c0c0' }
const platinum: LoyaltyTier = { id: 'platinum', name: 'Platinum', threshold: 6000, multiplier: 1.5, color: '#e5e4e2' }

const history: PointsTransaction[] = Array.from({ length: 137 }).map((_, i) => {
  const earn = Math.floor(Math.random() * 200) + 20
  const date = new Date(Date.now() - i * 86400000).toISOString()
  return {
    id: `txn_${i}`,
    date,
    type: 'earn' as const,
    points: earn,
    source: 'Purchase',
  }
})

export async function getLoyaltySummary(): Promise<LoyaltySummary> {
  const nextTierThreshold = pointsBalance >= silver.threshold ? platinum.threshold : silver.threshold
  const nextTier = pointsBalance >= platinum.threshold
    ? undefined
    : {
        tier: pointsBalance >= silver.threshold ? platinum : silver,
        remainingToUpgrade: Math.max(0, nextTierThreshold - pointsBalance),
        progressPct: Math.min(100, Math.round((pointsBalance / nextTierThreshold) * 100)),
      }

  const benefits = [
    { id: 'b1', title: 'Free Shipping', description: 'No shipping fees on all orders.' },
    { id: 'b2', title: 'Birthday Bonus', description: '500 bonus points on your birthday.' },
    { id: 'b3', title: 'Priority Support', description: 'Skip the line with priority support.' },
  ]

  return { currentTier, pointsBalance, nextTier, benefits }
}

export async function getPointsHistory(page: number, pageSize: number): Promise<PointsHistoryResponse> {
  const start = page * pageSize
  const end = start + pageSize
  const data = history.slice(start, end)
  return { data, page, pageSize, total: history.length }
}

export async function redeemPoints(req: RedemptionRequest): Promise<RedemptionResponse> {
  await delay(300)
  if (req.points <= 0 || req.points > pointsBalance) {
    throw new Error('Invalid redemption amount')
  }
  pointsBalance -= req.points
  const transaction = {
    id: `txn_red_${Date.now()}`,
    date: new Date().toISOString(),
    type: 'redeem' as const,
    points: -Math.abs(req.points),
    source: 'Redemption',
  }
  history.unshift(transaction)
  return { newBalance: pointsBalance, transaction }
}

export async function getTierComparison(): Promise<TierComparisonDatum[]> {
  return [
    { tier: 'Silver', threshold: 1500, multiplier: 1.1, retention: 70 },
    { tier: 'Gold', threshold: 3000, multiplier: 1.25, retention: 80 },
    { tier: 'Platinum', threshold: 6000, multiplier: 1.5, retention: 90 },
  ]
}

export async function getReferralLink(): Promise<{ url: string; invited: number; rewards: number }> {
  return { url: 'https://example.com/ref?code=ABC123', invited: 12, rewards: 4 }
}

type IncomingTransactionListener = (transaction: StellarTransaction) => void

export function subscribeToIncomingTransactions(listener: IncomingTransactionListener): () => void {
  const emit = () => listener(createMockStellarTransaction())
  emit()
  const timer = window.setInterval(emit, 2200)
  return () => window.clearInterval(timer)
}

function createMockStellarTransaction(): StellarTransaction {
  return {
    id: `stellar_txn_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
    timestamp: new Date().toISOString(),
    amount: Number((Math.random() * 120 + 5).toFixed(2)),
    sourceAccount: randomAccount(),
    destinationAccount: randomAccount(),
  }
}

function randomAccount() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  let value = 'G'
  for (let i = 0; i < 10; i += 1) {
    value += chars[Math.floor(Math.random() * chars.length)]
  }
  return `${value}...`
}

export async function getFraudStats(): Promise<FraudStats> {
  const patterns = ['sybil_cluster', 'wash_trading_loop', 'anomaly'] as const
  const descriptions = [
    'Coordinated fan-out from single controller account',
    'Circular value transfer detected across 5 accounts',
    'Unusual transaction velocity spike',
    'Low-value repeated transfers to new accounts',
    'Rapid account creation with identical patterns',
    'Wash trading loop with 4 participants',
    'Minor anomaly in transaction timing',
    'Sybil cluster with 8 coordinated identities',
  ]
  const scores = [85, 72, 91, 45, 60, 88, 33, 77]

  const recentAlerts = Array.from({ length: 8 }).map((_, i) => ({
    id: `alert_${i}`,
    accountId: `GACC${String(i).padStart(4, '0')}`,
    pattern: patterns[i % 3],
    riskScore: scores[i],
    detectedAt: new Date(Date.now() - i * 3600000 * 6).toISOString(),
    description: descriptions[i],
  }))

  const riskOverTime = Array.from({ length: 14 }).map((_, i) => ({
    date: new Date(Date.now() - (13 - i) * 86400000).toISOString().slice(0, 10),
    score: [42, 38, 55, 61, 48, 70, 65, 58, 72, 80, 68, 75, 63, 71][i],
  }))

  return {
    totalAlerts: 24,
    highRisk: 7,
    mediumRisk: 11,
    lowRisk: 6,
    recentAlerts,
    riskOverTime,
  }
}

function delay(ms: number) {
  return new Promise((res) => setTimeout(res, ms))
}
