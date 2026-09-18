<script setup lang="ts">
// Explicit imports: Nuxt auto-import breaks when the project path contains
// characters like "(" or ")" (e.g. a folder named "...-only(1)").
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useScreener } from '~/composables/useScreener'
import type { ScreenResult, Candle, NewsItem } from '~/composables/useScreener'
import StockRow from '~/components/StockRow.vue'
import PillarStrip from '~/components/PillarStrip.vue'
import CandleChart from '~/components/CandleChart.vue'
import PositionSizer from '~/components/PositionSizer.vue'
import RulesPanel from '~/components/RulesPanel.vue'
import ThemeToggle from '~/components/ThemeToggle.vue'

const { results, inPlayList, scannedAt, candlesAvailable, session, loading, error, thresholds, health, loadUniverse, scan, detail } = useScreener()

const symbolsText = ref('')
const showFilters = ref(false)
const showRules = ref(false)
const autoRefresh = ref(false)
const keyMissing = ref(false)
const finnhubOk = ref(false)
const finnhubError = ref('')
const backendDown = ref(false)
const selected = ref<{ result: ScreenResult; candles: Candle[]; news: NewsItem[] } | null>(null)
const detailLoading = ref(false)

const symbols = computed(() => symbolsText.value.split(/[\s,]+/).map(s => s.trim().toUpperCase()).filter(Boolean))
const inPlay = computed(() => results.value.filter(r => inPlayList.value.includes(r.symbol)))
const watching = computed(() => results.value.filter(r => !inPlayList.value.includes(r.symbol)))
const canScan = computed(() => !loading.value && symbols.value.length > 0)

const clock = ref('')
let clockTimer: number | undefined, refreshTimer: number | undefined
function tick() {
  clock.value = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(new Date())
}
const phaseLabel: Record<string, string> = {
  premarket: 'Pre-market', open: 'Opening drive', golden: 'Golden hours', midday: 'Midday chop', afterhours: 'After hours', closed: 'Closed'
}

