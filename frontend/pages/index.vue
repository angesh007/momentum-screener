<script setup lang="ts">
// Explicit imports: Nuxt auto-import breaks when the project path contains
// characters like "(" or ")" (e.g. a folder named "...-only(1)").
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useScreener } from '~/composables/useScreener'
import type { ScreenResult, Candle, NewsItem, SignalKind, Health } from '~/composables/useScreener'
import { fmtPrice, fmtGap, fmtRvol, fmtShares, fmtMoney, fmtRR, SIGNALS, SIGNAL_ORDER } from '~/composables/format'
import StockRow from '~/components/StockRow.vue'
import PillarStrip from '~/components/PillarStrip.vue'
import CandleChart from '~/components/CandleChart.vue'
import PositionSizer from '~/components/PositionSizer.vue'
import RulesPanel from '~/components/RulesPanel.vue'
import ThemeToggle from '~/components/ThemeToggle.vue'
import SignalBadge from '~/components/SignalBadge.vue'
import MarketValueChart from '~/components/MarketValueChart.vue'
import ConnectionScreen from '~/components/ConnectionScreen.vue'

const {
  results, inPlayList, scannedAt, candlesAvailable, session, loading, scanSlow, error, thresholds,
  connection, connectionStartedAt, connectionError, loadUniverse, connect, scan, detail
} = useScreener()

const symbolsText = ref('')
const showFilters = ref(false)
const showRules = ref(false)
const autoRefresh = ref(false)
const keyMissing = ref(false)
const finnhubOk = ref(false)
const finnhubError = ref('')
const selected = ref<{ result: ScreenResult; candles: Candle[]; news: NewsItem[] } | null>(null)
const detailLoading = ref(false)
const signalFilter = ref<SignalKind | null>(null)

const symbols = computed(() => symbolsText.value.split(/[\s,]+/).map(s => s.trim().toUpperCase()).filter(Boolean))
const matchesFilter = (r: ScreenResult) => !signalFilter.value || r.signal === signalFilter.value
const inPlay = computed(() => results.value.filter(r => inPlayList.value.includes(r.symbol) && matchesFilter(r)))
const watching = computed(() => results.value.filter(r => !inPlayList.value.includes(r.symbol) && matchesFilter(r)))
const canScan = computed(() => !loading.value && symbols.value.length > 0 && connection.value === 'ready')
const ready = computed(() => connection.value === 'ready')

const signalCounts = computed(() => {
  const c: Record<SignalKind, number> = { strong_buy: 0, buy: 0, hold: 0, sell: 0, strong_sell: 0 }
  for (const r of results.value) if (r.signal && !r.error) c[r.signal]++
  return c
})
const hasSignals = computed(() => results.value.some(r => r.signal))

const clock = ref('')
let clockTimer: number | undefined, refreshTimer: number | undefined
function tick() {
  clock.value = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(new Date())
}
const phaseLabel: Record<string, string> = {
  premarket: 'Pre-market', open: 'Opening drive', golden: 'Golden hours', midday: 'Midday chop', afterhours: 'After hours', closed: 'Closed'
}

async function onBackendReady(h: Health) {
  keyMissing.value = !h.finnhub_key_set; finnhubOk.value = h.finnhub_ok; finnhubError.value = h.finnhub_error || ''
  session.value = h.session; candlesAvailable.value = h.candles_available
  symbolsText.value = (await loadUniverse()).join(' ')
}
const startConnection = () => connect(onBackendReady)

onMounted(() => {
  tick(); clockTimer = window.setInterval(tick, 1000)
  startConnection()
})
onUnmounted(() => { clearInterval(clockTimer); clearInterval(refreshTimer) })

watch(autoRefresh, on => {
  clearInterval(refreshTimer)
  if (on) refreshTimer = window.setInterval(() => { if (!loading.value) runScan() }, 60_000)
})

