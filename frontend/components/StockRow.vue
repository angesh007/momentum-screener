<script setup lang="ts">
import { computed } from 'vue'
import PillarStrip from '~/components/PillarStrip.vue'
import type { ScreenResult } from '~/composables/useScreener'
const props = defineProps<{ r: ScreenResult; rank: number }>()
defineEmits<{ open: [symbol: string] }>()

const passed = computed(() => props.r.pillars.filter(p => p.status === 'pass').length)
const setupLabel = computed(() => {
  const s = props.r.setup
  if (!s || s.pattern === 'none') return null
  return `${s.pattern === 'bull_flag' ? 'Bull flag' : 'Flat top'} · ${s.stage}`
})
</script>

<template>
  <button class="row" :class="{ play: r.in_play, err: !!r.error }" @click="$emit('open', r.symbol)">
    <div class="head">
      <span class="rank" :class="{ play: r.in_play }">{{ rank }}</span>
      <span class="ticker">{{ r.symbol }}</span>
      <span v-if="r.gap_pct != null" class="gap" :class="{ up: r.gap_pct > 0, down: r.gap_pct < 0 }">
        {{ r.gap_pct > 0 ? '+' : '' }}{{ r.gap_pct.toFixed(1) }}%
      </span>
      <span v-if="r.price != null" class="price">${{ r.price.toFixed(2) }}</span>
      <span class="score" :class="{ full: passed === 5 }" aria-label="pillars passed">
        <b>{{ passed }}</b>/5
      </span>
    </div>
    <p v-if="r.error" class="error">Couldn't load: {{ r.error }}</p>
    <template v-else>
      <PillarStrip :pillars="r.pillars" />
      <div class="foot">
        <span v-if="setupLabel" class="badge badge--accent">{{ setupLabel }}</span>
        <span v-else class="setup-quiet">No setup yet</span>
        <span v-if="r.catalyst" class="news" :title="r.catalyst.headline">
          <span class="news-dot" /> {{ r.catalyst.headline }}
        </span>
      </div>
    </template>
  </button>
</template>

<style scoped>
.row {
  width: 100%;
  text-align: left;
  display: grid;
  gap: 13px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 3px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  color: inherit;
  box-shadow: var(--shadow-sm);
  transition: transform .12s ease, box-shadow .2s ease, border-color .2s ease;
}
.row:hover { transform: translateY(-1px); box-shadow: var(--shadow); border-color: var(--line-strong); }
.row.play { border-left-color: var(--pass); }
.row.err  { border-left-color: var(--fail); }

.head { display: flex; align-items: center; gap: 12px; }
.rank {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: var(--radius-pill);
  background: var(--surface-3);
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}
.rank.play { background: var(--pass-bg); color: var(--pass); }
.ticker {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 26px;
  letter-spacing: .01em;
  line-height: 1;
}
.gap { font-weight: 700; font-size: 17px; }
.gap.up { color: var(--pass); }
.gap.down { color: var(--fail); }
.price { color: var(--muted); font-weight: 500; }
.score {
  margin-left: auto;
  font-size: 13px;
  color: var(--muted);
  background: var(--surface-3);
  border-radius: var(--radius-pill);
  padding: 4px 10px;
}
.score b { color: var(--ink); }
.score.full { background: var(--pass-bg); color: var(--pass); }
.score.full b { color: var(--pass); }

.foot { display: flex; gap: 12px; align-items: center; font-size: 13px; min-width: 0; }
.setup-quiet { color: var(--muted); }
.news { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-flex; align-items: center; gap: 6px; min-width: 0; }
.news-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
.error { margin: 0; color: var(--fail); font-size: 13px; }

@media (max-width: 480px) {
  .ticker { font-size: 22px; }
  .price { display: none; }
}
</style>
