<script setup lang="ts">
import { computed, useState } from '#imports'
// Accepts a Setup or a TradePlan — both carry the same entry/stop/+1R/+2R levels.
type Levels = { entry?: number; stop?: number; scale_out?: number; target?: number; risk?: number }
const props = defineProps<{ setup: Levels }>()
const riskDollars = useState('riskDollars', () => 100)
const shares = computed(() => props.setup.risk ? Math.floor(riskDollars.value / props.setup.risk) : 0)
const cost = computed(() => shares.value * (props.setup.entry ?? 0))
const half = computed(() => Math.floor(shares.value / 2))
const gainHalf = computed(() => half.value * ((props.setup.scale_out ?? 0) - (props.setup.entry ?? 0)))
const gainRest = computed(() => (shares.value - half.value) * ((props.setup.target ?? 0) - (props.setup.entry ?? 0)))
</script>

<template>
  <div class="sizer">
    <label class="risk-input">
      <span>Max loss on this trade ($)</span>
      <input v-model.number="riskDollars" type="number" min="1" step="10">
    </label>

    <template v-if="shares > 0">
      <div class="summary">
        <div class="metric">
          <span class="k">Shares</span>
          <span class="v">{{ shares }}</span>
        </div>
        <div class="metric">
          <span class="k">Est. cost</span>
          <span class="v">${{ cost.toFixed(0) }}</span>
        </div>
        <div class="metric">
          <span class="k">Max loss</span>
          <span class="v risk">${{ riskDollars }}</span>
        </div>
      </div>
      <ol>
        <li>Buy <b>{{ shares }}</b> shares at <b>{{ setup.entry?.toFixed(2) }}</b> (≈ ${{ cost.toFixed(0) }}). Limit order, not market.</li>
        <li>Stop at <b>{{ setup.stop?.toFixed(2) }}</b> — a full stop-out costs ${{ riskDollars }}.</li>
        <li>At <b>{{ setup.scale_out?.toFixed(2) }}</b> sell {{ half }} shares (<span class="pos">+${{ gainHalf.toFixed(0) }}</span>) and move the stop to {{ setup.entry?.toFixed(2) }}. The trade is now risk-free.</li>
        <li>Sell the rest at <b>{{ setup.target?.toFixed(2) }}</b> (<span class="pos">+${{ gainRest.toFixed(0) }}</span>) — that's the 2:1.</li>
      </ol>
    </template>
    <p v-else class="empty">Risk per share is zero or unknown — no size can be computed.</p>
  </div>
</template>

<style scoped>
.sizer { display: grid; gap: 14px; }
.risk-input { display: grid; gap: 5px; font-size: 13px; color: var(--muted); max-width: 260px; }
.risk-input input {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 9px 11px;
  background: var(--surface-2);
  color: var(--ink);
}
.risk-input input:focus-visible { border-color: var(--accent); }

.summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.metric {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}
.metric .k { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.metric .v { font-size: 18px; font-weight: 700; font-family: var(--font-display); }
.metric .v.risk { color: var(--fail); }

ol { margin: 0; padding-left: 20px; display: grid; gap: 8px; font-size: 14px; color: var(--ink-soft); }
ol b { color: var(--ink); }
.pos { color: var(--pass); font-weight: 600; }
.empty { color: var(--muted); font-size: 13px; margin: 0; }
</style>
