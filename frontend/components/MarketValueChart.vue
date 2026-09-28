<script setup lang="ts">
import { computed, ref } from 'vue'
import { fmtMoney, fmtPrice, fmtShares, SIGNALS } from '~/composables/format'
import type { ScreenResult } from '~/composables/useScreener'

const props = defineProps<{ results: ScreenResult[]; inPlay: string[] }>()
defineEmits<{ open: [symbol: string] }>()

// Finnhub's free plan has no market-cap history, so this compares today's
// live market value across the scanned list instead of over time.
const rows = computed(() => {
  const withCap = props.results.filter(r => r.market_cap != null && r.market_cap > 0)
  const max = Math.max(...withCap.map(r => r.market_cap!), 1)
  return withCap
    .slice()
    .sort((a, b) => b.market_cap! - a.market_cap!)
    .map(r => ({ r, pct: (r.market_cap! / max) * 100 }))
})
const missing = computed(() => props.results.filter(r => !r.error && (r.market_cap == null || r.market_cap <= 0)).map(r => r.symbol))

const hover = ref<{ r: ScreenResult; top: number } | null>(null)
function show(r: ScreenResult, ev: Event) {
  const el = ev.currentTarget as HTMLElement
  hover.value = { r, top: el.offsetTop + el.offsetHeight }
}
</script>

<template>
  <section class="card mv" aria-labelledby="mv-title">
    <header class="mv-head">
      <div>
        <h3 id="mv-title" class="card-title">Market value</h3>
        <p class="sub">Live price × shares outstanding · largest first · click a bar for detail</p>
      </div>
      <span class="legend-note"><span class="dot" aria-hidden="true" /> in play</span>
    </header>

    <div v-if="rows.length" class="plot" role="list" @mouseleave="hover = null">
      <button
        v-for="{ r, pct } in rows"
        :key="r.symbol"
        class="bar-row"
        role="listitem"
        :aria-label="`${r.symbol} market value ${fmtMoney(r.market_cap)}`"
        @click="$emit('open', r.symbol)"
        @mouseenter="show(r, $event)"
        @focus="show(r, $event)"
        @blur="hover = null"
      >
        <span class="tk">
          <span v-if="inPlay.includes(r.symbol)" class="dot" aria-hidden="true" />{{ r.symbol }}
        </span>
        <span class="track">
          <span class="bar" :style="{ width: `max(calc((100% - 72px) * ${pct / 100}), 3px)` }" />
          <span class="val">{{ fmtMoney(r.market_cap) }}</span>
        </span>
      </button>

      <div v-if="hover" class="tip" :style="{ top: `${hover.top + 4}px` }" role="status">
        <b>{{ hover.r.symbol }}</b><span v-if="hover.r.name" class="tip-name"> · {{ hover.r.name }}</span>
        <dl>
          <dt>Market value</dt><dd>{{ fmtMoney(hover.r.market_cap) }}</dd>
          <dt>Price</dt><dd>{{ fmtPrice(hover.r.price) }}</dd>
          <dt>Shares out</dt><dd>{{ fmtShares(hover.r.shares_outstanding) }}</dd>
          <template v-if="hover.r.signal"><dt>Signal</dt><dd>{{ SIGNALS[hover.r.signal].label }}</dd></template>
        </dl>
      </div>
    </div>
    <p v-else class="empty">No market value data for this scan.</p>
    <p v-if="missing.length" class="foot">No market value from Finnhub: {{ missing.join(', ') }}</p>
  </section>
</template>

<style scoped>
.mv { display: grid; gap: 14px; }
.mv-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.sub { margin: 4px 0 0; font-size: 12.5px; color: var(--muted); }
.legend-note { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); white-space: nowrap; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--pass); flex-shrink: 0; }

.plot { position: relative; display: grid; gap: 2px; }
.bar-row {
  display: grid;
  grid-template-columns: 64px 1fr;
  align-items: center;
  gap: 10px;
  padding: 4px 6px;
  margin: 0 -6px;
  background: none;
  border: 0;
  border-radius: 6px;
  text-align: left;
  color: inherit;
}
.bar-row:hover, .bar-row:focus-visible { background: var(--surface-2); }
.tk { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; font-size: 13px; color: var(--ink-soft); }
.track { display: flex; align-items: center; gap: 8px; min-width: 0; border-left: 1px solid var(--line-strong); }
/* Bars: ≤ 24px thick, square at the baseline, 4px rounded data end. */
.bar {
  display: block;
  height: 14px;
  flex-shrink: 0;
  background: var(--accent);
  border-radius: 0 4px 4px 0;
  transition: width .3s ease, filter .15s ease;
}
.bar-row:hover .bar, .bar-row:focus-visible .bar { filter: brightness(1.15); }
.val { font-size: 12.5px; font-weight: 600; color: var(--ink-soft); white-space: nowrap; font-variant-numeric: tabular-nums; }

.tip {
  position: absolute;
  left: 74px;
  z-index: 2;
  min-width: 200px;
  padding: 10px 12px;
  background: var(--surface);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  font-size: 12.5px;
  pointer-events: none;
}
.tip-name { color: var(--muted); }
.tip dl { margin: 6px 0 0; display: grid; grid-template-columns: auto auto; gap: 2px 14px; }
.tip dt { color: var(--muted); }
.tip dd { margin: 0; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
.empty, .foot { margin: 0; font-size: 12.5px; color: var(--muted); }
</style>
