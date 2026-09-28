<script setup lang="ts">
import { computed } from 'vue'
import PillarStrip from '~/components/PillarStrip.vue'
import SignalBadge from '~/components/SignalBadge.vue'
import { fmtPrice, fmtGap, fmtRvol, fmtMoney, fmtRR } from '~/composables/format'
import type { ScreenResult } from '~/composables/useScreener'
const props = defineProps<{ r: ScreenResult; rank: number }>()
defineEmits<{ open: [symbol: string] }>()

const passed = computed(() => props.r.pillars.filter(p => p.status === 'pass').length)
const setupLabel = computed(() => {
  const s = props.r.setup
  if (!s || s.pattern === 'none') return null
  return `${s.pattern === 'bull_flag' ? 'Bull flag' : 'Flat top'} · ${s.stage}`
})
const rvolPillar = computed(() => props.r.pillars.find(p => p.key === 'rvol'))
const rvolStatus = computed(() => rvolPillar.value?.status ?? 'unknown')
// Lead with the reasons that agree with the signal, so the row says *why*.
const topReasons = computed(() => {
  const rs = props.r.signal_reasons ?? []
  const want = props.r.signal === 'sell' || props.r.signal === 'strong_sell' ? 'negative' : 'positive'
  return rs.filter(x => x.impact === want).slice(0, 3)
})
const plan = computed(() => props.r.plan)
</script>

<template>
  <button class="row" :class="[{ play: r.in_play, err: !!r.error }, r.signal ? `sig-${r.signal}` : '']" @click="$emit('open', r.symbol)">
    <div class="head">
      <span class="rank" :class="{ play: r.in_play }">{{ rank }}</span>
      <div class="id">
        <span class="ticker">{{ r.symbol }}</span>
        <span v-if="r.name" class="name">{{ r.name }}</span>
      </div>
      <span v-if="r.gap_pct != null" class="gap" :class="{ up: r.gap_pct > 0, down: r.gap_pct < 0 }">
        {{ r.gap_pct > 0 ? '▲' : r.gap_pct < 0 ? '▼' : '' }} {{ fmtGap(r.gap_pct) }}
      </span>
      <div class="head-right">
        <span class="score" :class="{ full: passed === 5 }" :title="`${passed} of 5 pillars pass`">
          <b>{{ passed }}</b>/5
        </span>
        <SignalBadge v-if="!r.error" :signal="r.signal" />
      </div>
    </div>

    <p v-if="r.error" class="error">Couldn't load: {{ r.error }}</p>
    <template v-else>
      <dl class="metrics">
        <div class="m">
          <dt>Price</dt>
          <dd>{{ fmtPrice(r.price) }}</dd>
        </div>
        <div class="m">
          <dt>Mkt value</dt>
          <dd :class="{ na: r.market_cap == null }">{{ fmtMoney(r.market_cap) }}</dd>
        </div>
        <div class="m rvol" :data-status="rvolStatus" :title="rvolPillar?.note">
          <dt>RVOL</dt>
          <dd>
            {{ fmtRvol(r.rvol) }}
            <small v-if="r.rvol == null">no intraday data</small>
          </dd>
        </div>
        <div class="m">
          <dt>Entry</dt>
          <dd class="entry" :class="{ na: !plan }">{{ plan ? fmtPrice(plan.entry) : 'N/A' }}</dd>
        </div>
        <div class="m">
          <dt>Target</dt>
          <dd class="target" :class="{ na: !plan }">{{ plan ? fmtPrice(plan.target) : 'N/A' }}</dd>
        </div>
        <div class="m">
          <dt>Stop</dt>
          <dd class="stop" :class="{ na: !plan }">{{ plan ? fmtPrice(plan.stop) : 'N/A' }}</dd>
        </div>
        <div class="m">
          <dt>R : R</dt>
          <dd :class="{ na: !plan }">{{ plan ? fmtRR(plan.reward_risk) : 'N/A' }}</dd>
        </div>
      </dl>

      <PillarStrip :pillars="r.pillars" />

      <div class="foot">
        <span v-if="setupLabel" class="badge badge--accent">{{ setupLabel }}</span>
        <span v-else-if="plan?.source === 'day_range'" class="badge badge--unknown" title="Levels from today's high/low — no intraday candles">Day-range plan</span>
        <span v-for="x in topReasons" :key="x.label" class="reason" :class="x.impact">{{ x.label }}</span>
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
  gap: 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 4px solid var(--line-strong);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  color: inherit;
  box-shadow: var(--shadow-sm);
  transition: transform .12s ease, box-shadow .2s ease, border-color .2s ease;
}
.row:hover { transform: translateY(-1px); box-shadow: var(--shadow); border-color: var(--line-strong); }
.row.sig-strong_buy, .row.sig-buy { border-left-color: var(--pass); }
.row.sig-sell, .row.sig-strong_sell { border-left-color: var(--fail); }
.row.err  { border-left-color: var(--fail); }

