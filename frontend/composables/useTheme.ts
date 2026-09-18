import { useState } from '#imports'

export type Theme = 'light' | 'dark'
const STORAGE_KEY = 'momentum-theme'

/**
 * Light/dark theme with persistence + system-preference fallback.
 * The initial value is applied pre-render by an inline head script
 * (see nuxt.config.ts) to avoid a flash; this composable keeps Vue
 * state in sync and handles toggling/persistence at runtime.
 */
export const useTheme = () => {
  const theme = useState<Theme>('theme', () => 'light')

  function resolveInitial(): Theme {
    if (typeof window === 'undefined') return 'light'
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  function apply(next: Theme) {
    if (typeof document !== 'undefined') {
      document.documentElement.dataset.theme = next
    }
  }

  /** Sync Vue state with whatever the pre-render script already set. */
  function init() {
    const current = (typeof document !== 'undefined' && document.documentElement.dataset.theme) as Theme | undefined
    theme.value = current === 'light' || current === 'dark' ? current : resolveInitial()
    apply(theme.value)
    // Enable color transitions only after first paint, so the initial
    // theme application does not animate.
    if (typeof document !== 'undefined') {
      requestAnimationFrame(() => document.documentElement.classList.add('theme-ready'))
    }
  }

  function setTheme(next: Theme) {
    theme.value = next
    apply(next)
    if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, next)
  }

  function toggle() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  return { theme, init, setTheme, toggle }
}
