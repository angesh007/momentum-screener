<script setup lang="ts">
import { computed, ref } from 'vue'
import { fmtPrice, fmtGap, fmtShares, fmtRvol, SIGNALS } from '~/composables/format'
import { useElementWidth, niceTicks } from '~/composables/useElementWidth'
import type { ScreenResult, Thresholds } from '~/composables/useScreener'

// Gap % (x) against float (y, log) — the two pillars that define a low-float
// runner. The shaded corner is where both pillars pass with current thresholds.
const props = defineProps<{ results: ScreenResult[]; inPlay: string[]; th: Thresholds }>()
const emit = defineEmits<{ open: [symbol: string] }>()

const PAD_L = 46, PAD_R = 12, PAD_T = 12, PLOT_H = 210, X_AXIS = 34

const wrap = ref<HTMLElement | null>(null)
const W = useElementWidth(wrap, 360)

const pts = computed(() => props.results.filter(r => !r.error && r.gap_pct != null && r.shares_outstanding && r.shares_outstanding > 0))
const missing = computed(() => props.results.filter(r => !r.error && !pts.value.includes(r)).map(r => r.symbol))
const fmtFloat = (v: number) => v >= 1e9 ? `${+(v / 1e9).toFixed(1)}B` : `${+(v / 1e6).toFixed(v < 1e7 ? 1 : 0)}M`

const view = computed(() => {
  const ps = pts.value
  if (!ps.length) return null
  const plotW = Math.max(160, W.value - PAD_L - PAD_R)
  const H = PAD_T + PLOT_H + X_AXIS

  let x0 = Math.min(0, ...ps.map(r => r.gap_pct!)), x1 = Math.max(props.th.gap_pct_min, ...ps.map(r => r.gap_pct!))
  const xp = (x1 - x0 || 1) * 0.06; x0 -= xp; x1 += xp
  const floats = ps.map(r => r.shares_outstanding!)
  let l0 = Math.log10(Math.min(props.th.float_ideal, ...floats)), l1 = Math.log10(Math.max(props.th.float_max, ...floats))
  const lp = (l1 - l0 || 1) * 0.06; l0 -= lp; l1 += lp

  const x = (v: number) => PAD_L + plotW * (v - x0) / (x1 - x0)
  const y = (v: number) => PAD_T + PLOT_H * (1 - (Math.log10(v) - l0) / (l1 - l0))

  const yTicks: { v: number; y: number }[] = []
  for (let e = Math.ceil(l0); e <= Math.floor(l1); e++) yTicks.push({ v: 10 ** e, y: y(10 ** e) })
  const xTicks = niceTicks(x0, x1, Math.max(3, Math.round(plotW / 90))).map(v => ({ v, x: x(v) }))

  const dots = ps.map(r => ({ r, cx: x(r.gap_pct!), cy: y(r.shares_outstanding!), play: props.inPlay.includes(r.symbol) }))
    // In-play last so they paint on top.
    .sort((a, b) => Number(a.play) - Number(b.play))

  const zx = x(props.th.gap_pct_min), zy = y(props.th.float_max)
  return {
    H, plotW, x0, dots, yTicks, xTicks,
    zone: { x: zx, y: zy, w: PAD_L + plotW - zx, h: PAD_T + PLOT_H - zy },
    gapX: zx, idealY: y(props.th.float_ideal), maxY: zy, zeroX: x(0)
  }
})

const active = ref<string | null>(null)
const tip = computed(() => {
  const d = view.value?.dots.find(d => d.r.symbol === active.value)
  if (!d) return null
  const style: Record<string, string> = d.cx > W.value / 2 ? { right: `${W.value - d.cx + 14}px` } : { left: `${d.cx + 14}px` }
  style[d.cy > PAD_T + PLOT_H / 2 ? 'bottom' : 'top'] = d.cy > PAD_T + PLOT_H / 2 ? `${(view.value!.H - d.cy) + 8}px` : `${d.cy + 8}px`
  return { d, style }
})
</script>

