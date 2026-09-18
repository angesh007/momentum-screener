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
</script>

<template>
  <main class="page">
    <header class="top">
      <div>
        <h1>Momentum board</h1>
        <p class="sub">Scores your gapper list on the five pillars, live from Finnhub, and hands you a sized trade plan.</p>
      </div>
      <div class="clock" :data-phase="session?.phase">
        <span class="time">{{ clock }} ET</span>
        <span class="phase">{{ session ? phaseLabel[session.phase] : '—' }}</span>
      </div>
    </header>

    <p v-if="session" class="advice" :data-phase="session.phase">{{ session.advice }}</p>
    <p v-if="backendDown" class="error">Backend isn't reachable on port 8000. Run <code>./run.sh</code> (or <code>make dev</code>) and reload.</p>
    <p v-else-if="keyMissing" class="error">No Finnhub key found. Put it in <code>backend/.env</code> as <code>FINNHUB_API_KEY=…</code> and restart the backend.</p>
    <p v-else-if="finnhubError" class="error">Finnhub rejected the key: {{ finnhubError }}</p>
    <p v-else-if="finnhubOk" class="status">Connected to Finnhub · live data</p>
    <p v-if="scannedAt && !candlesAvailable" class="note">Intraday candles aren't on the Finnhub free plan, so relative volume and chart setups show as unavailable — confirm those on your scanner and charts. The other four pillars are live.</p>

    <section class="controls">
      <label class="field">
        <span>Tickers to scan (pre-filled from backend/universe.txt)</span>
        <textarea v-model="symbolsText" rows="2" spellcheck="false" placeholder="SOUN BBAI IONQ …" />
        <small>Finnhub's free plan has no screener, so paste the gappers from your pre-market scanner here.</small>
      </label>

      <div class="actions">
        <button class="primary" :disabled="!canScan" @click="runScan">
          {{ loading ? 'Scanning…' : `Scan ${symbols.length} tickers` }}
        </button>
        <button class="ghost" @click="showFilters = !showFilters">{{ showFilters ? 'Hide' : 'Edit' }} thresholds</button>
        <button class="ghost" @click="showRules = !showRules">{{ showRules ? 'Hide' : 'Show' }} the rules</button>
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
      <RulesPanel v-if="showRules" :th="thresholds" />
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section v-if="results.length" class="board">
      <h2>In play <span class="count">{{ inPlay.length }} of 10 max</span></h2>
      <p v-if="!inPlay.length" class="empty">Nothing passes all five pillars right now. That's normal outside the open — it's a filter, not a suggestion box.</p>
      <div class="list">
        <StockRow v-for="(r, i) in inPlay" :key="r.symbol" :r="r" :rank="i + 1" @open="open" />
      </div>
      <h2 v-if="watching.length">Watching <span class="count">{{ watching.length }}</span></h2>
      <div class="list">
        <StockRow v-for="(r, i) in watching" :key="r.symbol" :r="r" :rank="i + 1" @open="open" />
      </div>
    </section>
    <section v-else-if="!loading" class="board">
      <p class="empty">Paste today's gappers and scan to rank them by the five pillars. Best from 9:30 to 11:30 ET.</p>
    </section>

    <aside v-if="selected || detailLoading" class="drawer" @click.self="selected = null">
      <div class="panel">
        <button class="close" @click="selected = null" aria-label="Close">×</button>
        <p v-if="detailLoading" class="empty">Loading…</p>
        <template v-else-if="selected">
          <div class="dhead">
            <span class="ticker">{{ selected.result.symbol }}</span>
            <span class="name">{{ selected.result.name }}</span>
          </div>
          <PillarStrip :pillars="selected.result.pillars" />
          <CandleChart :candles="selected.candles" :setup="selected.result.setup" />

          <div v-if="selected.result.setup" class="setup">
            <h3>{{ patternName(selected.result.setup.pattern) }} <small>{{ selected.result.setup.stage }}</small></h3>
            <ul><li v-for="n in selected.result.setup.notes" :key="n">{{ n }}</li></ul>
            <p v-if="session && !session.tradeable" class="warn">Outside the 9:30–11:30 ET window — plan only, don't enter.</p>
            <PositionSizer v-if="selected.result.setup.entry" :setup="selected.result.setup" />
          </div>

          <div class="news">
            <h3>Catalyst</h3>
            <p v-if="!selected.news.length" class="empty">No headlines in the last 48 hours — without a catalyst this isn't a Ross trade.</p>
            <a v-for="n in selected.news" :key="n.url" :href="n.url" target="_blank" rel="noopener">
              <span class="src">{{ n.source }}, {{ new Date(n.published).toLocaleString() }}</span>
              {{ n.headline }}
            </a>
          </div>
        </template>
      </div>
    </aside>
  </main>
