import type { SignalKind } from '~/composables/useScreener'

// Display helpers only — every value comes from the backend; these never derive new numbers.

export const fmtPrice = (n?: number | null) => n != null ? `$${n < 1 ? n.toFixed(4) : n.toFixed(2)}` : '—'
export const fmtGap = (n?: number | null) => n != null ? `${n > 0 ? '+' : ''}${n.toFixed(1)}%` : '—'
export const fmtRvol = (n?: number | null) => n != null ? `${n.toFixed(1)}×` : 'N/A'
export const fmtShares = (n?: number | null) => n != null ? `${(n / 1e6).toFixed(1)}M` : '—'
export const fmtRR = (n?: number | null) => n != null ? `${n.toFixed(1)} : 1` : '—'

/** $1.23B / $456M / $7.8K */
export function fmtMoney(n?: number | null): string {
  if (n == null) return 'N/A'
  const a = Math.abs(n)
  if (a >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (a >= 1e9) return `$${(n / 1e9).toFixed(a >= 1e10 ? 1 : 2)}B`
  if (a >= 1e6) return `$${(n / 1e6).toFixed(a >= 1e8 ? 0 : 1)}M`
  if (a >= 1e3) return `$${(n / 1e3).toFixed(1)}K`
  return `$${n.toFixed(0)}`
}

export const SIGNALS: Record<SignalKind, { label: string; icon: string; tone: string; hint: string }> = {
  strong_buy:  { label: 'Strong buy',  icon: '▲▲', tone: 'strong-pos', hint: 'In play with measured RVol, a live chart setup and a 2:1 plan' },
  buy:         { label: 'Buy',         icon: '▲',  tone: 'pos',        hint: 'In play and holding above the open' },
  hold:        { label: 'Hold',        icon: '■',  tone: 'neutral',    hint: 'Not a long setup yet — watch' },
  sell:        { label: 'Sell',        icon: '▼',  tone: 'neg',        hint: 'Below the open with sellers in control — avoid longs' },
  strong_sell: { label: 'Strong sell', icon: '▼▼', tone: 'strong-neg', hint: 'Gapping down and below the open — avoid longs' }
}
export const SIGNAL_ORDER: SignalKind[] = ['strong_buy', 'buy', 'hold', 'sell', 'strong_sell']
