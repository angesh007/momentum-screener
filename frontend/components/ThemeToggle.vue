<script setup lang="ts">
import { onMounted } from 'vue'
import { useTheme } from '~/composables/useTheme'

const { theme, init, toggle } = useTheme()
onMounted(init)
</script>

<template>
  <button
    class="theme-toggle"
    type="button"
    role="switch"
    :aria-checked="theme === 'dark'"
    :title="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
    aria-label="Toggle color theme"
    @click="toggle"
  >
    <!-- Sun -->
    <svg v-if="theme === 'dark'" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <circle cx="12" cy="12" r="4.2" fill="currentColor" />
      <g stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
        <line x1="12" y1="2.5" x2="12" y2="5" />
        <line x1="12" y1="19" x2="12" y2="21.5" />
        <line x1="2.5" y1="12" x2="5" y2="12" />
        <line x1="19" y1="12" x2="21.5" y2="12" />
        <line x1="5.2" y1="5.2" x2="6.9" y2="6.9" />
        <line x1="17.1" y1="17.1" x2="18.8" y2="18.8" />
        <line x1="5.2" y1="18.8" x2="6.9" y2="17.1" />
        <line x1="17.1" y1="6.9" x2="18.8" y2="5.2" />
      </g>
    </svg>
    <!-- Moon -->
    <svg v-else viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        d="M20 14.2A8 8 0 1 1 9.8 4a6.4 6.4 0 0 0 10.2 10.2z"
        fill="currentColor"
      />
    </svg>
    <span class="label">{{ theme === 'dark' ? 'Light' : 'Dark' }}</span>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-pill);
  background: var(--surface);
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}
.theme-toggle:hover { border-color: var(--line-strong); color: var(--ink); }
.theme-toggle svg { flex-shrink: 0; }
@media (max-width: 520px) {
  .label { display: none; }
  .theme-toggle { padding: 8px; }
}
</style>