<template>
  <section class="card gf" aria-labelledby="gf-title">
    <header>
      <h3 id="gf-title" class="card-title">Gap vs float</h3>
      <p class="sub">Shaded: gap ≥ {{ th.gap_pct_min }}% and float ≤ {{ fmtShares(th.float_max) }} · float = shares outstanding</p>
    </header>

    <template v-if="view">
      <div ref="wrap" class="frame">
        <svg :width="W" :height="view.H" class="chart" role="group" aria-label="Gap percent versus float, one dot per ticker">
          <rect class="zone" :x="view.zone.x" :y="view.zone.y" :width="Math.max(0, view.zone.w)" :height="Math.max(0, view.zone.h)" />
          <g class="grid">
            <line v-for="t in view.yTicks" :key="'y' + t.v" :x1="PAD_L" :x2="PAD_L + view.plotW" :y1="t.y" :y2="t.y" />
          </g>
          <g class="ax">
            <text v-for="t in view.yTicks" :key="'yl' + t.v" :x="PAD_L - 6" :y="t.y + 4" text-anchor="end">{{ fmtFloat(t.v) }}</text>
            <text v-for="t in view.xTicks" :key="'xl' + t.v" :x="t.x" :y="PAD_T + PLOT_H + 15" text-anchor="middle">{{ t.v > 0 ? '+' : '' }}{{ t.v }}%</text>
            <text :x="PAD_L + view.plotW" :y="view.H - 2" text-anchor="end" class="ax-title">Gap % →</text>
            <line class="baseline" :x1="PAD_L" :x2="PAD_L + view.plotW" :y1="PAD_T + PLOT_H" :y2="PAD_T + PLOT_H" />
            <line class="baseline" :x1="view.zeroX" :x2="view.zeroX" :y1="PAD_T" :y2="PAD_T + PLOT_H" />
          </g>
          <g class="th">
            <line class="gap" :x1="view.gapX" :x2="view.gapX" :y1="PAD_T" :y2="PAD_T + PLOT_H" />
            <line class="ideal" :x1="PAD_L" :x2="PAD_L + view.plotW" :y1="view.idealY" :y2="view.idealY" />
            <text :x="PAD_L + 4" :y="view.idealY - 4">ideal ≤ {{ fmtShares(th.float_ideal) }}</text>
          </g>

          <g
            v-for="d in view.dots" :key="d.r.symbol" class="pt" :class="{ play: d.play, on: active === d.r.symbol }"
            tabindex="0" role="button"
            :aria-label="`${d.r.symbol}: gap ${fmtGap(d.r.gap_pct)}, float ${fmtShares(d.r.shares_outstanding)}${d.play ? ', in play' : ''}`"
            @pointerenter="active = d.r.symbol" @pointerleave="active = null"
            @focus="active = d.r.symbol" @blur="active = null"
            @click="emit('open', d.r.symbol)" @keydown.enter="emit('open', d.r.symbol)"
          >
            <circle class="hit" :cx="d.cx" :cy="d.cy" r="12" />
            <circle class="dot" :cx="d.cx" :cy="d.cy" r="4.5" />
            <text v-if="d.play" class="lbl" :x="d.cx + 8" :y="d.cy - 7">{{ d.r.symbol }}</text>
          </g>
        </svg>

        <div v-if="tip" class="tip" :style="tip.style" role="status">
          <b>{{ tip.d.r.symbol }}</b><span v-if="tip.d.play" class="pl"> · in play</span>
          <dl>
            <dt>Gap</dt><dd>{{ fmtGap(tip.d.r.gap_pct) }}</dd>
            <dt>Float</dt><dd>{{ fmtShares(tip.d.r.shares_outstanding) }}</dd>
            <dt>Price</dt><dd>{{ fmtPrice(tip.d.r.price) }}</dd>
            <dt>Rel. volume</dt><dd>{{ fmtRvol(tip.d.r.rvol) }}</dd>
            <template v-if="tip.d.r.signal"><dt>Signal</dt><dd>{{ SIGNALS[tip.d.r.signal].label }}</dd></template>
          </dl>
        </div>
      </div>
      <div class="legend">
        <span><i class="key play" />In play (labelled)</span>
        <span><i class="key" />Watching</span>
        <span><i class="key-zone" />Both pillars pass</span>
      </div>
    </template>
    <p v-else class="empty">No gap / float data for this scan.</p>
    <p v-if="view && missing.length" class="foot">Not plotted (no float or gap from Finnhub): {{ missing.join(', ') }}</p>
  </section>
</template>

<style scoped>
.gf { display: grid; gap: 12px; min-width: 0; }
.sub { margin: 4px 0 0; font-size: 12.5px; color: var(--muted); }
.frame { position: relative; min-width: 0; contain: inline-size; }
.chart { display: block; overflow: visible; }
.zone { fill: var(--pass-bg); }
.grid line { stroke: var(--line); }
.ax text { font-size: 11px; fill: var(--muted); }
.ax .ax-title { font-size: 10.5px; }
.ax .baseline { stroke: var(--line-strong); }
.th line { stroke-width: 1.2; stroke-dasharray: 4 4; }
.th .gap { stroke: var(--accent); }
.th .ideal { stroke: var(--pass); opacity: .7; }
.th text { font-size: 10.5px; fill: var(--muted); }

.pt { cursor: pointer; outline: none; }
.hit { fill: transparent; }
.dot { fill: var(--muted); stroke: var(--surface); stroke-width: 2; transition: r .12s ease; }
.pt.play .dot { fill: var(--pass); }
.pt.on .dot { r: 6.5; stroke: var(--ink); stroke-width: 1.5; }
.pt:focus-visible .dot { stroke: var(--accent); stroke-width: 2.5; }
.lbl { font-size: 11px; font-weight: 700; fill: var(--ink); paint-order: stroke; stroke: var(--surface); stroke-width: 3px; pointer-events: none; }

.tip {
  position: absolute; z-index: 2; min-width: 170px;
  padding: 9px 12px; background: var(--surface); border: 1px solid var(--line-strong);
  border-radius: var(--radius); box-shadow: var(--shadow); font-size: 12.5px; pointer-events: none;
}
.tip .pl { color: var(--pass); font-weight: 600; }
.tip dl { margin: 6px 0 0; display: grid; grid-template-columns: auto auto; gap: 2px 14px; }
.tip dt { color: var(--muted); }
.tip dd { margin: 0; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }

.legend { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 12px; color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.key { width: 9px; height: 9px; border-radius: 50%; background: var(--muted); display: inline-block; }
.key.play { background: var(--pass); }
.key-zone { width: 12px; height: 10px; border-radius: 2px; background: var(--pass-bg); border: 1px solid var(--line); display: inline-block; }
.empty, .foot { margin: 0; font-size: 12.5px; color: var(--muted); }
</style>
