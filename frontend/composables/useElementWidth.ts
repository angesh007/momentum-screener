import { ref, watch, onUnmounted, type Ref } from 'vue'

/** Tracks an element's content width so SVG charts can draw at true pixel size
 *  (text and stroke widths stay crisp instead of being stretched by a viewBox).
 *  Follows the ref, so it works when the element sits behind a v-if. */
export function useElementWidth(el: Ref<HTMLElement | null>, fallback = 640) {
  const width = ref(fallback)
  const ro = typeof ResizeObserver !== 'undefined'
    ? new ResizeObserver(([e]) => { if (e.contentRect.width) width.value = Math.floor(e.contentRect.width) })
    : undefined
  watch(el, (node, prev) => {
    if (prev) ro?.unobserve(prev)
    if (!node) return
    width.value = node.clientWidth || width.value
    ro?.observe(node)
  }, { immediate: true, flush: 'post' })
  onUnmounted(() => ro?.disconnect())
  return width
}

/** ~`count` round tick values covering [lo, hi]. */
export function niceTicks(lo: number, hi: number, count = 4): number[] {
  const span = hi - lo
  if (!(span > 0)) return [lo]
  const raw = span / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = ([1, 2, 2.5, 5, 10].find(m => m * mag >= raw) ?? 10) * mag
  const out: number[] = []
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toFixed(10))
  return out
}
