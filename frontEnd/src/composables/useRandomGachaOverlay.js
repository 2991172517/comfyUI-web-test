import { inject, nextTick, provide, ref } from 'vue'
import { playRandomGachaAnimation } from '@/lib/randomGachaAnimation.js'

const RANDOM_GACHA_KEY = Symbol('randomGachaOverlay')

/** @type {ReturnType<typeof createRandomGachaOverlay> | null} */
let gachaSingleton = null

export function createRandomGachaOverlay() {
  const open = ref(false)
  /** @type {import('vue').Ref<HTMLElement | null>} */
  const panelRef = ref(null)
  const gachaTitle = ref('正在抽取随机参数')
  const gachaSubtitle = ref('各随机组同时开奖，请稍候…')
  /** 模拟抽词等场景：动画结束后保留弹窗，由用户手动关闭 */
  const manualClose = ref(false)
  const canClose = ref(false)

  function closeOverlay() {
    open.value = false
    manualClose.value = false
    canClose.value = false
  }

  /**
   * @param {ReturnType<typeof import('@/lib/randomGachaReels.js').buildGachaRows>} rows
   * @param {{
   *   targetEl?: HTMLElement | null,
   *   title?: string,
   *   subtitle?: string,
   *   manualClose?: boolean,
   * }} [opts]
   */
  async function playWithRows(
    rows,
    { targetEl = null, title, subtitle, manualClose: stayOpen = false } = {},
  ) {
    if (!rows?.length) {
      return { played: false, reason: 'no-random' }
    }

    gachaTitle.value = title || '正在抽取随机参数'
    gachaSubtitle.value = subtitle || '各随机组同时开奖，请稍候…'
    manualClose.value = stayOpen
    canClose.value = false
    open.value = true
    await nextTick()
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))

    try {
      const root = panelRef.value
      if (!root) {
        return { played: false, reason: 'no-host' }
      }
      const result = await playRandomGachaAnimation({ root, rows, targetEl })
      if (stayOpen) {
        canClose.value = true
      }
      return { ...result, rows }
    } finally {
      if (!stayOpen) {
        open.value = false
        manualClose.value = false
        canClose.value = false
      }
    }
  }

  const api = {
    open,
    panelRef,
    gachaTitle,
    gachaSubtitle,
    manualClose,
    canClose,
    closeOverlay,
    playWithRows,
  }

  return api
}

export function provideRandomGachaOverlay() {
  const api = createRandomGachaOverlay()
  gachaSingleton = api
  provide(RANDOM_GACHA_KEY, api)
  return api
}

export function getRandomGachaOverlay() {
  if (!gachaSingleton) {
    throw new Error('RandomGacha 未初始化，请确认 AppLayout 已挂载 RandomGachaHost')
  }
  return gachaSingleton
}

export function useRandomGachaOverlay() {
  const api = inject(RANDOM_GACHA_KEY, gachaSingleton)
  if (!api) {
    throw new Error('useRandomGachaOverlay must be used within AppLayout')
  }
  return api
}
