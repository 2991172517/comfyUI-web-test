import { ref } from 'vue'

const prepActive = ref(false)
const stageMessage = ref('')
/** @type {import('vue').Ref<{ id: number, text: string, time: string }[]>} */
const stageLogs = ref([])

let logSeq = 0

function formatLogTime(date = new Date()) {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

/** @param {string} text */
export function appendGenerateStageLog(text) {
  stageMessage.value = text
  stageLogs.value = [
    ...stageLogs.value,
    { id: ++logSeq, text, time: formatLogTime() },
  ]
}

export function beginGeneratePrep() {
  prepActive.value = true
  stageLogs.value = []
  stageMessage.value = ''
  appendGenerateStageLog('开始准备生成…')
}

export function endGeneratePrep() {
  prepActive.value = false
}

export function useGenerateStageLog() {
  return {
    prepActive,
    stageMessage,
    stageLogs,
    appendGenerateStageLog,
    beginGeneratePrep,
    endGeneratePrep,
  }
}
