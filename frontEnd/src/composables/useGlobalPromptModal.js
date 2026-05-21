import { ref } from 'vue'

/** 全局提示词设置弹窗（全局 / 随机池 / 预设） */
export const globalPromptModalOpen = ref(false)
export const globalPromptModalTab = ref('global')

export function openGlobalPromptModal(tab = 'global') {
  globalPromptModalTab.value = tab
  globalPromptModalOpen.value = true
}

export function closeGlobalPromptModal() {
  globalPromptModalOpen.value = false
}

export function useGlobalPromptModal() {
  return {
    open: globalPromptModalOpen,
    activeTab: globalPromptModalTab,
    openModal: openGlobalPromptModal,
    close: closeGlobalPromptModal,
  }
}
