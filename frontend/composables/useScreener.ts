import { useState, useRuntimeConfig } from '#imports'

export interface Pillar { key: string; label: string; status: 'pass'|'fail'|'warn'|'unknown'; value?: number; display: string; note: string }
export interface NewsItem { headline: string; source: string; url: string; published: string }
export interface Candle { t: number; o: number; h: number; l: number; c: number; v: number }
export interface Setup {
  pattern: 'bull_flag'|'flat_top'|'none'; stage: string
  entry?: number; stop?: number; scale_out?: number; target?: number; risk?: number; reward_risk?: number; ema9?: number; notes: string[]
}
export interface ScreenResult {
  symbol: string; name: string; price?: number; gap_pct?: number; rvol?: number
  shares_outstanding?: number; pillars: Pillar[]; score: number; in_play: boolean
  catalyst?: NewsItem; news_count: number; setup?: Setup; error?: string
}
export interface Session { et_time: string; et_date: string; phase: string; tradeable: boolean; advice: string }
export interface Thresholds { price_min: number; price_max: number; gap_pct_min: number; rvol_min: number; float_ideal: number; float_max: number; news_lookback_hours: number }
export interface ScreenResponse { scanned_at: string; session: Session; candles_available: boolean; results: ScreenResult[]; in_play: string[] }

export const useScreener = () => {
  const api = useRuntimeConfig().public.apiBase
  const results = useState<ScreenResult[]>('results', () => [])
  const inPlayList = useState<string[]>('inPlayList', () => [])
  const scannedAt = useState<string | null>('scannedAt', () => null)
  const candlesAvailable = useState<boolean>('candlesAvailable', () => true)
  const session = useState<Session | null>('session', () => null)
  const loading = useState('loading', () => false)
  const error = useState<string | null>('error', () => null)
  const thresholds = useState<Thresholds>('thresholds', () => ({
    price_min: 2, price_max: 20, gap_pct_min: 10, rvol_min: 5,
    float_ideal: 10_000_000, float_max: 100_000_000, news_lookback_hours: 24
  }))

  async function health() {
    return await $fetch<{ ok: boolean; finnhub_key_set: boolean; finnhub_ok: boolean; finnhub_error?: string; candles_available: boolean; session: Session }>(`${api}/api/health`)
  }
  async function loadUniverse(): Promise<string[]> {
    return (await $fetch<{ symbols: string[] }>(`${api}/api/universe`)).symbols
  }
  async function scan(symbols: string[]) {
    loading.value = true; error.value = null
    try {
      const r = await $fetch<ScreenResponse>(`${api}/api/screen`, {
        method: 'POST',
        body: { symbols, thresholds: thresholds.value, include_setups: true }
      })
      results.value = r.results; inPlayList.value = r.in_play
      scannedAt.value = r.scanned_at; candlesAvailable.value = r.candles_available; session.value = r.session
    } catch (e: any) {
      error.value = e?.data?.detail || e?.message || 'Scan failed — is the backend running on port 8000?'
    } finally { loading.value = false }
  }
  async function detail(symbol: string) {
    return await $fetch<{ result: ScreenResult; candles: Candle[]; news: NewsItem[] }>(`${api}/api/stock/${symbol}`)
  }
  return { results, inPlayList, scannedAt, candlesAvailable, session, loading, error, thresholds, health, loadUniverse, scan, detail }
}
