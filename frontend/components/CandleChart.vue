<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Candle, Setup, TradePlan } from '~/composables/useScreener'
import { fmtPrice } from '~/composables/format'
import { useElementWidth, niceTicks } from '~/composables/useElementWidth'

/** Today's quote as a single daily candle — used when intraday candles are
 *  unavailable (Finnhub free plan). Every field comes from /quote. */
export interface DayOHLC { t?: number | null; o?: number | null; h?: number | null; l?: number | null; c?: number | null; pc?: number | null }

const props = defineProps<{ candles: Candle[]; setup?: Setup | null; plan?: TradePlan | null; day?: DayOHLC | null }>()

const MAX_BARS = 90
const AXIS_R = 58, PAD_L = 4, PAD_T = 10, X_AXIS = 22, VOL_H = 56, VOL_GAP = 10

const wrap = ref<HTMLElement | null>(null)
const W = useElementWidth(wrap)

const etTime = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false })
const etDate = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric' })
const etMinute = (t: number) => { const [h, m] = etTime.format(new Date(t * 1000)).split(':').map(Number); return h * 60 + m }
const fmtVol = (v: number) => v >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(1)}K` : v.toFixed(0)
const pct = (a: number, b: number) => `${a >= b ? '+' : ''}${((a - b) / b * 100).toFixed(2)}%`

function ema(values: number[], period: number) {
  // Same recurrence as backend/app/patterns.py:ema — drawn, not re-scored.
  const k = 2 / (period + 1), out: number[] = []
  values.forEach((v, i) => out.push(i ? v * k + out[i - 1] * (1 - k) : v))
  return out
}

const mode = computed<'intraday' | 'daily' | null>(() => {
  if (props.candles.length) return 'intraday'
  const d = props.day
  return d && d.o != null && d.h != null && d.l != null && d.c != null ? 'daily' : null
})

type Bar = Candle & { ema?: number }
const bars = computed<Bar[]>(() => {
  if (mode.value === 'intraday') {
    const e = ema(props.candles.map(c => c.c), 9)
    const off = Math.max(0, props.candles.length - MAX_BARS)
    return props.candles.slice(off).map((c, i) => ({ ...c, ema: e[off + i] }))
  }
  if (mode.value === 'daily') {
    const d = props.day!
    return [{ t: d.t ?? 0, o: d.o!, h: d.h!, l: d.l!, c: d.c!, v: NaN }]
  }
  return []
})
const hasVolume = computed(() => mode.value === 'intraday' && bars.value.some(b => b.v > 0))

const levels = computed(() => {
  const p = props.plan, s = props.setup
  const out: { k: string; label: string; v: number }[] = []
  if (p) {
    out.push({ k: 'target', label: 'Target', v: p.target }, { k: 'scale', label: '+1R', v: p.scale_out },
      { k: 'entry', label: 'Entry', v: p.entry }, { k: 'stop', label: 'Stop', v: p.stop })
  } else if (s && s.pattern !== 'none') {
    if (s.target != null) out.push({ k: 'target', label: 'Target', v: s.target })
    if (s.entry != null) out.push({ k: 'entry', label: 'Entry', v: s.entry })
    if (s.stop != null) out.push({ k: 'stop', label: 'Stop', v: s.stop })
  }
  const pc = props.day?.pc
  if (pc != null) out.push({ k: 'pc', label: 'Prev close', v: pc })
  return out
})

const view = computed(() => {
  const bs = bars.value
  if (!bs.length) return null
  const daily = mode.value === 'daily'
  const priceH = daily ? 190 : 220
  const volTop = PAD_T + priceH + VOL_GAP
  const H = PAD_T + priceH + (hasVolume.value ? VOL_GAP + VOL_H : 0) + X_AXIS
  const plotW = Math.max(120, W.value - AXIS_R - PAD_L)

  let lo = Math.min(...bs.map(b => b.l)), hi = Math.max(...bs.map(b => b.h))
  // Plan levels (and prev close on the daily candle) always fit; intraday prev
  // close only shows when it's already inside the candles' range.
  for (const l of levels.value) {
    if (l.k === 'pc' && !daily) continue
    lo = Math.min(lo, l.v); hi = Math.max(hi, l.v)
  }
  const padY = (hi - lo || hi * 0.02 || 1) * 0.06
  lo -= padY; hi += padY
  const y = (v: number) => PAD_T + priceH * (1 - (v - lo) / (hi - lo))

  const cw = plotW / bs.length
  const bodyW = Math.max(1, Math.min(cw * 0.68, daily ? 26 : 14))
  const cx = (i: number) => PAD_L + cw * i + cw / 2

  const vMax = hasVolume.value ? Math.max(...bs.map(b => b.v)) : 0
  const vy = (v: number) => volTop + VOL_H * (1 - v / (vMax || 1))

  const candles = bs.map((b, i) => ({
    x: cx(i), up: b.c >= b.o,
    yh: y(b.h), yl: y(b.l), top: y(Math.max(b.o, b.c)), h: Math.max(1, Math.abs(y(b.o) - y(b.c))),
    vy: hasVolume.value ? vy(b.v) : 0
  }))
  const emaPath = !daily && bs.length > 1
    ? bs.map((b, i) => `${i ? 'L' : 'M'}${cx(i).toFixed(1)},${y(b.ema!).toFixed(1)}`).join('')
    : ''

  const yTicks = niceTicks(lo, hi, 4).map(v => ({ v, y: y(v) }))
  const decimals = hi - lo < 0.5 ? 3 : 2

  let xTicks: { x: number; label: string }[]
  if (daily) {
    xTicks = [{ x: cx(0), label: bs[0].t ? etDate.format(new Date(bs[0].t * 1000)) : 'Today' }]
  } else {
    const every = [5, 10, 15, 30, 60, 120].find(m => (m * cw) >= 64) ?? 120
    xTicks = bs.map((b, i) => ({ b, i })).filter(({ b }) => etMinute(b.t) % every === 0)
      .map(({ b, i }) => ({ x: cx(i), label: etTime.format(new Date(b.t * 1000)) }))
      .filter(t => t.x >= PAD_L + 16 && t.x <= PAD_L + plotW - 16)   // keep labels inside the frame
  }

  // Level labels sit at the left edge; nudge apart so they never overlap.
  const lv = levels.value
    .filter(l => daily || l.k !== 'pc' || (l.v >= lo && l.v <= hi))
    .map(l => ({ ...l, y: y(l.v), ty: y(l.v) - 4 }))
    .sort((a, b) => a.y - b.y)
  for (let i = 1; i < lv.length; i++) if (lv[i].ty - lv[i - 1].ty < 13) lv[i].ty = lv[i - 1].ty + 13

  return { H, plotW, priceH, volTop, candles, emaPath, yTicks, xTicks, decimals, cw, bodyW, lv, vMax }
})

// ---- Hover / keyboard crosshair ------------------------------------------
const active = ref<number | null>(null)
function onMove(ev: PointerEvent) {
  const v = view.value; if (!v) return
  const r = (ev.currentTarget as SVGElement).getBoundingClientRect()
  const i = Math.floor((ev.clientX - r.left - PAD_L) / v.cw)
  active.value = Math.max(0, Math.min(bars.value.length - 1, i))
}
function onKey(ev: KeyboardEvent) {
  const n = bars.value.length
  if (ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight') return
  ev.preventDefault()
  const cur = active.value ?? n - 1
  active.value = Math.max(0, Math.min(n - 1, cur + (ev.key === 'ArrowRight' ? 1 : -1)))
}
const tip = computed(() => {
  const v = view.value, i = active.value
  if (!v || i == null || !bars.value[i]) return null
  const b = bars.value[i], c = v.candles[i]
  const when = mode.value === 'daily'
    ? (b.t ? `${etDate.format(new Date(b.t * 1000))} · ${etTime.format(new Date(b.t * 1000))} ET` : 'Today')
    : `${etTime.format(new Date(b.t * 1000))} ET`
  const left = c.x > W.value / 2
  return { b, c, when, style: left ? { right: `${W.value - c.x + 12}px` } : { left: `${c.x + 12}px` } }
})
const summary = computed(() => {
  const bs = bars.value; if (!bs.length) return ''
  if (mode.value === 'daily') {
    const b = bs[0]; return `Today's candle: open ${b.o}, high ${b.h}, low ${b.l}, last ${b.c}`
  }
  return `${bs.length} one-minute candles from ${etTime.format(new Date(bs[0].t * 1000))} to ${etTime.format(new Date(bs[bs.length - 1].t * 1000))} ET. Last close ${bs[bs.length - 1].c}. Use arrow keys to step through candles.`
})
</script>

