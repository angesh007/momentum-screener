<script setup lang="ts">
import { computed } from 'vue'
import { SIGNALS } from '~/composables/format'
import type { SignalKind } from '~/composables/useScreener'
const props = defineProps<{ signal?: SignalKind; large?: boolean }>()
const meta = computed(() => props.signal ? SIGNALS[props.signal] : null)
</script>

<template>
  <span v-if="meta" class="sig" :class="[meta.tone, { large }]" :title="meta.hint">
    <span class="ico" aria-hidden="true">{{ meta.icon }}</span>{{ meta.label }}
  </span>
</template>

<style scoped>
.sig {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: .03em;
  text-transform: uppercase;
  white-space: nowrap;
  border: 1px solid transparent;
}
.ico { font-size: 9px; letter-spacing: -1px; }
.large { font-size: 14px; padding: 8px 14px; }
.large .ico { font-size: 11px; }
.strong-pos  { background: var(--pass); color: var(--on-status); }
.pos         { background: var(--pass-bg); color: var(--pass); border-color: var(--pass); }
.neutral     { background: var(--unknown-bg); color: var(--ink-soft); border-color: var(--line-strong); }
.neg         { background: var(--fail-bg); color: var(--fail); border-color: var(--fail); }
.strong-neg  { background: var(--fail); color: var(--on-status); }
</style>