async function runScan() { await scan(symbols.value) }
async function open(symbol: string) {
  detailLoading.value = true
  try { selected.value = await detail(symbol) } catch (e: any) { error.value = e?.data?.detail || 'Could not load details' }
  finally { detailLoading.value = false }
}
const scannedLabel = computed(() => scannedAt.value ? new Date(scannedAt.value).toLocaleTimeString() : '')
const patternName = (p?: string) => p === 'bull_flag' ? 'Bull flag' : p === 'flat_top' ? 'Flat top' : 'No setup'

// --- Detail-drawer helpers (derive only, never fabricate) ---
const sel = computed(() => selected.value?.result)
const passedCount = computed(() => sel.value ? sel.value.pillars.filter(p => p.status === 'pass').length : 0)
const rvolPillar = computed(() => sel.value?.pillars.find(p => p.key === 'rvol'))
const hasSetup = computed(() => !!sel.value?.setup && sel.value.setup.pattern !== 'none')
const plan = computed(() => sel.value?.plan ?? null)
const reasonsByImpact = computed(() => {
  const rs = sel.value?.signal_reasons ?? []
  return {
    positive: rs.filter(r => r.impact === 'positive'),
    negative: rs.filter(r => r.impact === 'negative'),
    neutral: rs.filter(r => r.impact === 'neutral')
  }
})
const factorName: Record<string, string> = {
  pillars: 'Pillars', rvol: 'Rel. volume', momentum: 'Momentum', trend: 'Trend',
  breakout: 'Breakout', setup: 'Setup', risk_reward: 'Risk / reward', catalyst: 'Catalyst'
}
function closeDrawer() { selected.value = null }
function onKey(e: KeyboardEvent) { if (e.key === 'Escape') closeDrawer() }
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <main class="page">
    <header class="top">
      <div class="brand">
        <h1>Momentum board</h1>
        <p class="sub">Scores your gapper list on the five pillars, live from Finnhub, and hands you a sized trade plan.</p>
      </div>
      <div class="top-right">
        <ClientOnly><ThemeToggle /></ClientOnly>
        <div class="clock" :data-phase="session?.phase">
          <span class="time">{{ clock }} <small>ET</small></span>
          <span class="phase">{{ session ? phaseLabel[session.phase] : '—' }}</span>
        </div>
      </div>
    </header>

    <!-- Initial connection: Render may be waking the backend up -->
    <ConnectionScreen
      v-if="!ready"
      :phase="connection"
      :started-at="connectionStartedAt"
      :error="connectionError"
      @retry="startConnection"
    />

    <template v-else>
      <div class="status-row">
        <p v-if="session" class="advice" :data-phase="session.phase">{{ session.advice }}</p>
        <p v-if="keyMissing" class="banner banner--error">No Finnhub key found. Put it in <code>backend/.env</code> as <code>FINNHUB_API_KEY=…</code> and restart the backend.</p>
        <p v-else-if="finnhubError" class="banner banner--error">Finnhub rejected the key: {{ finnhubError }}</p>
        <p v-else-if="finnhubOk" class="banner banner--ok"><span class="live-dot" /> Connected to Finnhub · live data</p>
      </div>
      <p v-if="scannedAt && !candlesAvailable" class="banner banner--note">
        Intraday candles aren't on the Finnhub free plan, so relative volume shows N/A and chart setups are unavailable.
        Entry, target and stop come from today's high/low instead — confirm RVol and tighten the stop on your scanner and charts.
      </p>

      <section class="controls card">
        <label class="field">
          <span>Tickers to scan <em>(pre-filled from backend/universe.txt)</em></span>
          <textarea v-model="symbolsText" rows="2" spellcheck="false" placeholder="SOUN BBAI IONQ …" />
          <small>Finnhub's free plan has no screener, so paste the gappers from your pre-market scanner here.</small>
        </label>

        <div class="actions">
          <button class="btn btn--primary" :disabled="!canScan" @click="runScan">
            <span v-if="loading" class="spinner" /> {{ loading ? 'Scanning…' : `Scan ${symbols.length} ticker${symbols.length === 1 ? '' : 's'}` }}
          </button>
          <button class="btn btn--ghost" @click="showFilters = !showFilters">{{ showFilters ? 'Hide' : 'Edit' }} thresholds</button>
          <button class="btn btn--ghost" @click="showRules = !showRules">{{ showRules ? 'Hide' : 'Show' }} the rules</button>
          <label class="toggle"><input v-model="autoRefresh" type="checkbox"> Rescan every minute</label>
          <span v-if="scannedLabel" class="stamp">Last scan {{ scannedLabel }}</span>
        </div>

        <div v-if="showFilters" class="filters">
          <label>Min price <input v-model.number="thresholds.price_min" type="number" step="0.5"></label>
          <label>Max price <input v-model.number="thresholds.price_max" type="number" step="1"></label>
          <label>Min gap % <input v-model.number="thresholds.gap_pct_min" type="number" step="1"></label>
          <label>Min rel. volume <input v-model.number="thresholds.rvol_min" type="number" step="0.5"></label>
          <label>Ideal float <input v-model.number="thresholds.float_ideal" type="number" step="1000000"></label>
          <label>Max float <input v-model.number="thresholds.float_max" type="number" step="10000000"></label>
          <label>News lookback (h) <input v-model.number="thresholds.news_lookback_hours" type="number" step="1"></label>
        </div>
        <p v-if="error" class="banner banner--error">{{ error }}</p>
      </section>

      <RulesPanel v-if="showRules" :th="thresholds" />

      <!-- Loading skeleton on first scan -->
      <section v-if="loading && !results.length" class="board" aria-busy="true">
        <h2>Scanning…</h2>
        <p v-if="scanSlow" class="slow-note"><span class="spinner" /> Still working. Big lists take a while on the free plan (60 calls/min), and the engine may still be warming up.</p>
        <div class="list">
          <div v-for="i in 4" :key="i" class="skeleton skel-row" />
        </div>
      </section>

      <div v-else-if="results.length" class="layout">
        <section class="board" :class="{ refreshing: loading }">
          <p v-if="loading" class="slow-note"><span class="spinner" /> Rescanning{{ scanSlow ? ' — still working…' : '…' }}</p>

          <h2>In play <span class="count">{{ inPlay.length }} of 10 max</span></h2>
          <p v-if="!inPlay.length" class="empty card">
            {{ signalFilter ? `No in-play stocks with a ${SIGNALS[signalFilter].label} signal.` : 'Nothing passes all five pillars right now. That\'s normal outside the open — it\'s a filter, not a suggestion box.' }}
          </p>
          <div v-else class="list">
            <StockRow v-for="(r, i) in inPlay" :key="r.symbol" :r="r" :rank="i + 1" @open="open" />
          </div>
          <template v-if="watching.length">
            <h2>Watching <span class="count">{{ watching.length }}</span></h2>
            <div class="list">
              <StockRow v-for="(r, i) in watching" :key="r.symbol" :r="r" :rank="i + 1" @open="open" />
            </div>
          </template>
        </section>

        <aside class="side">
          <section v-if="hasSignals" class="card signals">
            <div class="card-head">
              <h3 class="card-title">Signals</h3>
              <button v-if="signalFilter" class="link" @click="signalFilter = null">Show all</button>
            </div>
            <div class="sig-grid">
              <button
                v-for="k in SIGNAL_ORDER"
                :key="k"
                class="sig-tile"
                :class="{ active: signalFilter === k, zero: !signalCounts[k] }"
                :aria-pressed="signalFilter === k"
                :title="SIGNALS[k].hint"
                @click="signalFilter = signalFilter === k ? null : k"
              >
                <span class="sig-n">{{ signalCounts[k] }}</span>
                <SignalBadge :signal="k" />
              </button>
            </div>
            <p class="side-note">Click a signal to filter the board.</p>
          </section>
          <MarketValueChart :results="results" :in-play="inPlayList" @open="open" />
        </aside>
      </div>

      <section v-else class="board">
        <div class="empty card empty--hero">
          <div class="empty-icon" aria-hidden="true">📈</div>
          <p>Paste today's gappers and scan to rank them by the five pillars.</p>
          <small>Best from 9:30 to 11:30 ET.</small>
        </div>
      </section>
    </template>

    <!-- Detail drawer -->
    <aside v-if="selected || detailLoading" class="drawer" @click.self="closeDrawer">
      <div class="panel" role="dialog" aria-label="Stock detail">
        <button class="close" @click="closeDrawer" aria-label="Close">×</button>

        <template v-if="detailLoading">
          <div class="skeleton skel-head" />
          <div class="skeleton skel-block" />
          <div class="skeleton skel-block" />
        </template>

        <template v-else-if="sel && selected">
          <!-- Header: identity + status -->
          <header class="dhead">
            <div class="dhead-id">
              <span class="ticker">{{ sel.symbol }}</span>
              <span class="name">{{ sel.name }}</span>
            </div>
            <span class="badge badge--dot" :class="sel.in_play ? 'badge--pass' : 'badge--unknown'">{{ sel.in_play ? 'In play' : 'Watching' }}</span>
          </header>

          <!-- Stock information -->
          <section class="card">
            <h3 class="card-title">Stock information</h3>
            <div class="stat-grid">
              <div class="stat">
                <span class="k">Price</span>
                <span class="v">{{ fmtPrice(sel.price) }}</span>
              </div>
              <div class="stat">
                <span class="k">Change</span>
                <span class="v" :class="{ up: (sel.gap_pct ?? 0) > 0, down: (sel.gap_pct ?? 0) < 0 }">{{ fmtGap(sel.gap_pct) }}</span>
              </div>
              <div class="stat">
                <span class="k">Market value</span>
                <span class="v">{{ fmtMoney(sel.market_cap) }}</span>
              </div>
              <div class="stat stat--rvol" :data-status="rvolPillar?.status ?? 'unknown'" :title="rvolPillar?.note">
                <span class="k">Rel. volume</span>
                <span class="v">{{ fmtRvol(sel.rvol) }}</span>
                <span v-if="sel.rvol == null" class="s">{{ rvolPillar?.note || 'Unavailable' }}</span>
              </div>
              <div class="stat">
                <span class="k">Float</span>
                <span class="v">{{ fmtShares(sel.shares_outstanding) }}</span>
              </div>
              <div class="stat">
                <span class="k">Open</span>
                <span class="v">{{ fmtPrice(sel.open) }}</span>
              </div>
              <div class="stat">
                <span class="k">Day range</span>
                <span class="v sm">{{ fmtPrice(sel.low) }} – {{ fmtPrice(sel.high) }}</span>
              </div>
              <div class="stat">
                <span class="k">Prev close</span>
                <span class="v">{{ fmtPrice(sel.prev_close) }}</span>
              </div>
            </div>
          </section>

          <!-- Signal + reasons -->
          <section v-if="sel.signal" class="card">
            <div class="card-head">
              <h3 class="card-title">Signal</h3>
              <SignalBadge :signal="sel.signal" large />
            </div>
            <p v-if="sel.signal_note" class="signal-note top">{{ sel.signal_note }}</p>
            <div class="reasons">
              <template v-for="grp in (['positive', 'negative', 'neutral'] as const)" :key="grp">
                <div v-if="reasonsByImpact[grp].length" class="reason-group" :data-impact="grp">
                  <h4>{{ grp === 'positive' ? 'Supporting' : grp === 'negative' ? 'Against' : 'Neutral / unverified' }}</h4>
                  <ul>
                    <li v-for="x in reasonsByImpact[grp]" :key="x.factor + x.label">
                      <span class="rf">{{ factorName[x.factor] || x.factor }}</span>
                      <span class="rl">{{ x.label }}</span>
                      <span v-if="x.detail" class="rd">{{ x.detail }}</span>
                    </li>
                  </ul>
                </div>
              </template>
            </div>
          </section>

          <!-- Trade plan: entry / target / stop / R:R -->
          <section class="card">
            <div class="card-head">
              <h3 class="card-title">Trade plan</h3>
              <span v-if="plan" class="badge" :class="plan.source === 'setup' ? 'badge--accent' : 'badge--unknown'">
                {{ plan.source === 'setup' ? 'From chart setup' : 'From day range' }}
              </span>
            </div>
            <template v-if="plan">
              <div class="plan-grid">
                <div class="pl entry"><span class="lk">Entry</span><span class="lv">{{ fmtPrice(plan.entry) }}</span></div>
                <div class="pl target"><span class="lk">Target (+2R)</span><span class="lv">{{ fmtPrice(plan.target) }}</span></div>
                <div class="pl stop"><span class="lk">Stop loss</span><span class="lv">{{ fmtPrice(plan.stop) }}</span></div>
                <div class="pl rr"><span class="lk">Risk / reward</span><span class="lv">{{ fmtRR(plan.reward_risk) }}</span></div>
              </div>
              <div class="levels">
                <div class="lvl"><span class="lk">Scale out (+1R)</span><span class="lv">{{ fmtPrice(plan.scale_out) }}</span></div>
                <div class="lvl"><span class="lk">Risk / share</span><span class="lv">{{ fmtPrice(plan.risk) }} <small>({{ plan.risk_pct.toFixed(1) }}%)</small></span></div>
                <div v-if="sel.setup?.ema9 != null" class="lvl"><span class="lk">9 EMA</span><span class="lv">{{ fmtPrice(sel.setup.ema9) }}</span></div>
              </div>
              <p class="plan-note">{{ plan.note }}</p>
              <p v-if="session && !session.tradeable" class="banner banner--note inline">Outside the 9:30–11:30 ET window — plan only, don't enter.</p>
              <PositionSizer :setup="plan" />
            </template>
            <p v-else class="empty">No long plan: the stock is red on the day or has no range yet. Wait for it to turn green and set a high of day.</p>
          </section>

          <!-- Chart setup (screener's read of the 1-min chart) -->
          <section class="card">
            <div class="card-head">
              <h3 class="card-title">Chart setup</h3>
              <span v-if="hasSetup" class="badge badge--accent">{{ patternName(sel.setup!.pattern) }} · {{ sel.setup!.stage }}</span>
              <span v-else class="badge badge--unknown">No setup yet</span>
            </div>
            <CandleChart :candles="selected.candles" :setup="sel.setup" />
            <ul v-if="hasSetup && sel.setup!.notes.length" class="notes">
              <li v-for="n in sel.setup!.notes" :key="n">{{ n }}</li>
            </ul>
          </section>

          <!-- Momentum / screener signals -->
          <section class="card">
            <div class="card-head">
              <h3 class="card-title">Five pillars</h3>
              <span class="badge" :class="passedCount === 5 ? 'badge--pass' : 'badge--accent'">{{ passedCount }} / 5 pillars</span>
            </div>
            <div class="signal-bar" role="img" :aria-label="`${passedCount} of 5 pillars passed`">
              <span class="signal-fill" :class="{ full: passedCount === 5 }" :style="{ width: (passedCount / 5 * 100) + '%' }" />
            </div>
            <PillarStrip :pillars="sel.pillars" />
            <p class="signal-note">Composite score {{ sel.score }} · {{ passedCount === 5 ? 'passes every pillar' : `${5 - passedCount} pillar${5 - passedCount === 1 ? '' : 's'} short of "in play"` }}.</p>
          </section>

          <!-- Catalyst -->
          <section class="card">
            <h3 class="card-title">Catalyst</h3>
            <p v-if="!selected.news.length" class="empty">No headlines in the last 48 hours — without a catalyst this isn't a Ross trade.</p>
            <div v-else class="news">
              <a v-for="n in selected.news" :key="n.url" :href="n.url" target="_blank" rel="noopener">
                <span class="headline">{{ n.headline }}</span>
                <span class="src">{{ n.source }} · {{ new Date(n.published).toLocaleString() }}</span>
              </a>
            </div>
          </section>
        </template>
      </div>
    </aside>
  </main>
</template>

<style scoped>
.page { max-width: 1240px; margin: 0 auto; padding: 28px 20px 90px; }

/* Header */
.top { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; margin-bottom: 18px; }
.brand h1 { font-family: var(--font-display); font-weight: 700; font-size: 32px; margin: 0; line-height: 1.05; letter-spacing: -.01em; }
.sub { margin: 6px 0 0; color: var(--muted); max-width: 60ch; }
.top-right { display: flex; align-items: center; gap: 14px; flex-shrink: 0; }
.clock { text-align: right; display: grid; gap: 2px; }
.time { font-weight: 600; font-size: 18px; font-variant-numeric: tabular-nums; }
.time small { color: var(--muted); font-size: 12px; font-weight: 500; }
.phase { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
.clock[data-phase="golden"] .phase, .clock[data-phase="open"] .phase { color: var(--pass); font-weight: 700; }
.clock[data-phase="midday"] .phase { color: var(--warn); }

.status-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: stretch; margin-bottom: 12px; }
.status-row > * { margin: 0; }
.advice {
  flex: 1 1 360px;
  padding: 10px 14px;
  border-left: 3px solid var(--line-strong);
  background: var(--surface);
  border-radius: 0 var(--radius) var(--radius) 0;
  font-size: 14px;
  color: var(--ink-soft);
  box-shadow: var(--shadow-sm);
}
.advice[data-phase="golden"], .advice[data-phase="open"] { border-left-color: var(--pass); }
.advice[data-phase="midday"] { border-left-color: var(--warn); }

/* Banners */
.banner { margin: 0 0 12px; padding: 10px 14px; border-radius: var(--radius); font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 8px; }
.banner--error { color: var(--fail); background: var(--fail-bg); border: 1px solid var(--fail); }
.banner--ok { color: var(--pass); background: var(--pass-bg); font-weight: 600; white-space: nowrap; }
.banner--note { color: var(--muted); background: var(--surface-3); border: 1px solid var(--line); display: block; }
.banner.inline { margin: 0; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--pass); box-shadow: 0 0 0 3px var(--pass-bg); }

