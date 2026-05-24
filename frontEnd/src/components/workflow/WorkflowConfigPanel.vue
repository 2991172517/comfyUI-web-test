<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Trash2 } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import { useCheckpointField } from '@/composables/useCheckpointField.js'
import { WORKFLOW_CONFIG_MODULES } from '@/composables/useWorkflowConfigModules.js'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'
import { api } from '@/api/client.js'
import ModuleTabBar from '@/components/run/ModuleTabBar.vue'
import LoraModulePanel from '@/components/run/modules/LoraModulePanel.vue'
import OtherModulePanel from '@/components/run/modules/OtherModulePanel.vue'
import ModelVisualPicker from '@/components/models/ModelVisualPicker.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Badge from '@/components/ui/Badge.vue'
import Alert from '@/components/ui/Alert.vue'
import { gsap, prefersReducedMotion } from '@/lib/gsap/motion.js'

const props = defineProps({
  workflowId: { type: String, default: '' },
})

const emit = defineEmits(['deleted', 'saved'])

const router = useRouter()
const app = useAppStore()
const { confirmDelete } = useConfirmDialog()

const activeModule = ref('checkpoint')
const panelRef = ref(null)
const displayName = ref('')
const saving = ref(false)
const metaSaving = ref(false)
const chainBusy = ref(false)

const MAX_LORA_SLOTS = 5

const { entry, ckptName, hasCheckpoint } = useCheckpointField()

const readOnly = computed(() => app.isMasterWorkflow)
const panelDisabled = computed(() => readOnly.value || app.loading || app.modelsLoading || chainBusy.value)

watch(
  () => props.workflowId,
  async (id) => {
    if (!id) return
    await app.loadWorkflow(id)
    displayName.value =
      app.workflowMeta?.display_name ||
      app.workflows.find((w) => w.id === id)?.display_name ||
      id
  },
  { immediate: true },
)

watch(activeModule, async () => {
  await nextTick()
  const el = panelRef.value
  if (!el || prefersReducedMotion()) return
  gsap.fromTo(
    el,
    { opacity: 0 },
    { opacity: 1, duration: 0.18, ease: 'power1.out', clearProps: 'opacity' },
  )
})

async function saveMetaName() {
  if (!props.workflowId || readOnly.value) return
  metaSaving.value = true
  try {
    await api.updateWorkflowMeta(props.workflowId, {
      display_name: displayName.value.trim() || undefined,
    })
    await app.loadWorkflowList()
    app.setMessage('显示名已更新')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    metaSaving.value = false
  }
}

async function saveWorkflow() {
  if (readOnly.value) return
  saving.value = true
  try {
    await app.saveWorkflow()
    emit('saved')
  } finally {
    saving.value = false
  }
}

async function addLora(loraName) {
  if (!props.workflowId || readOnly.value || !loraName) return
  chainBusy.value = true
  try {
    await api.addLoraSlot(props.workflowId, { role: 'character', lora_name: loraName })
    await app.loadWorkflow(props.workflowId)
    app.setMessage('已添加 LoRA')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    chainBusy.value = false
  }
}

async function removeLora(nodeId) {
  if (!props.workflowId || readOnly.value) return
  if (
    !(await confirmDelete({
      title: '移除 LoRA',
      message: '从链中移除此 LoRA 节点？下游会自动重连 model/clip。',
    }))
  ) {
    return
  }
  chainBusy.value = true
  try {
    await api.removeLoraSlot(props.workflowId, nodeId)
    await app.loadWorkflow(props.workflowId)
    app.setMessage('已移除 LoRA')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    chainBusy.value = false
  }
}

async function deleteWorkflow() {
  if (!props.workflowId || readOnly.value) return
  const label = displayName.value || props.workflowId
  if (
    !(await confirmDelete({
      title: '删除子工作流',
      message: `确定删除「${label}」？JSON 与配置将一并移除，不可恢复。`,
      confirmText: '删除',
    }))
  ) {
    return
  }
  try {
    await api.deleteWorkflowVariant(props.workflowId)
    app.setMessage('子工作流已删除')
    emit('deleted')
  } catch (e) {
    app.setMessage(e.message, true)
  }
}

