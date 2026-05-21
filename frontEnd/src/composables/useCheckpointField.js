import { computed } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'

/** 工作流中第一个 Checkpoint 节点字段 */
export function useCheckpointField() {
  const app = useAppStore()

  const entry = computed(() => {
    for (const node of app.state.nodes) {
      for (const field of node.fields) {
        if (app.isModelSelectField(field) && app.modelFolderForField(field) === 'checkpoints') {
          return { nodeId: node.id, nodeTitle: node.title, field }
        }
      }
    }
    return null
  })

  const ckptName = computed({
    get: () => {
      if (!entry.value) return ''
      return String(app.fieldValue(entry.value.nodeId, entry.value.field) || '')
    },
    set: (v) => {
      if (!entry.value) return
      app.updateField(entry.value.nodeId, entry.value.field.key, v)
    },
  })

  return {
    entry,
    ckptName,
    hasCheckpoint: computed(() => !!entry.value),
  }
}
