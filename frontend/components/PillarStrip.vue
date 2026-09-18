<script setup lang="ts">
import type { Pillar } from '~/composables/useScreener'
defineProps<{ pillars: Pillar[]; compact?: boolean }>()
</script>

<template>
  <div class="strip" :class="{ compact }" role="list" aria-label="Five pillars">
    <div
      v-for="p in pillars"
      :key="p.key"
      class="seg"
      :data-status="p.status"
      role="listitem"
      :title="p.note"
    >
      <span class="bar" />
      <template v-if="!compact">
        <span class="label">{{ p.label }}</span>
        <span class="val">{{ p.display }}</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.seg { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.bar {
  height: 8px;
  border-radius: var(--radius-pill);
  background: var(--unknown);
  transition: background-color .2s ease;
}
.seg[data-status="pass"] .bar { background: var(--pass); }
.seg[data-status="warn"] .bar { background: var(--warn); }
.seg[data-status="fail"] .bar { background: var(--fail); opacity: .5; }
.label {
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-transform: uppercase;
  letter-spacing: .04em;
}
.val { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.seg[data-status="pass"] .val { color: var(--ink); }
.seg[data-status="fail"] .val { color: var(--muted); }
.compact .bar { height: 5px; }
</style>
