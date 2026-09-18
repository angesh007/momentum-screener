<script setup lang="ts">
import { computed, useState } from '#imports'
import type { Setup } from '~/composables/useScreener'
const props = defineProps<{ setup: Setup }>()
const riskDollars = useState('riskDollars', () => 100)
const shares = computed(() => props.setup.risk ? Math.floor(riskDollars.value / props.setup.risk) : 0)
const cost = computed(() => shares.value * (props.setup.entry ?? 0))
const half = computed(() => Math.floor(shares.value / 2))
const gainHalf = computed(() => half.value * ((props.setup.scale_out ?? 0) - (props.setup.entry ?? 0)))
const gainRest = computed(() => (shares.value - half.value) * ((props.setup.target ?? 0) - (props.setup.entry ?? 0)))
</script>

<template>
  <div class="sizer">
    <label>
      <span>Max loss on this trade ($)</span>
      <input v-model.number="riskDollars" type="number" min="1" step="10">
    </label>
    <ol v-if="shares > 0">
      <li>Buy <b>{{ shares }}</b> shares at <b>{{ setup.entry?.toFixed(2) }}</b> (≈ ${{ cost.toFixed(0) }}). Limit order, not market.</li>
      <li>Stop at <b>{{ setup.stop?.toFixed(2) }}</b> — a full stop-out costs ${{ riskDollars }}.</li>
      <li>At <b>{{ setup.scale_out?.toFixed(2) }}</b> sell {{ half }} shares (+${{ gainHalf.toFixed(0) }}) and move the stop to {{ setup.entry?.toFixed(2) }}. The trade is now risk-free.</li>
      <li>Sell the rest at <b>{{ setup.target?.toFixed(2) }}</b> (+${{ gainRest.toFixed(0) }}) — that's the 2:1.</li>
    </ol>
    <p v-else class="empty">Risk per share is zero or unknown — no size can be computed.</p>
  </div>
</template>

<style scoped>
.sizer { display: grid; gap: 10px; }
label { display: grid; gap: 4px; font-size: 13px; color: var(--muted); max-width: 240px; }
input { border: 1px solid var(--line); border-radius: 4px; padding: 8px 10px; background: var(--surface); color: var(--ink); }
ol { margin: 0; padding-left: 20px; display: grid; gap: 6px; font-size: 14px; }
.empty { color: var(--muted); font-size: 13px; margin: 0; }
</style>