<template>
  <div class="cc">
    <template v-if="view">
      <div ref="wrap" class="frame">
      <svg
        :width="W" :height="view.H" class="chart" role="img" tabindex="0"
        :aria-label="summary"
        @pointermove="onMove" @pointerleave="active = null"
        @focus="active = active ?? bars.length - 1" @blur="active = null" @keydown="onKey"
      >
        <!-- grid + price axis -->
        <g class="grid">
          <line v-for="t in view.yTicks" :key="t.v" :x1="PAD_L" :x2="PAD_L + view.plotW" :y1="t.y" :y2="t.y" />
        </g>
        <g class="ax">
          <text v-for="t in view.yTicks" :key="t.v" :x="PAD_L + view.plotW + 8" :y="t.y + 4">{{ t.v.toFixed(view.decimals) }}</text>
          <text v-for="t in view.xTicks" :key="t.label + t.x" :x="t.x" :y="view.H - 6" text-anchor="middle">{{ t.label }}</text>
          <line class="baseline" :x1="PAD_L" :x2="PAD_L + view.plotW" :y1="PAD_T + view.priceH" :y2="PAD_T + view.priceH" />
        </g>

        <!-- trade-plan levels -->
        <g v-for="l in view.lv" :key="l.k" class="lvl" :class="l.k">
          <line :x1="PAD_L" :x2="PAD_L + view.plotW" :y1="l.y" :y2="l.y" />
          <text :x="PAD_L + 6" :y="l.ty">{{ l.label }} {{ fmtPrice(l.v) }}</text>
        </g>

        <!-- candles -->
        <g v-for="(c, i) in view.candles" :key="i" :class="[c.up ? 'up' : 'down', { dim: active != null && active !== i }]">
          <line class="wick" :x1="c.x" :x2="c.x" :y1="c.yh" :y2="c.yl" />
          <rect class="body" :x="c.x - view.bodyW / 2" :width="view.bodyW" :y="c.top" :height="c.h" rx="1" />
          <rect v-if="hasVolume" class="vol" :x="c.x - view.bodyW / 2" :width="view.bodyW" :y="c.vy" :height="Math.max(0, view.volTop + VOL_H - c.vy)" />
        </g>
        <path v-if="view.emaPath" class="ema" :d="view.emaPath" />

        <!-- volume pane axis -->
        <g v-if="hasVolume" class="ax">
          <line class="baseline" :x1="PAD_L" :x2="PAD_L + view.plotW" :y1="view.volTop + VOL_H" :y2="view.volTop + VOL_H" />
          <text :x="PAD_L + view.plotW + 8" :y="view.volTop + 9">{{ fmtVol(view.vMax) }}</text>
          <text :x="PAD_L + view.plotW + 8" :y="view.volTop + VOL_H">Vol</text>
        </g>

        <!-- crosshair -->
        <line v-if="tip" class="cross" :x1="tip.c.x" :x2="tip.c.x" :y1="PAD_T" :y2="view.H - X_AXIS" />
      </svg>

      <div v-if="tip" class="tip" :style="{ ...tip.style, top: '8px' }" role="status">
        <div class="tip-when">{{ tip.when }}</div>
        <dl>
          <dt>Open</dt><dd>{{ fmtPrice(tip.b.o) }}</dd>
          <dt>High</dt><dd>{{ fmtPrice(tip.b.h) }}</dd>
          <dt>Low</dt><dd>{{ fmtPrice(tip.b.l) }}</dd>
          <dt>{{ mode === 'daily' ? 'Last' : 'Close' }}</dt><dd :class="tip.c.up ? 'up' : 'down'">{{ fmtPrice(tip.b.c) }}</dd>
          <dt>vs open</dt><dd>{{ pct(tip.b.c, tip.b.o) }}</dd>
          <template v-if="mode === 'daily' && day?.pc"><dt>vs prev close</dt><dd>{{ pct(tip.b.c, day.pc) }}</dd></template>
          <template v-if="tip.b.ema != null"><dt>9 EMA</dt><dd>{{ fmtPrice(tip.b.ema) }}</dd></template>
          <template v-if="hasVolume"><dt>Volume</dt><dd>{{ fmtVol(tip.b.v) }}</dd></template>
        </dl>
      </div>
      </div>

      <div class="legend">
        <span><i class="key up" />Up</span>
        <span><i class="key down" />Down</span>
        <span v-if="view.emaPath"><i class="key-line ema" />9 EMA</span>
        <span v-if="hasVolume"><i class="key vol" />Volume</span>
        <span class="src">
          {{ mode === 'daily'
            ? "Today's candle from the live quote — 1-minute candles need Finnhub's paid plan"
            : `1-minute candles · last ${bars.length}` }}
        </span>
      </div>
    </template>
    <p v-else class="empty">
      No price data to chart — Finnhub returned no quote range and no intraday candles for this symbol.
    </p>
  </div>
