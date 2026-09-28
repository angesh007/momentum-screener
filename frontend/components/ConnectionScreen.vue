<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { ConnectionPhase } from '~/composables/useScreener'

const props = defineProps<{ phase: ConnectionPhase; startedAt: number; error?: string }>()
defineEmits<{ retry: [] }>()

const now = ref(Date.now())
let timer: number | undefined
onMounted(() => { timer = window.setInterval(() => { now.value = Date.now() }, 1000) })
onUnmounted(() => clearInterval(timer))

const elapsed = computed(() => Math.max(0, Math.floor((now.value - props.startedAt) / 1000)))
const elapsedLabel = computed(() => {
  const s = elapsed.value
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`
})

// Two visible steps: reach the backend, then load the first data.
const steps = computed(() => {
  const connected = props.phase === 'loading' || props.phase === 'ready'
  return [
    { label: 'Connecting to trading engine…', state: connected ? 'done' : props.phase === 'error' ? 'failed' : 'active' },
    { label: 'Loading market data…', state: props.phase === 'ready' ? 'done' : props.phase === 'loading' ? 'active' : 'pending' }
  ]
})
</script>

<template>
  <section class="conn card" :aria-busy="phase !== 'error'" aria-live="polite">
    <template v-if="phase !== 'error'">
      <div class="pulse" aria-hidden="true"><span /></div>
      <h2>{{ phase === 'loading' ? 'Loading market data' : 'Connecting to trading engine' }}</h2>
      <ol class="steps">
        <li v-for="s in steps" :key="s.label" :data-state="s.state">
          <span class="mark" aria-hidden="true" />{{ s.label }}
        </li>
      </ol>
      <p v-if="phase === 'waking'" class="hint">
        The trading engine sleeps when nobody is using it and is starting up now.
        This usually takes under a minute, occasionally two or three. You don't need to refresh; the dashboard opens automatically.
      </p>
      <p class="elapsed">{{ elapsedLabel }} elapsed</p>
    </template>

    <template v-else>
      <div class="err-icon" aria-hidden="true">!</div>
      <h2>Couldn't reach the trading engine</h2>
      <p class="hint">{{ error || 'The backend did not respond.' }}</p>
      <p class="hint small">If it was asleep it may still be starting. Retrying usually works. Running locally? Start it with <code>./run.sh</code>.</p>
      <button class="btn btn--primary" @click="$emit('retry')">Retry connection</button>
    </template>
  </section>
</template>

<style scoped>
.conn {
  display: grid;
  justify-items: center;
  text-align: center;
  gap: 12px;
  padding: 48px 24px;
  margin: 12px auto 0;
  max-width: 560px;
}
h2 { font-family: var(--font-display); font-size: 22px; margin: 4px 0 0; }
.pulse { position: relative; width: 44px; height: 44px; }
.pulse span, .pulse::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid var(--accent-bg);
  border-top-color: var(--accent);
  animation: spin .9s linear infinite;
}
.pulse::before { inset: 10px; border-width: 2px; border-top-color: var(--pass); animation-duration: 1.4s; animation-direction: reverse; }
@keyframes spin { to { transform: rotate(360deg); } }

.steps { list-style: none; margin: 6px 0 0; padding: 0; display: grid; gap: 8px; text-align: left; }
.steps li { display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--muted); }
.steps li[data-state="active"] { color: var(--ink); font-weight: 600; }
.steps li[data-state="done"] { color: var(--pass); }
.mark { width: 10px; height: 10px; border-radius: 50%; border: 2px solid var(--line-strong); flex-shrink: 0; }
li[data-state="active"] .mark { border-color: var(--accent); background: var(--accent); animation: blink 1s ease-in-out infinite; }
li[data-state="done"] .mark { border-color: var(--pass); background: var(--pass); }
li[data-state="failed"] .mark { border-color: var(--fail); background: var(--fail); }
@keyframes blink { 50% { opacity: .35; } }

.hint { margin: 0; max-width: 46ch; color: var(--ink-soft); font-size: 14px; }
.hint.small { font-size: 13px; color: var(--muted); }
.elapsed { margin: 0; font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }
.err-icon {
  display: grid; place-items: center;
  width: 44px; height: 44px; border-radius: 50%;
  background: var(--fail-bg); color: var(--fail);
  font-family: var(--font-display); font-weight: 700; font-size: 24px;
}
.btn { margin-top: 6px; border-radius: var(--radius); padding: 10px 18px; font-weight: 600; border: 1px solid transparent; }
.btn--primary { background: var(--accent); color: var(--accent-ink); }
.btn--primary:hover { background: var(--accent-strong); }
</style>