onMounted(async () => {
  tick(); clockTimer = window.setInterval(tick, 1000)
  try {
    const h = await health(); keyMissing.value = !h.finnhub_key_set; finnhubOk.value = h.finnhub_ok; finnhubError.value = h.finnhub_error || ''; session.value = h.session
    symbolsText.value = (await loadUniverse()).join(' ')
  } catch { backendDown.value = true }
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
const passedCount = computed(() => selected.value ? selected.value.result.pillars.filter(p => p.status === 'pass').length : 0)
const fmtPrice = (n?: number) => n != null ? `$${n.toFixed(2)}` : '—'
const fmtFloat = (n?: number) => n != null ? `${(n / 1e6).toFixed(1)}M` : '—'
const fmtGap = (n?: number) => n != null ? `${n > 0 ? '+' : ''}${n.toFixed(1)}%` : '—'
const fmtRvol = (n?: number) => n != null ? `${n.toFixed(1)}×` : 'N/A'
const hasSetup = computed(() => {
  const s = selected.value?.result.setup
  return !!s && s.pattern !== 'none'
})
const hasPlan = computed(() => selected.value?.result.setup?.entry != null)
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

    <p v-if="session" class="advice" :data-phase="session.phase">{{ session.advice }}</p>

    <!-- Connection / status banners -->
    <p v-if="backendDown" class="banner banner--error">Backend isn't reachable on port 8000. Run <code>./run.sh</code> (or <code>make dev</code>) and reload.</p>
    <p v-else-if="keyMissing" class="banner banner--error">No Finnhub key found. Put it in <code>backend/.env</code> as <code>FINNHUB_API_KEY=…</code> and restart the backend.</p>
    <p v-else-if="finnhubError" class="banner banner--error">Finnhub rejected the key: {{ finnhubError }}</p>
    <p v-else-if="finnhubOk" class="banner banner--ok"><span class="live-dot" /> Connected to Finnhub · live data</p>
    <p v-if="scannedAt && !candlesAvailable" class="banner banner--note">Intraday candles aren't on the Finnhub free plan, so relative volume and chart setups show as unavailable — confirm those on your scanner and charts. The other four pillars are live.</p>

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
      <div class="list">
        <div v-for="i in 4" :key="i" class="skeleton skel-row" />
      </div>
    </section>

    <section v-else-if="results.length" class="board">
      <h2>In play <span class="count">{{ inPlay.length }} of 10 max</span></h2>
      <p v-if="!inPlay.length" class="empty card">Nothing passes all five pillars right now. That's normal outside the open — it's a filter, not a suggestion box.</p>
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

    <section v-else class="board">
      <div class="empty card empty--hero">
        <div class="empty-icon" aria-hidden="true">📈</div>
        <p>Paste today's gappers and scan to rank them by the five pillars.</p>
        <small>Best from 9:30 to 11:30 ET.</small>
      </div>
    </section>

    <!-- Detail drawer -->
    <aside v-if="selected || detailLoading" class="drawer" @click.self="selected = null">
      <div class="panel" role="dialog" aria-label="Stock detail">
        <button class="close" @click="selected = null" aria-label="Close">×</button>

        <template v-if="detailLoading">
          <div class="skeleton skel-head" />
          <div class="skeleton skel-block" />
          <div class="skeleton skel-block" />
        </template>

        <template v-else-if="selected">
          <!-- Header: identity + status -->
          <header class="dhead">
            <div class="dhead-id">
              <span class="ticker">{{ selected.result.symbol }}</span>
              <span class="name">{{ selected.result.name }}</span>
            </div>
            <span
              class="badge badge--dot"
              :class="selected.result.in_play ? 'badge--pass' : 'badge--unknown'"
            >{{ selected.result.in_play ? 'In play' : 'Watching' }}</span>
          </header>

          <!-- Stock information -->
          <section class="card">
            <h3 class="card-title">Stock information</h3>
            <div class="stat-grid">
              <div class="stat">
                <span class="k">Price</span>
                <span class="v">{{ fmtPrice(selected.result.price) }}</span>
              </div>
              <div class="stat">
                <span class="k">Gap</span>
                <span class="v" :class="{ up: (selected.result.gap_pct ?? 0) > 0, down: (selected.result.gap_pct ?? 0) < 0 }">{{ fmtGap(selected.result.gap_pct) }}</span>
              </div>
              <div class="stat">
                <span class="k">Rel. volume</span>
                <span class="v">{{ fmtRvol(selected.result.rvol) }}</span>
              </div>
              <div class="stat">
                <span class="k">Float</span>
                <span class="v">{{ fmtFloat(selected.result.shares_outstanding) }}</span>
              </div>
            </div>
          </section>

          <!-- Momentum / screener signals -->
          <section class="card">
            <div class="card-head">
              <h3 class="card-title">Momentum signals</h3>
              <span class="badge" :class="passedCount === 5 ? 'badge--pass' : 'badge--accent'">{{ passedCount }} / 5 pillars</span>
            </div>
            <div class="signal-bar" role="img" :aria-label="`${passedCount} of 5 pillars passed`">
              <span class="signal-fill" :class="{ full: passedCount === 5 }" :style="{ width: (passedCount / 5 * 100) + '%' }" />
            </div>
            <PillarStrip :pillars="selected.result.pillars" />
            <p class="signal-note">Composite score {{ selected.result.score }} · {{ passedCount === 5 ? 'passes every pillar' : `${5 - passedCount} pillar${5 - passedCount === 1 ? '' : 's'} short of "in play"` }}.</p>
          </section>

          <!-- Trade setup (screener's read of the chart) -->
          <section class="card">
            <div class="card-head">
              <h3 class="card-title">Trade setup</h3>
              <span v-if="hasSetup" class="badge badge--accent">{{ patternName(selected.result.setup!.pattern) }} · {{ selected.result.setup!.stage }}</span>
              <span v-else class="badge badge--unknown">No setup yet</span>
            </div>
            <CandleChart :candles="selected.candles" :setup="selected.result.setup" />
            <ul v-if="hasSetup && selected.result.setup!.notes.length" class="notes">
              <li v-for="n in selected.result.setup!.notes" :key="n">{{ n }}</li>
            </ul>
          </section>

          <!-- Technical levels + risk plan -->
          <section v-if="hasPlan" class="card">
            <div class="card-head">
              <h3 class="card-title">Risk &amp; position plan</h3>
              <span v-if="selected.result.setup!.reward_risk != null" class="badge badge--pass">{{ selected.result.setup!.reward_risk!.toFixed(1) }} : 1 R:R</span>
            </div>
            <div class="levels">
              <div class="lvl"><span class="lk">Entry</span><span class="lv entry">{{ fmtPrice(selected.result.setup!.entry) }}</span></div>
              <div class="lvl"><span class="lk">Stop</span><span class="lv stop">{{ fmtPrice(selected.result.setup!.stop) }}</span></div>
              <div class="lvl"><span class="lk">Scale out (+1R)</span><span class="lv">{{ fmtPrice(selected.result.setup!.scale_out) }}</span></div>
              <div class="lvl"><span class="lk">Target (+2R)</span><span class="lv target">{{ fmtPrice(selected.result.setup!.target) }}</span></div>
              <div v-if="selected.result.setup!.ema9 != null" class="lvl"><span class="lk">9 EMA</span><span class="lv">{{ fmtPrice(selected.result.setup!.ema9) }}</span></div>
              <div v-if="selected.result.setup!.risk != null" class="lvl"><span class="lk">Risk / share</span><span class="lv">{{ fmtPrice(selected.result.setup!.risk) }}</span></div>
            </div>
            <p v-if="session && !session.tradeable" class="banner banner--note inline">Outside the 9:30–11:30 ET window — plan only, don't enter.</p>
            <PositionSizer :setup="selected.result.setup!" />
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
.page { max-width: 900px; margin: 0 auto; padding: 28px 18px 90px; }

/* shared card shell */
.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
}

/* Header */
.top { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; margin-bottom: 14px; }
.brand h1 { font-family: var(--font-display); font-weight: 700; font-size: 34px; margin: 0; line-height: 1.05; letter-spacing: -.01em; }
.sub { margin: 6px 0 0; color: var(--muted); max-width: 52ch; }
.top-right { display: flex; align-items: center; gap: 14px; flex-shrink: 0; }
.clock { text-align: right; display: grid; gap: 2px; }
.time { font-weight: 600; font-size: 18px; }
.time small { color: var(--muted); font-size: 12px; font-weight: 500; }
.phase { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
.clock[data-phase="golden"] .phase, .clock[data-phase="open"] .phase { color: var(--pass); font-weight: 700; }
.clock[data-phase="midday"] .phase { color: var(--warn); }

.advice {
  margin: 0 0 16px;
  padding: 12px 16px;
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
.banner--ok { color: var(--pass); background: var(--pass-bg); font-weight: 600; }
.banner--note { color: var(--muted); background: var(--surface-3); border: 1px solid var(--line); max-width: none; }
.banner.inline { margin: 0; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--pass); box-shadow: 0 0 0 3px var(--pass-bg); }

/* Controls */
.controls { display: grid; gap: 14px; margin-bottom: 22px; }
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
.spinner { width: 14px; height: 14px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.filters { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; padding-top: 4px; border-top: 1px solid var(--line); }
.filters label { display: grid; gap: 4px; font-size: 12px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .03em; }

/* Board */
.board { margin-top: 8px; }
.board h2 { font-family: var(--font-display); font-size: 20px; margin: 26px 0 12px; display: flex; align-items: baseline; gap: 8px; }
.count { color: var(--muted); font-weight: 400; font-size: 14px; }
.list { display: grid; gap: 12px; }
.empty { color: var(--muted); }
.empty.card { padding: 20px; }
.empty--hero { text-align: center; padding: 48px 24px; display: grid; gap: 6px; justify-items: center; }
.empty-icon { font-size: 34px; opacity: .7; }
.empty--hero p { margin: 0; color: var(--ink-soft); font-size: 16px; }
.empty--hero small { color: var(--muted); }
.skel-row { height: 96px; }

/* Drawer */
.drawer { position: fixed; inset: 0; background: rgba(5, 10, 18, .55); backdrop-filter: blur(2px); display: flex; justify-content: flex-end; z-index: 10; animation: fade .15s ease; }
@keyframes fade { from { opacity: 0; } }
.panel {
  width: min(600px, 100%);
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

.card-title { font-family: var(--font-display); font-size: 15px; margin: 0; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 14px; }
.card > .card-title { margin-bottom: 14px; }

/* Stat grid */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.stat { display: grid; gap: 4px; padding: 12px; background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); }
.stat .k { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.stat .v { font-size: 20px; font-weight: 700; font-family: var(--font-display); }
.stat .v.up { color: var(--pass); } .stat .v.down { color: var(--fail); }

/* Signal progress */
.signal-bar { height: 8px; background: var(--surface-3); border-radius: var(--radius-pill); overflow: hidden; margin-bottom: 14px; }
.signal-fill { display: block; height: 100%; background: var(--accent); border-radius: var(--radius-pill); transition: width .3s ease; }
.signal-fill.full { background: var(--pass); }
.signal-note { margin: 12px 0 0; font-size: 13px; color: var(--muted); }

/* Trade setup notes */
.notes { margin: 14px 0 0; padding-left: 18px; color: var(--muted); font-size: 14px; display: grid; gap: 4px; }

/* Levels */
.levels { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 14px; }
.lvl { display: flex; align-items: center; justify-content: space-between; padding: 9px 12px; background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); }
.lk { font-size: 12px; color: var(--muted); }
.lv { font-weight: 700; font-family: var(--font-display); }
.lv.entry { color: var(--accent); }
.lv.stop { color: var(--fail); }
.lv.target { color: var(--pass); }

/* News */
.news { display: grid; gap: 8px; }
.news a { display: grid; gap: 3px; text-decoration: none; background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 11px 13px; font-size: 14px; transition: border-color .15s ease; }
.news a:hover { border-color: var(--accent); }
.news .headline { color: var(--ink); }
.src { font-size: 12px; color: var(--muted); }

/* Drawer skeletons */
.skel-head { height: 44px; width: 60%; }
.skel-block { height: 140px; }

@media (max-width: 640px) {
  .top { flex-direction: column; }
  .top-right { width: 100%; justify-content: space-between; }
  .clock { text-align: right; }
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .levels { grid-template-columns: 1fr; }
  .brand h1 { font-size: 28px; }
}
</style>