/* Controls */
.controls { display: grid; gap: 14px; margin-bottom: 8px; }
.field { display: grid; gap: 6px; }
.field span { font-size: 13px; color: var(--ink-soft); font-weight: 600; }
.field span em { color: var(--muted); font-weight: 400; font-style: normal; }
.field small { color: var(--muted); font-size: 13px; }
textarea, input[type=number] {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 10px 12px;
  background: var(--surface-2);
  color: var(--ink);
  resize: vertical;
  width: 100%;
}
textarea:hover, input[type=number]:hover { border-color: var(--line-strong); }
textarea:focus-visible, input[type=number]:focus-visible { border-color: var(--accent); outline-offset: 0; }

.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.btn { border-radius: var(--radius); padding: 10px 18px; font-weight: 600; border: 1px solid transparent; display: inline-flex; align-items: center; gap: 8px; transition: background-color .15s ease, border-color .15s ease, opacity .15s ease; }
.btn--primary { background: var(--accent); color: var(--accent-ink); }
.btn--primary:hover:not(:disabled) { background: var(--accent-strong); }
.btn--primary:disabled { opacity: .5; cursor: default; }
.btn--ghost { background: var(--surface); border-color: var(--line); color: var(--ink); }
.btn--ghost:hover { border-color: var(--line-strong); background: var(--surface-2); }
.toggle { font-size: 13px; color: var(--muted); display: flex; gap: 6px; align-items: center; cursor: pointer; }
.toggle input { accent-color: var(--accent); }
.stamp { color: var(--muted); font-size: 13px; margin-left: auto; }
.spinner { width: 14px; height: 14px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: spin .7s linear infinite; flex-shrink: 0; }
@keyframes spin { to { transform: rotate(360deg); } }

