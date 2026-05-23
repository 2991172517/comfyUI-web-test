import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'custom_project_prompt_editor_mode'

/** @typedef {'plain' | 'tags' | 'autocomplete'} PromptEditorMode */

export const PROMPT_EDITOR_MODE_OPTIONS = [
  { id: 'plain', label: '纯文本', desc: '不查词库、无补全' },
  { id: 'tags', label: 'Tag 条', desc: '中英文标签，滚轮调权重' },
  { id: 'autocomplete', label: '文本 + 补全', desc: '输入时下拉建议' },
]

/** @returns {import('vue').Ref<PromptEditorMode>} */
function readMode() {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'plain' || v === 'tags' || v === 'autocomplete') return v
  } catch {
    /* ignore */
  }
  return 'autocomplete'
}

const modeRef = ref(readMode())

watch(modeRef, (m) => {
  try {
    localStorage.setItem(STORAGE_KEY, m)
  } catch {
    /* ignore */
  }
})

export function usePromptEditorMode() {
  const mode = computed({
    get: () => modeRef.value,
    set: (v) => {
      if (v === 'plain' || v === 'tags' || v === 'autocomplete') {
        modeRef.value = v
      }
    },
  })

  return { mode, modeRef }
}
