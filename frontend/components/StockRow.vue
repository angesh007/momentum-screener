<script setup lang="ts">
import { computed } from 'vue'
import PillarStrip from '~/components/PillarStrip.vue'
import type { ScreenResult } from '~/composables/useScreener'
const props = defineProps<{ r: ScreenResult; rank: number }>()
defineEmits<{ open: [symbol: string] }>()
const setupLabel = computed(() => {
  const s = props.r.setup
  if (!s || s.pattern === 'none') return null
  return `${s.pattern === 'bull_flag' ? 'Bull flag' : 'Flat top'} · ${s.stage}`
})
</script>

<template>
  <button class="row" :class="{ play: r.in_play, err: !!r.error }" @click="$emit('open', r.symbol)">
    <div class="head">
      <span class="ticker">{{ r.symbol }}</span>
      <span v-if="r.gap_pct != null" class="gap" :class="{ up: r.gap_pct > 0, down: r.gap_pct < 0 }">
        {{ r.gap_pct > 0 ? '+' : '' }}{{ r.gap_pct.toFixed(1) }}%
      </span>
      <span v-if="r.price != null" class="price">${{ r.price.toFixed(2) }}</span>
      <span class="score" aria-label="pillars passed">{{ r.pillars.filter(p => p.status === 'pass').length }}/5</span>
    </div>
    <p v-if="r.error" class="error">Couldn't load: {{ r.error }}</p>
    <template v-else>
      <PillarStrip :pillars="r.pillars" />
      <div class="foot">
        <span v-if="setupLabel" class="setup">{{ setupLabel }}</span>
        <span v-else class="setup quiet">No setup yet</span>
        <span v-if="r.catalyst" class="news">{{ r.catalyst.headline }}</span>
      </div>
    </template>
  </button>
</template>

<style scoped>
.row {
  width: 100%; text-align: left; display: grid; gap: 12px;
  background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--line);
  border-radius: 4px; padding: 14px 16px; color: inherit;
}
.row.play { border-left-color: var(--pass); }
.row.err { border-left-color: var(--fail); }
.head { display: flex; align-items: baseline; gap: 12px; }
.ticker { font-family: var(--font-display); font-weight: 700; font-size: 28px; letter-spacing: .01em; line-height: 1; }
.gap { font-weight: 600; font-size: 18px; }
.gap.up { color: var(--pass); } .gap.down { color: var(--fail); }
.price { color: var(--muted); }
.score { margin-left: auto; font-size: 13px; color: var(--muted); }
.foot { display: flex; gap: 12px; align-items: baseline; font-size: 13px; min-width: 0; }
.setup { font-weight: 600; white-space: nowrap; }
.setup.quiet { color: var(--muted); font-weight: 400; }
.news { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.error { margin: 0; color: var(--fail); font-size: 13px; }
</style>
