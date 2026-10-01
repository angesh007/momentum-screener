<script setup lang="ts">
import { computed, ref } from 'vue'
import { fmtPrice, fmtGap, SIGNALS } from '~/composables/format'
import { useElementWidth, niceTicks } from '~/composables/useElementWidth'
import type { ScreenResult } from '~/composables/useScreener'

// One candle per ticker: today's open / high / low / last from Finnhub's quote,
// expressed as % from the previous close so every ticker shares one axis.
const props = defineProps<{ results: ScreenResult[]; inPlay: string[]; gapMin: number }>()
const emit = defineEmits<{ open: [symbol: string] }>()

const AXIS_R = 48, PAD_T = 12, PLOT_H = 210

const wrap = ref<HTMLElement | null>(null)
const W = useElementWidth(wrap)
const etDate = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric' })

const rows = computed(() => props.results
  .filter(r => !r.error && r.prev_close && r.open != null && r.high != null && r.low != null && r.price != null)
  .map(r => {
    const pc = r.prev_close!, p = (v: number) => (v - pc) / pc * 100
    return { r, o: p(r.open!), h: p(r.high!), l: p(r.low!), c: p(r.price!) }
  })
  .sort((a, b) => b.c - a.c))
const missing = computed(() => props.results.filter(r => !r.error && !rows.value.some(x => x.r.symbol === r.symbol)).map(r => r.symbol))
const asOf = computed(() => {
  const t = Math.max(0, ...rows.value.map(x => x.r.quote_time ?? 0))
  return t ? etDate.format(new Date(t * 1000)) : ''
})

const view = computed(() => {
  const rs = rows.value
  if (!rs.length) return null
  // Rotated ticker labels hang left of their candle, so the first needs room.
  const rotate = (W.value - AXIS_R - 6) / rs.length < 44
  const padL = rotate ? 26 : 6
  const plotW = Math.max(160, W.value - AXIS_R - padL)
  const cw = plotW / rs.length
  const xAxis = rotate ? 46 : 24
  const H = PAD_T + PLOT_H + xAxis

  let lo = Math.min(0, ...rs.map(x => x.l)), hi = Math.max(0, ...rs.map(x => x.h))
  if (props.gapMin > 0) hi = Math.max(hi, props.gapMin)
  const pad = (hi - lo || 1) * 0.06
  lo -= pad; hi += pad
  const y = (v: number) => PAD_T + PLOT_H * (1 - (v - lo) / (hi - lo))
  const bodyW = Math.max(2, Math.min(cw * 0.56, 22))

  const candles = rs.map((x, i) => {
    const cx = padL + cw * i + cw / 2
    return {
      ...x, cx, up: x.c >= x.o,
      yh: y(x.h), yl: y(x.l), top: y(Math.max(x.o, x.c)), bh: Math.max(1.5, Math.abs(y(x.o) - y(x.c)))
    }
  })
  return { H, padL, plotW, cw, rotate, bodyW, candles, y0: y(0), yGap: y(props.gapMin), ticks: niceTicks(lo, hi, 4).map(v => ({ v, y: y(v) })) }
})

const active = ref<number | null>(null)
function onMove(ev: PointerEvent) {
  const v = view.value; if (!v) return
  const r = (ev.currentTarget as SVGElement).getBoundingClientRect()
  active.value = Math.max(0, Math.min(v.candles.length - 1, Math.floor((ev.clientX - r.left - v.padL) / v.cw)))
}
function onKey(ev: KeyboardEvent) {
  const n = view.value?.candles.length ?? 0
  if (!n) return
  if (ev.key === 'ArrowLeft' || ev.key === 'ArrowRight') {
    ev.preventDefault()
    active.value = Math.max(0, Math.min(n - 1, (active.value ?? -1) + (ev.key === 'ArrowRight' ? 1 : -1)))
  } else if (ev.key === 'Enter' && active.value != null) {
    emit('open', view.value!.candles[active.value].r.symbol)
  }
}
function onClick() {
  if (active.value != null && view.value) emit('open', view.value.candles[active.value].r.symbol)
}
const tip = computed(() => {
  const v = view.value, i = active.value
  if (!v || i == null || !v.candles[i]) return null
  const c = v.candles[i]
  return { c, style: c.cx > W.value / 2 ? { right: `${W.value - c.cx + 14}px` } : { left: `${c.cx + 14}px` } }
})
const summary = computed(() => rows.value.map(x => `${x.r.symbol} ${fmtGap(x.c)}`).join(', '))
</script>

