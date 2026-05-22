import { ref } from 'vue'

/** 模型下载 / 导入弹窗 */
export const modelImportModalOpen = ref(false)
/** 打开弹窗时预填的模型页链接（来自 C 站浏览等） */
export const modelImportInitialUrl = ref('')

export function openModelImportModal(url = '') {
  modelImportInitialUrl.value = typeof url === 'string' ? url.trim() : ''
  modelImportModalOpen.value = true
}

export function closeModelImportModal() {
  modelImportModalOpen.value = false
  modelImportInitialUrl.value = ''
}

export function useModelImportModal() {
  return {
    open: modelImportModalOpen,
    initialUrl: modelImportInitialUrl,
    openModal: openModelImportModal,
    close: closeModelImportModal,
  }
}
