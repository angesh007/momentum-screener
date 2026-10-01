<script setup lang="ts">
import { computed, ref } from 'vue'
import { SIGNALS, SIGNAL_ORDER } from '~/composables/format'
import type { SignalKind } from '~/composables/useScreener'

// Share of the scan in each signal. The tiles beside it are the legend and the
// exact counts, so this only has to show proportion at a glance.
const props = defineProps<{ counts: Record<SignalKind, number>; active?: SignalKind | null }>()
const emit = defineEmits<{ pick: [k: SignalKind] }>()

const R = 44, STROKE = 14, SIZE = (R + STROKE) * 2, C = 2 * Math.PI * R, GAP = 2

const total = computed(() => SIGNAL_ORDER.reduce((s, k) => s + props.counts[k], 0))
const segs = computed(() => {
  let acc = 0
  const n = SIGNAL_ORDER.filter(k => props.counts[k]).length
  return SIGNAL_ORDER.filter(k => props.counts[k]).map(k => {
    const len = props.counts[k] / total.value * C
    // 2px surface gap between segments; a lone segment is a full ring.
    const seg = { k, dash: `${Math.max(0.5, len - (n > 1 ? GAP : 0))} ${C}`, offset: -acc }
    acc += len
    return seg
  })
})
const hover = ref<SignalKind | null>(null)
const focus = computed(() => hover.value ?? props.active ?? null)
const pctOf = (k: SignalKind) => Math.round(props.counts[k] / (total.value || 1) * 100)
</script>

<template>
  <div v-if="total" class="donut">
    <svg :width="SIZE" :height="SIZE" :viewBox="`0 0 ${SIZE} ${SIZE}`" role="img"
      :aria-label="SIGNAL_ORDER.filter(k => counts[k]).map(k => `${SIGNALS[k].label} ${counts[k]}`).join(', ')">
      <g :transform="`rotate(-90 ${SIZE / 2} ${SIZE / 2})`">
        <circle class="track" :cx="SIZE / 2" :cy="SIZE / 2" :r="R" :stroke-width="STROKE" />
        <circle
          v-for="s in segs" :key="s.k" class="seg" :class="[s.k, { dim: focus && focus !== s.k }]"
          :cx="SIZE / 2" :cy="SIZE / 2" :r="R" :stroke-width="STROKE"
          :stroke-dasharray="s.dash" :stroke-dashoffset="s.offset"
          @pointerenter="hover = s.k" @pointerleave="hover = null" @click="emit('pick', s.k)"
        >
          <title>{{ SIGNALS[s.k].label }}: {{ counts[s.k] }} ({{ pctOf(s.k) }}%)</title>
        </circle>
      </g>
    </svg>
    <div class="center" aria-hidden="true">
      <template v-if="focus && counts[focus]">
        <b>{{ pctOf(focus) }}%</b><span>{{ SIGNALS[focus].label }}</span>
      </template>
      <template v-else><b>{{ total }}</b><span>scored</span></template>
    </div>
  </div>
</template>

<style scoped>
.donut { position: relative; width: max-content; margin: 2px auto 8px; }
svg { display: block; }
.track { fill: none; stroke: var(--surface-3); }
.seg { fill: none; cursor: pointer; transition: opacity .15s ease; }
.seg.dim { opacity: .3; }
.strong_buy  { stroke: var(--pass); }
.buy         { stroke: color-mix(in srgb, var(--pass) 50%, var(--surface)); }
.hold        { stroke: var(--line-strong); }
.sell        { stroke: color-mix(in srgb, var(--fail) 50%, var(--surface)); }
.strong_sell { stroke: var(--fail); }
.center { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; pointer-events: none; line-height: 1.1; }
.center b { font-size: 20px; font-weight: 700; color: var(--ink); }
.center span { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
</style>