<template>
  <section class="card sc" aria-labelledby="sc-title">
    <header class="head">
      <div>
        <h3 id="sc-title" class="card-title">Today's session</h3>
        <p class="sub">Open · high · low · last per ticker, % from previous close{{ asOf ? ` · ${asOf}` : '' }} · click a candle for detail</p>
      </div>
    </header>

    <template v-if="view">
      <div ref="wrap" class="frame">
        <svg
          :width="W" :height="view.H" role="img" tabindex="0" class="chart"
          :aria-label="`Today's change from previous close: ${summary}. Arrow keys step through tickers, Enter opens one.`"
          @pointermove="onMove" @pointerleave="active = null" @click="onClick"
          @blur="active = null" @keydown="onKey"
        >
          <g class="grid">
            <line v-for="t in view.ticks" :key="t.v" :x1="view.padL" :x2="view.padL + view.plotW" :y1="t.y" :y2="t.y" />
          </g>
          <g class="ax">
            <text v-for="t in view.ticks" :key="t.v" :x="view.padL + view.plotW + 8" :y="t.y + 4">{{ t.v > 0 ? '+' : '' }}{{ t.v }}%</text>
          </g>
          <line class="zero" :x1="view.padL" :x2="view.padL + view.plotW" :y1="view.y0" :y2="view.y0" />
          <g v-if="gapMin > 0" class="gapline">
            <line :x1="view.padL" :x2="view.padL + view.plotW" :y1="view.yGap" :y2="view.yGap" />
            <text :x="view.padL + 4" :y="view.yGap - 5">Gap ≥ {{ gapMin }}%</text>
          </g>

          <rect v-if="tip" class="hl" :x="tip.c.cx - view.cw / 2" :width="view.cw" :y="PAD_T" :height="PLOT_H" />
          <g v-for="(c, i) in view.candles" :key="c.r.symbol" :class="c.up ? 'up' : 'down'">
            <line class="wick" :x1="c.cx" :x2="c.cx" :y1="c.yh" :y2="c.yl" />
            <rect class="body" :x="c.cx - view.bodyW / 2" :width="view.bodyW" :y="c.top" :height="c.bh" rx="1.5" />
            <text
              class="tk" :class="{ play: inPlay.includes(c.r.symbol), on: active === i }"
              :transform="view.rotate ? `translate(${c.cx + 4},${PAD_T + PLOT_H + 12}) rotate(-50)` : undefined"
              :x="view.rotate ? 0 : c.cx" :y="view.rotate ? 0 : PAD_T + PLOT_H + 16"
              :text-anchor="view.rotate ? 'end' : 'middle'"
            >{{ c.r.symbol }}</text>
          </g>
        </svg>

        <div v-if="tip" class="tip" :style="tip.style" role="status">
          <div class="tip-head"><b>{{ tip.c.r.symbol }}</b><span v-if="tip.c.r.name"> · {{ tip.c.r.name }}</span></div>
          <dl>
            <dt>Last</dt><dd>{{ fmtPrice(tip.c.r.price) }} <small>{{ fmtGap(tip.c.c) }}</small></dd>
            <dt>Open</dt><dd>{{ fmtPrice(tip.c.r.open) }} <small>{{ fmtGap(tip.c.o) }}</small></dd>
            <dt>High</dt><dd>{{ fmtPrice(tip.c.r.high) }} <small>{{ fmtGap(tip.c.h) }}</small></dd>
            <dt>Low</dt><dd>{{ fmtPrice(tip.c.r.low) }} <small>{{ fmtGap(tip.c.l) }}</small></dd>
            <dt>Prev close</dt><dd>{{ fmtPrice(tip.c.r.prev_close) }}</dd>
            <template v-if="tip.c.r.signal"><dt>Signal</dt><dd>{{ SIGNALS[tip.c.r.signal].label }}</dd></template>
          </dl>
        </div>
      </div>
      <div class="legend">
        <span><i class="key up" />Last ≥ open</span>
        <span><i class="key down" />Last &lt; open</span>
        <span><i class="key-line zero" />Prev close</span>
        <span v-if="gapMin > 0"><i class="key-line gap" />Gap threshold</span>
        <span><b class="play-key">TICK</b> in play</span>
      </div>
    </template>
    <p v-else class="empty">No quote range for this scan yet — Finnhub returns open/high/low once the stock has traded today.</p>
    <p v-if="view && missing.length" class="foot">No range from Finnhub: {{ missing.join(', ') }}</p>
  </section>
</template>

<style scoped>
.sc { display: grid; gap: 12px; min-width: 0; }
.sub { margin: 4px 0 0; font-size: 12.5px; color: var(--muted); }
.frame { position: relative; min-width: 0; contain: inline-size; }
.chart { display: block; touch-action: pan-y; cursor: pointer; }
.chart:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.grid line { stroke: var(--line); }
.ax text { font-size: 11px; fill: var(--muted); }
.zero { stroke: var(--line-strong); stroke-width: 1.2; }
.gapline line { stroke: var(--accent); stroke-dasharray: 4 4; stroke-width: 1.2; }
.gapline text { font-size: 11px; font-weight: 600; fill: var(--accent); paint-order: stroke; stroke: var(--surface); stroke-width: 3px; }
.hl { fill: var(--surface-3); }
.wick { stroke-width: 1.4; }
.up .wick { stroke: var(--pass); } .up .body { fill: var(--pass); }
.down .wick { stroke: var(--fail); } .down .body { fill: var(--fail); }
.tk { font-size: 11px; font-weight: 600; fill: var(--muted); }
.tk.play { fill: var(--ink); font-weight: 700; }
.tk.on { fill: var(--accent); }

.tip {
  position: absolute; top: 6px; z-index: 2; min-width: 210px;
  padding: 9px 12px; background: var(--surface); border: 1px solid var(--line-strong);
  border-radius: var(--radius); box-shadow: var(--shadow); font-size: 12.5px; pointer-events: none;
}
.tip-head span { color: var(--muted); }
.tip dl { margin: 6px 0 0; display: grid; grid-template-columns: auto auto; gap: 2px 14px; }
.tip dt { color: var(--muted); }
.tip dd { margin: 0; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
.tip dd small { color: var(--muted); font-weight: 500; margin-left: 4px; }

.legend { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 12px; color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.key { width: 8px; height: 12px; border-radius: 2px; display: inline-block; }
.key.up { background: var(--pass); } .key.down { background: var(--fail); }
.key-line { width: 14px; height: 0; display: inline-block; border-top: 2px solid var(--line-strong); }
.key-line.gap { border-top: 2px dashed var(--accent); }
.play-key { color: var(--ink); font-size: 11px; }
.empty, .foot { margin: 0; font-size: 12.5px; color: var(--muted); }
</style>
