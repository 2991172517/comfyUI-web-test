import { onUnmounted, ref } from 'vue'

/**
 * 编辑后延迟自动保存；load 完成后调用 markReady() 再开始监听。
 */
export function useDebouncedSave(saveFn, { delay = 450 } = {}) {
  const ready = ref(false)
  const saving = ref(false)
  let timer = null

  function markReady(value = true) {
    ready.value = value
  }

  function schedule() {
    if (!ready.value) return
    if (timer) clearTimeout(timer)
    timer = setTimeout(async () => {
      timer = null
      saving.value = true
      try {
        await saveFn()
      } finally {
        saving.value = false
      }
    }, delay)
  }

  function flush() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    if (!ready.value) return Promise.resolve()
    saving.value = true
    return saveFn().finally(() => {
      saving.value = false
    })
  }

  onUnmounted(() => {
    if (timer) clearTimeout(timer)
  })

  return { ready, saving, markReady, schedule, flush }
}
