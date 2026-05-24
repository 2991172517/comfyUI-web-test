import { inject, provide, reactive, ref } from 'vue'

const CONFIRM_DIALOG_KEY = Symbol('confirmDialog')

/** @type {ReturnType<typeof createConfirmDialog> | null} */
let dialogSingleton = null

const defaults = {
  title: '确认操作',
  message: '',
  confirmText: '确认',
  cancelText: '取消',
  variant: 'destructive',
}

export function createConfirmDialog() {
  const open = ref(false)
  const options = reactive({ ...defaults })
  /** @type {import('vue').Ref<((v: boolean) => void) | null>} */
  const resolver = ref(null)

  function close(result) {
    open.value = false
    const resolve = resolver.value
    resolver.value = null
    resolve?.(result)
  }

  /**
   * @param {{
   *   title?: string
   *   message?: string
   *   confirmText?: string
   *   cancelText?: string
   *   variant?: 'destructive' | 'default'
   * }} opts
   * @returns {Promise<boolean>}
   */
  function confirm(opts = {}) {
    if (open.value) {
      close(false)
    }
    Object.assign(options, defaults, opts)
    open.value = true
    return new Promise((resolve) => {
      resolver.value = resolve
    })
  }

  function confirmDelete(opts = {}) {
    return confirm({
      title: '确认删除',
      confirmText: '删除',
      variant: 'destructive',
      ...opts,
    })
  }

  const api = {
    open,
    options,
    confirm,
    confirmDelete,
    accept: () => close(true),
    dismiss: () => close(false),
  }

  return api
}

export function provideConfirmDialog() {
  const api = createConfirmDialog()
  dialogSingleton = api
  provide(CONFIRM_DIALOG_KEY, api)
  return api
}

export function getConfirmDialog() {
  if (!dialogSingleton) {
    throw new Error('ConfirmDialog 未初始化，请确认 AppLayout 已挂载 ConfirmDialogHost')
  }
  return dialogSingleton
}

export function useConfirmDialog() {
  const api = inject(CONFIRM_DIALOG_KEY, dialogSingleton)
  if (!api) {
    throw new Error('useConfirmDialog must be used within AppLayout')
  }
  return api
}
