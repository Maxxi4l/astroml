import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useIncomingTransactions } from '../../hooks/useIncomingTransactions'

type ChartPoint = {
  id: string
  time: string
  amount: number
}

export function RealTimeTransactionsChart() {
  const transactions = useIncomingTransactions()

  const chartData: ChartPoint[] = [...transactions]
    .reverse()
    .map((tx) => ({
      id: tx.id,
      time: new Date(tx.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      amount: tx.amount,
    }))

  const latest = transactions[0]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <h2 style={{ margin: '8px 0' }}>Live Stellar Transactions</h2>
        <div style={{ color: '#555', fontSize: 14 }}>
          {latest ? `Latest: ${latest.amount.toFixed(2)} XLM from ${latest.sourceAccount}` : 'Waiting for stream...'}
        </div>
      </div>
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" minTickGap={20} />
            <YAxis />
            <Tooltip formatter={(value: number) => `${value.toFixed(2)} XLM`} />
            <Line type="monotone" dataKey="amount" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
