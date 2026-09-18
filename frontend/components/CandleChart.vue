<script setup lang="ts">
import { computed } from 'vue'
import type { Candle, Setup } from '~/composables/useScreener'
const props = defineProps<{ candles: Candle[]; setup?: Setup | null }>()
const W = 640, H = 220, PAD = 8
const view = computed(() => {
  const cs = props.candles.slice(-90)
  if (!cs.length) return null
  const lo = Math.min(...cs.map(c => c.l)), hi = Math.max(...cs.map(c => c.h))
  const span = hi - lo || 1
  const y = (v: number) => PAD + (H - 2 * PAD) * (1 - (v - lo) / span)
  const cw = (W - 2 * PAD) / cs.length
  const bars = cs.map((c, i) => ({
    x: PAD + i * cw + cw * 0.2, w: cw * 0.6, cx: PAD + i * cw + cw / 2,
    yo: y(c.o), yc: y(c.c), yh: y(c.h), yl: y(c.l), up: c.c >= c.o
  }))
  const lines = props.setup && props.setup.pattern !== 'none'
    ? [{ k: 'entry', v: props.setup.entry }, { k: 'stop', v: props.setup.stop }, { k: 'target', v: props.setup.target }]
        .filter(l => l.v != null && l.v! >= lo && l.v! <= hi).map(l => ({ ...l, y: y(l.v!) }))
    : []
  return { bars, lines, lo, hi }
})
</script>

<template>
  <div v-if="view" class="chart-wrap">
    <svg :viewBox="`0 0 ${W} ${H}`" class="chart" role="img" aria-label="One-minute candles" preserveAspectRatio="none">
      <g v-for="(b, i) in view.bars" :key="i" :class="b.up ? 'up' : 'down'">
        <line :x1="b.cx" :x2="b.cx" :y1="b.yh" :y2="b.yl" />
        <rect :x="b.x" :width="b.w" :y="Math.min(b.yo, b.yc)" :height="Math.max(1, Math.abs(b.yo - b.yc))" rx="0.5" />
      </g>
      <g v-for="l in view.lines" :key="l.k" :class="l.k">
        <line x1="0" :x2="W" :y1="l.y" :y2="l.y" />
        <text :x="W - 4" :y="l.y - 4" text-anchor="end">{{ l.k }} {{ l.v!.toFixed(2) }}</text>
      </g>
    </svg>
    <div class="axis">
      <span>H {{ view.hi.toFixed(2) }}</span>
      <span>L {{ view.lo.toFixed(2) }}</span>
    </div>
  </div>
  <p v-else class="empty">
    No intraday candles — Finnhub's free plan doesn't include them.
    Read the setup on your broker's 1-minute chart.
  </p>
</template>

<style scoped>
.chart-wrap { position: relative; }
.chart {
  width: 100%;
  height: auto;
  display: block;
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}
.up line, .up rect { stroke: var(--pass); fill: var(--pass); }
.down line, .down rect { stroke: var(--fail); fill: var(--fail); }
.entry line, .stop line, .target line { stroke-dasharray: 4 4; stroke-width: 1.2; }
.entry line  { stroke: var(--accent); }
.stop line   { stroke: var(--fail); }
.target line { stroke: var(--pass); }
.entry text  { fill: var(--accent); }
.stop text   { fill: var(--fail); }
.target text { fill: var(--pass); }
text { font-size: 11px; font-weight: 600; fill: var(--muted); }
.axis {
  position: absolute;
  top: 6px; left: 8px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  font-size: 11px;
  color: var(--muted);
  pointer-events: none;
}
.empty { color: var(--muted); font-size: 13px; margin: 0; }
</style>