.head { display: flex; align-items: center; gap: 12px; min-width: 0; }
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
.id { display: flex; align-items: baseline; gap: 10px; min-width: 0; }
.ticker {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 24px;
  letter-spacing: .01em;
  line-height: 1;
}
.name { color: var(--muted); font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 26ch; }
.gap { font-weight: 700; font-size: 15px; white-space: nowrap; }
.gap.up { color: var(--pass); }
.gap.down { color: var(--fail); }
.head-right { margin-left: auto; display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.score {
  font-size: 12px;
  color: var(--muted);
  background: var(--surface-3);
  border-radius: var(--radius-pill);
  padding: 4px 9px;
}
.score b { color: var(--ink); }
.score.full { background: var(--pass-bg); color: var(--pass); }
.score.full b { color: var(--pass); }

/* Trade line: Price → Mkt value → RVOL → Entry → Target → Stop → R:R */
.metrics {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface-2);
  overflow: hidden;
}
.m { padding: 9px 12px; display: grid; gap: 2px; align-content: start; min-width: 0; }
.m + .m { border-left: 1px solid var(--line); }
dt { font-size: 10.5px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
dd { margin: 0; font-family: var(--font-display); font-weight: 700; font-size: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-variant-numeric: tabular-nums; }
dd.na { color: var(--muted); font-weight: 600; }
dd.entry { color: var(--accent); }
dd.target { color: var(--pass); }
dd.stop { color: var(--fail); }

/* RVOL is the momentum tell — give it its own tinted cell. */
.rvol { background: var(--accent-bg); }
.rvol dd { font-size: 19px; line-height: 1.1; }
.rvol small { display: block; font-family: var(--font); font-size: 10.5px; font-weight: 500; color: var(--muted); }
.rvol[data-status="pass"] { background: var(--pass-bg); }
.rvol[data-status="pass"] dd { color: var(--pass); }
.rvol[data-status="warn"] { background: var(--warn-bg); }
.rvol[data-status="warn"] dd { color: var(--warn); }
.rvol[data-status="fail"] dd { color: var(--fail); }
.rvol[data-status="unknown"] { background: var(--unknown-bg); }
.rvol[data-status="unknown"] dd { color: var(--muted); }

.foot { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: 12.5px; min-width: 0; }
.reason {
  padding: 3px 9px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--line);
  color: var(--ink-soft);
  white-space: nowrap;
}
.reason.positive { border-color: color-mix(in srgb, var(--pass) 45%, transparent); }
.reason.negative { border-color: color-mix(in srgb, var(--fail) 45%, transparent); }
.reason.positive::before { content: "+ "; color: var(--pass); font-weight: 700; }
.reason.negative::before { content: "− "; color: var(--fail); font-weight: 700; }
.news { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-flex; align-items: center; gap: 6px; min-width: 0; flex: 1 1 200px; }
.news-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
.error { margin: 0; color: var(--fail); font-size: 13px; }

@media (max-width: 860px) {
  .metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .m { border-top: 1px solid var(--line); }
  .m:nth-child(-n+4) { border-top: 0; }
  .m:nth-child(4n+1) { border-left: 0; }
}
@media (max-width: 520px) {
  .row { padding: 14px; }
  .head { flex-wrap: wrap; row-gap: 8px; }
  .name { display: none; }
  .ticker { font-size: 22px; }
  .head-right { margin-left: 0; width: 100%; justify-content: space-between; }
  .metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .m:nth-child(n) { border-left: 1px solid var(--line); border-top: 1px solid var(--line); }
  .m:nth-child(-n+3) { border-top: 0; }
  .m:nth-child(3n+1) { border-left: 0; }
}
</style>
