<script setup lang="ts">
import type { Thresholds } from '~/composables/useScreener'
defineProps<{ th: Thresholds }>()
const m = (n: number) => `${(n / 1e6).toFixed(0)}M`
</script>

<template>
  <div class="rules">
    <div class="step">
      <span class="num">1</span>
      <div class="body">
        <h4>Stock selection</h4>
        <p>Only stocks passing all five pillars are "in play". At most 10 make the list.</p>
        <ul>
          <li>Price ${{ th.price_min }}–${{ th.price_max }}; nothing under $1</li>
          <li>Gapping up ≥ {{ th.gap_pct_min }}% from yesterday's close</li>
          <li>Relative volume ≥ {{ th.rvol_min }}× the average</li>
          <li>Float ≤ {{ m(th.float_ideal) }} ideal, ≤ {{ m(th.float_max) }} at most</li>
          <li>A fresh catalyst in the last {{ th.news_lookback_hours }}h</li>
        </ul>
      </div>
    </div>
    <div class="step">
      <span class="num">2</span>
      <div class="body">
        <h4>Setups</h4>
        <p>Never chase a vertical move. Wait for a bull flag micro-pullback or a flat-top consolidation and enter on the break of the prior candle's high or the resistance line.</p>
      </div>
    </div>
    <div class="step">
      <span class="num">3</span>
      <div class="body">
        <h4>Timing</h4>
        <p>9:30–11:30 ET only. The first 30 minutes are the cleanest; midday is chop.</p>
      </div>
    </div>
    <div class="step">
      <span class="num">4</span>
      <div class="body">
        <h4>Level 2</h4>
        <p>Confirm with the tape: ask walls getting eaten, bids stacking below. This needs your broker's Level 2 window — Finnhub's free plan doesn't provide it.</p>
      </div>
    </div>
    <div class="step">
      <span class="num">5</span>
      <div class="body">
        <h4>Risk</h4>
        <p>Stop at the pullback low or the 9 EMA. Aim for 2:1. Sell half at +1R, move the stop to break-even, let the rest run to +2R.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rules {
  display: grid;
  gap: 4px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 8px;
  box-shadow: var(--shadow-sm);
}
.step { display: flex; gap: 12px; padding: 12px; border-radius: var(--radius); }
.step + .step { border-top: 1px solid var(--line); border-radius: 0; }
.num {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border-radius: var(--radius-pill);
  background: var(--accent-bg);
  color: var(--accent-strong);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 14px;
}
.body { display: grid; gap: 4px; }
h4 { font-family: var(--font-display); font-size: 16px; margin: 0; color: var(--ink); }
p, ul { margin: 0; font-size: 14px; color: var(--muted); }
ul { padding-left: 18px; display: grid; gap: 2px; }
</style>