</template>

<style scoped>
.cc { position: relative; min-width: 0; }
.frame { position: relative; contain: inline-size; background: var(--surface-2); border: 1px solid var(--line); border-radius: var(--radius); }
.chart { display: block; touch-action: pan-y; border-radius: var(--radius); }
.chart:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.grid line { stroke: var(--line); stroke-width: 1; }
.ax text { font-size: 11px; fill: var(--muted); font-variant-numeric: tabular-nums; }
.ax .baseline { stroke: var(--line-strong); }

.wick { stroke-width: 1.2; }
.up .wick { stroke: var(--pass); } .up .body { fill: var(--pass); }
.down .wick { stroke: var(--fail); } .down .body { fill: var(--fail); }
.vol { opacity: .45; }
.up .vol { fill: var(--pass); } .down .vol { fill: var(--fail); }
.dim { opacity: .55; }
.ema { fill: none; stroke: var(--ema); stroke-width: 2; stroke-linejoin: round; }

.lvl line { stroke-dasharray: 4 4; stroke-width: 1.2; }
.lvl text { font-size: 11px; font-weight: 600; paint-order: stroke; stroke: var(--surface-2); stroke-width: 3px; }
.entry line { stroke: var(--accent); } .entry text { fill: var(--accent); }
.stop line { stroke: var(--fail); } .stop text { fill: var(--fail); }
.target line { stroke: var(--pass); } .target text { fill: var(--pass); }
.scale line { stroke: var(--pass); opacity: .55; } .scale text { fill: var(--muted); }
.pc line { stroke: var(--muted); stroke-dasharray: 2 3; } .pc text { fill: var(--muted); }

.cross { stroke: var(--ink-soft); stroke-width: 1; pointer-events: none; }

.tip {
  position: absolute; z-index: 2; min-width: 168px;
  padding: 8px 11px;
  background: var(--surface); border: 1px solid var(--line-strong); border-radius: var(--radius);
  box-shadow: var(--shadow); font-size: 12.5px; pointer-events: none;
}
.tip-when { color: var(--muted); font-size: 11.5px; margin-bottom: 4px; }
.tip dl { margin: 0; display: grid; grid-template-columns: auto auto; gap: 1px 14px; }
.tip dt { color: var(--muted); }
.tip dd { margin: 0; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; color: var(--ink); }

.legend { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; margin-top: 8px; font-size: 12px; color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.key { width: 8px; height: 12px; border-radius: 2px; display: inline-block; }
.key.up { background: var(--pass); } .key.down { background: var(--fail); }
.key.vol { background: var(--muted); opacity: .5; }
.key-line { width: 14px; height: 2px; display: inline-block; border-radius: 1px; }
.key-line.ema { background: var(--ema); }
.legend .src { margin-left: auto; font-size: 11.5px; }
.empty { color: var(--muted); font-size: 13px; margin: 0; }
</style>