</template>

<style scoped>
.page { max-width: 880px; margin: 0 auto; padding: 24px 16px 80px; }
.top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 10px; }
h1 { font-family: var(--font-display); font-weight: 700; font-size: 34px; margin: 0; line-height: 1.05; }
.sub { margin: 6px 0 0; color: var(--muted); max-width: 52ch; }
.clock { text-align: right; display: grid; gap: 2px; flex-shrink: 0; }
.time { font-weight: 600; font-size: 18px; }
.phase { font-size: 13px; color: var(--muted); }
.clock[data-phase="golden"] .phase, .clock[data-phase="open"] .phase { color: var(--pass); font-weight: 600; }
.clock[data-phase="midday"] .phase { color: var(--warn); }
.advice { margin: 0 0 20px; padding: 10px 14px; border-left: 4px solid var(--line); background: var(--surface); font-size: 14px; }
.advice[data-phase="golden"], .advice[data-phase="open"] { border-left-color: var(--pass); }
.advice[data-phase="midday"] { border-left-color: var(--warn); }
.error { color: var(--fail); margin: 0 0 12px; }
.note { color: var(--muted); font-size: 13px; margin: 0 0 12px; max-width: 70ch; }
.status { color: var(--pass); font-size: 13px; font-weight: 600; margin: 0 0 12px; }
code { background: var(--surface); padding: 1px 5px; border-radius: 3px; }

.controls { display: grid; gap: 12px; margin-bottom: 28px; }
.field { display: grid; gap: 6px; }
.field span { font-size: 13px; color: var(--muted); }
.field small { color: var(--muted); font-size: 13px; }
textarea, input[type=number] { border: 1px solid var(--line); border-radius: 4px; padding: 10px 12px; background: var(--surface); color: var(--ink); resize: vertical; width: 100%; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.primary { background: var(--ink); color: #fff; border: 0; border-radius: 4px; padding: 10px 18px; font-weight: 600; }
.primary:disabled { opacity: .5; cursor: default; }
.ghost { background: transparent; border: 1px solid var(--line); border-radius: 4px; padding: 9px 14px; color: var(--ink); }
.toggle { font-size: 13px; color: var(--muted); display: flex; gap: 6px; align-items: center; }
.stamp { color: var(--muted); font-size: 13px; }
.filters { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
.filters label { display: grid; gap: 4px; font-size: 13px; color: var(--muted); }

.board h2 { font-family: var(--font-display); font-size: 20px; margin: 24px 0 10px; }
.count { color: var(--muted); font-weight: 400; margin-left: 6px; font-size: 14px; }
.list { display: grid; gap: 10px; }
.empty { color: var(--muted); }

.drawer { position: fixed; inset: 0; background: rgba(20,33,61,.45); display: flex; justify-content: flex-end; z-index: 10; }
.panel { width: min(580px, 100%); height: 100%; overflow-y: auto; background: var(--bg); padding: 24px 20px 60px; display: grid; gap: 18px; align-content: start; position: relative; }
.close { position: absolute; top: 12px; right: 14px; background: transparent; border: 0; font-size: 26px; color: var(--muted); }
.dhead { display: flex; align-items: baseline; gap: 12px; }
.dhead .ticker { font-family: var(--font-display); font-weight: 700; font-size: 36px; line-height: 1; }
.dhead .name { color: var(--muted); }
h3 { font-family: var(--font-display); font-size: 18px; margin: 0 0 8px; }
h3 small { color: var(--muted); font-weight: 600; margin-left: 8px; }
.setup { display: grid; gap: 10px; }
ul { margin: 0; padding-left: 18px; color: var(--muted); font-size: 14px; }
.warn { margin: 0; color: var(--warn); font-size: 14px; font-weight: 600; }
.news { display: grid; gap: 8px; }
.news a { display: grid; gap: 2px; text-decoration: none; background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 10px 12px; font-size: 14px; }
.news a:hover { border-color: var(--ink); }
.src { font-size: 12px; color: var(--muted); }
@media (max-width: 600px) { .top { flex-direction: column; } .clock { text-align: left; } }
</style>
