import { ref } from 'vue'
import { appendPromptTag, removePromptTag } from '@/lib/appendPromptTag.js'
import {
  getWorkflowPositiveText,
  pickRandomSixFromLibrary,
  setWorkflowPositiveText,
} from '@/lib/vocabularyRandomSix.js'

const enabled = ref(false)
/** @type {import('vue').Ref<string[]>} */
const lastPickValues = ref([])
/** @type {import('vue').Ref<Array<{ name: string, value: string }>>} */
const lastPicks = ref([])
const rolling = ref(false)

function stripLastPicks(text) {
  let next = String(text || '')
  for (const tag of lastPickValues.value) {
    next = removePromptTag(next, tag).text
  }
  return next
}

function applyPickValues(text, values) {
  let next = stripLastPicks(text)
  for (const tag of values) {
    next = appendPromptTag(next, tag).text
  }
  return next
}

export function useVocabularyRandomMode() {
  async function rollForApp(app) {
    if (!app.promptEncode?.positive?.node_id) {
      return { picks: [], applied: false, message: '当前工作流无正向提示词节点' }
    }

    rolling.value = true
    try {
      const picks = await pickRandomSixFromLibrary()
      if (!picks.length) {
        return { picks: [], applied: false, message: '词库随机失败，请确认六类分类有词条' }
      }

      const values = picks.map((p) => p.value)
      const current = getWorkflowPositiveText(app)
      const next = applyPickValues(current, values)
      setWorkflowPositiveText(app, next)
      lastPickValues.value = values
      lastPicks.value = picks.map(({ name, value }) => ({ name, value }))

      return {
        picks: lastPicks.value,
        applied: true,
        message: `已抽取：${values.join(', ')}`,
      }
    } finally {
      rolling.value = false
    }
  }

  function clearFromApp(app) {
    if (!app.promptEncode?.positive?.node_id) {
      lastPickValues.value = []
      lastPicks.value = []
      return
    }
    const current = getWorkflowPositiveText(app)
    const next = stripLastPicks(current)
    if (next !== current) {
      setWorkflowPositiveText(app, next)
    }
    lastPickValues.value = []
    lastPicks.value = []
  }

  return {
    enabled,
    lastPicks,
    lastPickValues,
    rolling,
    rollForApp,
    clearFromApp,
  }
}
