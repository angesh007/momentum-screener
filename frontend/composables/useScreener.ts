import { useState, useRuntimeConfig } from '#imports'

export interface Pillar { key: string; label: string; status: 'pass'|'fail'|'warn'|'unknown'; value?: number; display: string; note: string }
export interface NewsItem { headline: string; source: string; url: string; published: string }
export interface Candle { t: number; o: number; h: number; l: number; c: number; v: number }
export interface Setup {
  pattern: 'bull_flag'|'flat_top'|'none'; stage: string
  entry?: number; stop?: number; scale_out?: number; target?: number; risk?: number; reward_risk?: number; ema9?: number; notes: string[]
}
export interface TradePlan {
  source: 'setup'|'day_range'
  entry: number; stop: number; scale_out: number; target: number; risk: number; reward_risk: number; risk_pct: number; note: string
}
export type SignalKind = 'strong_buy'|'buy'|'hold'|'sell'|'strong_sell'
export interface SignalReason {
  factor: 'pillars'|'rvol'|'momentum'|'trend'|'breakout'|'setup'|'risk_reward'|'catalyst'
  label: string; detail: string; impact: 'positive'|'negative'|'neutral'
}
export interface ScreenResult {
  symbol: string; name: string; price?: number; gap_pct?: number; rvol?: number
  today_volume?: number; avg_volume?: number
  shares_outstanding?: number; market_cap?: number
  open?: number; high?: number; low?: number; prev_close?: number
  quote_time?: number   // unix seconds of the quote — dates the daily candle
  pillars: Pillar[]; score: number; in_play: boolean
  catalyst?: NewsItem; news_count: number; setup?: Setup; plan?: TradePlan
  // Optional so an older backend without signals still renders.
  signal?: SignalKind; signal_reasons?: SignalReason[]; signal_note?: string
  error?: string
}
export interface Session { et_time: string; et_date: string; phase: string; tradeable: boolean; advice: string }
export interface Thresholds { price_min: number; price_max: number; gap_pct_min: number; rvol_min: number; float_ideal: number; float_max: number; news_lookback_hours: number }
export interface ScreenResponse { scanned_at: string; session: Session; candles_available: boolean; results: ScreenResult[]; in_play: string[] }
export interface Health { ok: boolean; finnhub_key_set: boolean; finnhub_ok: boolean; finnhub_error?: string; candles_available: boolean; session: Session }

/**
 * Backend connection lifecycle. The API is hosted on Render, whose free
 * instances sleep when idle: the first request can hang for a minute or more
 * (or fail with 502/503) while the service boots, so we poll until it answers.
 *   connecting → (slow) waking → loading → ready
 *                                         ↘ error (gave up; user can retry)
 */
export type ConnectionPhase = 'connecting'|'waking'|'loading'|'ready'|'error'

const ATTEMPT_TIMEOUT_MS = 20_000   // one health request
const RETRY_DELAY_MS = 3_000
const GIVE_UP_AFTER_MS = 180_000    // Render cold starts are usually < 1 min, occasionally longer
const WAKING_AFTER_MS = 5_000       // a warm backend answers well within this
const SLOW_SCAN_MS = 10_000

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))

export const useScreener = () => {
  const api = useRuntimeConfig().public.apiBase
  const results = useState<ScreenResult[]>('results', () => [])
  const inPlayList = useState<string[]>('inPlayList', () => [])
  const scannedAt = useState<string | null>('scannedAt', () => null)
  const candlesAvailable = useState<boolean>('candlesAvailable', () => true)
  const session = useState<Session | null>('session', () => null)
  const loading = useState('loading', () => false)
  const scanSlow = useState('scanSlow', () => false)
  const error = useState<string | null>('error', () => null)
  const thresholds = useState<Thresholds>('thresholds', () => ({
    price_min: 2, price_max: 20, gap_pct_min: 10, rvol_min: 5,
    float_ideal: 10_000_000, float_max: 100_000_000, news_lookback_hours: 24
  }))
  const connection = useState<ConnectionPhase>('connection', () => 'connecting')
  const connectionStartedAt = useState<number>('connectionStartedAt', () => Date.now())
  const connectionError = useState<string>('connectionError', () => '')

  async function health(timeout?: number) {
    return await $fetch<Health>(`${api}/api/health`, { timeout, retry: 0 })
  }
  async function loadUniverse(): Promise<string[]> {
    return (await $fetch<{ symbols: string[] }>(`${api}/api/universe`)).symbols
  }

  /** Poll /api/health until the backend answers, then run `onReady` (initial data). */
  async function connect(onReady: (h: Health) => Promise<void>) {
    connection.value = 'connecting'
    connectionError.value = ''
    connectionStartedAt.value = Date.now()
    const started = connectionStartedAt.value
    const wakingTimer = setTimeout(() => {
      if (connection.value === 'connecting') connection.value = 'waking'
    }, WAKING_AFTER_MS)
    try {
      let lastErr = ''
      while (Date.now() - started < GIVE_UP_AFTER_MS) {
        let h: Health | null = null
        try {
          h = await health(ATTEMPT_TIMEOUT_MS)
        } catch (e: any) {
          lastErr = e?.data?.detail || e?.message || 'No response'
          await sleep(RETRY_DELAY_MS)
          continue
        }
        connection.value = 'loading'
        try {
          await onReady(h)
          connection.value = 'ready'
        } catch (e: any) {
          connectionError.value = e?.data?.detail || e?.message || 'The backend answered but market data failed to load.'
          connection.value = 'error'
        }
        return
      }
      if (lastErr) console.warn('Backend health check failed:', lastErr)
      connectionError.value = `No response from the trading engine after ${Math.round(GIVE_UP_AFTER_MS / 60_000)} minutes.`
      connection.value = 'error'
    } finally {
      clearTimeout(wakingTimer)
    }
  }

  async function scan(symbols: string[]) {
    loading.value = true; error.value = null; scanSlow.value = false
    const slowTimer = setTimeout(() => { scanSlow.value = true }, SLOW_SCAN_MS)
    try {
      const r = await $fetch<ScreenResponse>(`${api}/api/screen`, {
        method: 'POST',
        body: { symbols, thresholds: thresholds.value, include_setups: true }
      })
      results.value = r.results; inPlayList.value = r.in_play
      scannedAt.value = r.scanned_at; candlesAvailable.value = r.candles_available; session.value = r.session
    } catch (e: any) {
      error.value = e?.data?.detail || e?.message || 'Scan failed — the trading engine did not respond. Try again in a moment.'
    } finally {
      clearTimeout(slowTimer)
      loading.value = false; scanSlow.value = false
    }
  }
  async function detail(symbol: string) {
    // Same cut-offs as the board, so the drawer's signal matches the row.
    return await $fetch<{ result: ScreenResult; candles: Candle[]; news: NewsItem[] }>(`${api}/api/stock/${symbol}`, { query: { ...thresholds.value } })
  }
  return {
    results, inPlayList, scannedAt, candlesAvailable, session, loading, scanSlow, error, thresholds,
    connection, connectionStartedAt, connectionError,
    health, loadUniverse, connect, scan, detail
  }
}