.filters { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; padding-top: 12px; border-top: 1px solid var(--line); }
.filters label { display: grid; gap: 4px; font-size: 12px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .03em; }

/* Board + sidebar */
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 22px; align-items: start; }
.side { display: grid; gap: 14px; position: sticky; top: 16px; margin-top: 26px; }
.board { margin-top: 8px; min-width: 0; }
.board.refreshing .list { opacity: .7; transition: opacity .2s ease; }
.board h2 { font-family: var(--font-display); font-size: 19px; margin: 22px 0 12px; display: flex; align-items: baseline; gap: 8px; }
.count { color: var(--muted); font-weight: 400; font-size: 14px; }
.list { display: grid; gap: 12px; }
.empty { color: var(--muted); }
.empty.card { padding: 20px; }
.empty--hero { text-align: center; padding: 48px 24px; display: grid; gap: 6px; justify-items: center; }
.empty-icon { font-size: 34px; opacity: .7; }
.empty--hero p { margin: 0; color: var(--ink-soft); font-size: 16px; }
.empty--hero small { color: var(--muted); }
.skel-row { height: 150px; }
.slow-note { display: flex; align-items: center; gap: 8px; margin: 14px 0 0; font-size: 13px; color: var(--muted); }

.signals { display: grid; gap: 4px; }
.sig-grid { display: grid; gap: 6px; }
.sig-tile {
  display: flex; align-items: center; gap: 12px;
  padding: 7px 10px;
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  text-align: left;
}
.sig-tile:hover { border-color: var(--line-strong); }
.sig-tile.active { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.sig-tile.zero { opacity: .55; }
.sig-n { font-family: var(--font-display); font-weight: 700; font-size: 20px; min-width: 2ch; text-align: right; font-variant-numeric: tabular-nums; }
.side-note { margin: 6px 0 0; font-size: 12px; color: var(--muted); }
.link { background: none; border: 0; color: var(--accent); font-size: 12.5px; font-weight: 600; padding: 0; }

/* Drawer */
.drawer { position: fixed; inset: 0; background: rgba(5, 10, 18, .55); backdrop-filter: blur(2px); display: flex; justify-content: flex-end; z-index: 10; animation: fade .15s ease; }
@keyframes fade { from { opacity: 0; } }
.panel {
  width: min(640px, 100%);
  height: 100%;
  overflow-y: auto;
  background: var(--bg);
  padding: 26px 22px 60px;
  display: grid;
  gap: 16px;
  align-content: start;
  position: relative;
  box-shadow: var(--shadow-lg);
}
.close {
  position: absolute; top: 14px; right: 16px;
  width: 34px; height: 34px;
  display: grid; place-items: center;
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 50%; font-size: 22px; line-height: 1; color: var(--muted);
  z-index: 1;
}
.close:hover { color: var(--ink); border-color: var(--line-strong); }

.dhead { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-right: 40px; }
.dhead-id { display: flex; align-items: baseline; gap: 12px; min-width: 0; }
.dhead .ticker { font-family: var(--font-display); font-weight: 700; font-size: 36px; line-height: 1; }
.dhead .name { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.card-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 14px; }
.card > .card-title { margin-bottom: 14px; }

/* Stat grid */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.stat { display: grid; gap: 3px; padding: 10px 12px; background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); align-content: start; min-width: 0; }
.stat .k { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.stat .v { font-size: 19px; font-weight: 700; font-family: var(--font-display); white-space: nowrap; }
.stat .v.sm { font-size: 15px; }
.stat .s { font-size: 11px; color: var(--muted); line-height: 1.3; }
.stat .v.up { color: var(--pass); } .stat .v.down { color: var(--fail); }
.stat--rvol { background: var(--accent-bg); }
.stat--rvol[data-status="pass"] { background: var(--pass-bg); } .stat--rvol[data-status="pass"] .v { color: var(--pass); }
.stat--rvol[data-status="warn"] { background: var(--warn-bg); } .stat--rvol[data-status="warn"] .v { color: var(--warn); }
.stat--rvol[data-status="fail"] .v { color: var(--fail); }
.stat--rvol[data-status="unknown"] { background: var(--unknown-bg); } .stat--rvol[data-status="unknown"] .v { color: var(--muted); }

/* Signal reasons */
.reasons { display: grid; gap: 14px; }
.reason-group h4 { margin: 0 0 6px; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; }
.reason-group[data-impact="positive"] h4 { color: var(--pass); }
.reason-group[data-impact="negative"] h4 { color: var(--fail); }
.reason-group[data-impact="neutral"] h4 { color: var(--muted); }
.reason-group ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.reason-group li {
  display: grid; grid-template-columns: 96px 1fr; column-gap: 12px;
  padding: 8px 12px; background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius);
  border-left: 3px solid var(--line-strong); font-size: 14px;
}
.reason-group[data-impact="positive"] li { border-left-color: var(--pass); }
.reason-group[data-impact="negative"] li { border-left-color: var(--fail); }
.rf { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); padding-top: 2px; }
.rl { font-weight: 600; color: var(--ink); }
.rd { grid-column: 2; font-size: 12.5px; color: var(--muted); }