function goGenerate() {
  router.push({ path: '/generate', query: { workflow: props.workflowId } })
}
</script>

<template>
  <div>
    <div v-if="!workflowId" class="py-16 text-center text-sm text-muted-foreground">
      请在左侧选择母版或子工作流。
    </div>

    <div v-else-if="app.loading && !app.state.nodes.length" class="py-16 text-center text-sm text-muted-foreground">
      加载工作流…
    </div>

    <div v-else class="space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3">
        <div class="min-w-[200px] flex-1 space-y-2">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="text-base font-semibold">{{ displayName || workflowId }}</h3>
            <Badge v-if="readOnly" variant="outline" class="text-[10px]">母版 · 只读</Badge>
            <Badge v-else variant="secondary" class="text-[10px]">子工作流</Badge>
          </div>
          <div v-if="!readOnly" class="space-y-1">
            <Label class="text-xs">显示名</Label>
            <div class="flex flex-wrap gap-2">
              <Input v-model="displayName" class="max-w-xs" />
              <Button variant="outline" size="sm" :disabled="metaSaving" @click="saveMetaName">
                {{ metaSaving ? '…' : '更新名称' }}
              </Button>
            </div>
          </div>
          <p class="text-xs text-muted-foreground font-mono truncate">{{ workflowId }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" @click="goGenerate">去抽卡试跑</Button>
          <Button v-if="!readOnly" size="sm" :disabled="saving || app.loading" @click="saveWorkflow">
            {{ saving ? '保存中…' : '保存配置' }}
          </Button>
          <Button
            v-if="!readOnly"
            variant="destructive"
            size="sm"
            class="gap-1.5"
            @click="deleteWorkflow"
          >
            <Trash2 class="h-4 w-4" />
            删除
          </Button>
        </div>
      </div>

      <Alert v-if="readOnly" variant="default">
        母版只读。请新建或导入子工作流后再编辑 Checkpoint / LoRA / 其他节点。
      </Alert>

      <ModuleTabBar v-model="activeModule" :tabs="WORKFLOW_CONFIG_MODULES" />

      <div
        ref="panelRef"
        class="rounded-lg border border-border bg-card p-4 md:p-6 min-h-[360px]"
      >
        <div v-show="activeModule === 'checkpoint'" class="space-y-3">
          <p class="text-sm text-muted-foreground">底模，整条 LoRA 链接在其后。</p>
          <div v-if="hasCheckpoint">
            <ModelVisualPicker
              v-model="ckptName"
              folder="checkpoints"
              label="Checkpoint"
              :options="app.modelLists.checkpoints"
              :catalog="app.modelLists.checkpointCatalog"
              :missing-value="entry && app.modelSelectMissing(entry.nodeId, entry.field)"
              :disabled="panelDisabled"
              :loading="app.modelsLoading"
            />
          </div>
          <p v-else class="text-sm text-muted-foreground">当前工作流未检测到 Checkpoint 节点。</p>
        </div>

        <div v-show="activeModule === 'lora'" class="space-y-4">
          <p v-if="!readOnly" class="text-xs text-muted-foreground leading-relaxed">
            LoRA 按链顺序串联在 Checkpoint 之后；增删会自动写入 API JSON 并重连下游节点。
          </p>
          <LoraModulePanel
            manage-chain
            :max-slots="MAX_LORA_SLOTS"
            :disabled="panelDisabled"
            @remove="removeLora"
            @add="addLora"
          />
        </div>

        <div v-show="activeModule === 'other'">
          <OtherModulePanel :disabled="panelDisabled" />
        </div>
      </div>
    </div>
  </div>
</template>
