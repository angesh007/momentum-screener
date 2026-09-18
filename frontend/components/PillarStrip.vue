<script setup lang="ts">
import type { Pillar } from '~/composables/useScreener'
defineProps<{ pillars: Pillar[]; compact?: boolean }>()
</script>

<template>
  <div class="strip" :class="{ compact }" role="list" aria-label="Five pillars">
    <div v-for="p in pillars" :key="p.key" class="seg" :data-status="p.status" role="listitem" :title="p.note">
      <span class="bar" />
      <span v-if="!compact" class="label">{{ p.label }}</span>
      <span v-if="!compact" class="val">{{ p.display }}</span>
    </div>
  </div>
</template>

<style scoped>
.strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
.seg { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.bar { height: 10px; border-radius: 2px; background: var(--unknown); }
.seg[data-status="pass"] .bar { background: var(--pass); }
.seg[data-status="warn"] .bar { background: var(--warn); }
.seg[data-status="fail"] .bar { background: var(--fail); opacity: .55; }
.label { font-size: 11px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.val { font-size: 13px; font-weight: 600; white-space: nowrap; }
.compact .bar { height: 6px; }
</style>