.signal-bar { height: 8px; background: var(--surface-3); border-radius: var(--radius-pill); overflow: hidden; margin-bottom: 14px; }
.signal-fill { display: block; height: 100%; background: var(--accent); border-radius: var(--radius-pill); transition: width .3s ease; }
.signal-fill.full { background: var(--pass); }
.signal-note { margin: 12px 0 0; font-size: 13px; color: var(--muted); }
.signal-note.top { margin: -4px 0 14px; color: var(--ink-soft); }

/* Trade plan */
.plan-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 8px; }
.pl { display: grid; gap: 3px; padding: 12px; border-radius: var(--radius); border: 1px solid var(--line); background: var(--surface-2); border-top: 3px solid var(--line-strong); }
.pl .lk { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.pl .lv { font-family: var(--font-display); font-weight: 700; font-size: 20px; }
.pl.entry { border-top-color: var(--accent); } .pl.entry .lv { color: var(--accent); }
.pl.target { border-top-color: var(--pass); } .pl.target .lv { color: var(--pass); }
.pl.stop { border-top-color: var(--fail); } .pl.stop .lv { color: var(--fail); }
.plan-note { margin: 0 0 12px; font-size: 13px; color: var(--muted); }
.notes { margin: 14px 0 0; padding-left: 18px; color: var(--muted); font-size: 14px; display: grid; gap: 4px; }

.levels { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px; }
.lvl { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 12px; background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); }
.lk { font-size: 12px; color: var(--muted); }
.lv { font-weight: 700; font-family: var(--font-display); white-space: nowrap; }
.lv small { color: var(--muted); font-weight: 500; font-family: var(--font); }

/* News */
.news { display: grid; gap: 8px; }
.news a { display: grid; gap: 3px; text-decoration: none; background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 11px 13px; font-size: 14px; transition: border-color .15s ease; }
.news a:hover { border-color: var(--accent); }
.news .headline { color: var(--ink); }
.src { font-size: 12px; color: var(--muted); }

/* Drawer skeletons */
.skel-head { height: 44px; width: 60%; }
.skel-block { height: 140px; }

@media (max-width: 1080px) {
  .layout { grid-template-columns: 1fr; }
  .side { position: static; order: -1; margin-top: 8px; grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); align-items: start; }
  .sig-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
}
@media (max-width: 720px) {
  .side { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .page { padding: 20px 14px 80px; }
  .top { flex-direction: column; }
  .top-right { width: 100%; justify-content: space-between; }
  .stat-grid, .plan-grid { grid-template-columns: repeat(2, 1fr); }
  .levels { grid-template-columns: 1fr; }
  .brand h1 { font-size: 28px; }
  .banner--ok { white-space: normal; }
  .reason-group li { grid-template-columns: 1fr; }
  .rd { grid-column: 1; }
}
</style>
