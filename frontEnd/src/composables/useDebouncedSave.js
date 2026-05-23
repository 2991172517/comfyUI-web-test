import { onUnmounted, ref } from 'vue'

/** 提示词设置等「随编辑自动保存」的统一防抖间隔（毫秒） */
export const PROMPT_AUTO_SAVE_DEBOUNCE_MS = 700

/**
 * 编辑后延迟自动保存；load 完成后调用 markReady() 再开始监听。
 * flush() 会立即提交；保存进行中若又有改动，会在当前请求结束后补一次。
 */
export function useDebouncedSave(saveFn, { delay = PROMPT_AUTO_SAVE_DEBOUNCE_MS } = {}) {
  const ready = ref(false)
  const saving = ref(false)
  const pending = ref(false)
  let timer = null
  let inFlight = null
  let dirtyWhileSaving = false

  function markReady(value = true) {
    ready.value = value
  }

  function cancel() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    pending.value = false
  }

  async function executeSave() {
    if (!ready.value) return
    if (inFlight) {
      dirtyWhileSaving = true
      return inFlight
    }
    pending.value = false
    saving.value = true
    inFlight = Promise.resolve()
      .then(() => saveFn())
      .finally(() => {
        inFlight = null
        saving.value = false
        if (dirtyWhileSaving && ready.value) {
          dirtyWhileSaving = false
          return executeSave()
        }
      })
    return inFlight
  }

  function schedule() {
    if (!ready.value) return
    pending.value = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      timer = null
      void executeSave()
    }, delay)
  }

  function flush() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    if (!ready.value) return Promise.resolve()
    pending.value = false
    if (inFlight) {
      dirtyWhileSaving = true
      return inFlight.then(() => flush())
    }
    return executeSave() || Promise.resolve()
  }

  onUnmounted(() => cancel())

  return { ready, saving, pending, markReady, schedule, flush, cancel }
}
