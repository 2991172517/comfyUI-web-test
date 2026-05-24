import { nextTick } from 'vue'
import { prefersReducedMotion } from '@/lib/gsap/motion.js'

/** 与 sticky 顶栏对齐，避免目标被遮挡 */
const SCROLL_MARGIN_TOP = 80

function waitForPaint() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  })
}

/**
 * 生成页点击生成后，滚动到单张「生成状态」或批量进度区域。
 * @param {{ sweep?: boolean }} opts
 */
export async function scrollToGenerateStatus({ sweep = false } = {}) {
  await nextTick()
  await waitForPaint()

  const el = document.querySelector(
    sweep ? '[data-generate-status="batch"]' : '[data-generate-status="single"]',
  )
  if (!el) return

  el.scrollIntoView({
    behavior: prefersReducedMotion() ? 'auto' : 'smooth',
    block: 'start',
  })
}

export { SCROLL_MARGIN_TOP }
