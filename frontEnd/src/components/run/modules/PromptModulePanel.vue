<script setup>
import { computed, ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import {
  applyPromptConfigTo,
  emptyBatchPromptConfig,
  promptConfigHasContent,
  promptConfigSummary,
  serializePromptConfig,
} from '@/composables/usePromptConfig.js'
import { savePromptPresetExport } from '@/composables/usePromptPresetExport.js'
import Label from '@/components/ui/Label.vue'
import PromptTextarea from '@/components/prompt/PromptTextarea.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import PromptConfigEditor from '@/components/prompt/PromptConfigEditor.vue'
import PromptPresetImportDialog from '@/components/prompt/PromptPresetImportDialog.vue'
import TempRandomGroupDialog from '@/components/prompt/TempRandomGroupDialog.vue'
import PromptPresetExportDialog from '@/components/prompt/PromptPresetExportDialog.vue'
import PromptMergePreview from '@/components/prompt/PromptMergePreview.vue'
import { openGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'
import { usePromptEditorMode } from '@/composables/usePromptEditorMode.js'
import { PROMPT_COLON_WEIGHT_HINT } from '@/lib/promptFormatValidate.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const app = useAppStore()
const { mode: promptEditorMode } = usePromptEditorMode()

const promptConfig = computed(() => app.sessionPrompts)

const presetName = computed(() => app.sessionPromptPresetName)

const presetId = computed(() => app.sessionPromptPresetId)

/** 仅导入预设后显示固定追加；临时随机组不需要 */
const showFixedAppend = computed(() => Boolean(presetId.value || presetName.value))

const hasLayer = computed(() => promptConfigHasContent(promptConfig.value))
const layerSummary = computed(() => promptConfigSummary(promptConfig.value))

const importOpen = ref(false)
const tempRandomOpen = ref(false)
const exportOpen = ref(false)
const exportSaving = ref(false)
const importSnapshot = ref('')
const editOpen = ref(false)
const positiveOpen = ref(true)
const negativeOpen = ref(true)

const previewSeed = computed(() => {
  const sn = app.workflowTargets?.seed_nodes?.[0]
  return sn?.seed != null ? Number(sn.seed) : null
})

const isDirty = computed(() => {
  if (!importSnapshot.value) return false
  return importSnapshot.value !== JSON.stringify(serializePromptConfig(app.sessionPrompts))
})

function workflowText(side) {
  const enc = app.promptEncode?.[side]
  if (!enc?.node_id) return ''
  const node = app.state.nodes.find((n) => n.id === enc.node_id)
  const field = node?.fields?.find((f) => f.key === 'text')
  return field ? app.fieldValue(enc.node_id, field) : ''
}

function setWorkflowText(side, val) {
  const enc = app.promptEncode?.[side]
  if (!enc?.node_id) return
  app.updateField(enc.node_id, 'text', val)
}

function onImport(cfg) {
  applyPromptConfigTo(promptConfig.value, cfg)
  app.sessionPromptPresetId = cfg.preset_id || ''
  app.sessionPromptPresetName = cfg.preset_name || ''
  importSnapshot.value = JSON.stringify(serializePromptConfig(app.sessionPrompts))
  editOpen.value = false
  app.setMessage(`已导入预设「${cfg.preset_name || '未命名'}」`)
}

function clearLayer() {
  applyPromptConfigTo(promptConfig.value, emptyBatchPromptConfig())
  app.sessionPromptPresetId = ''
  app.sessionPromptPresetName = ''
  importSnapshot.value = ''
  editOpen.value = false
  app.setMessage('已清除预设附加')
}

function toggleEdit() {
  editOpen.value = !editOpen.value
}

function openTempRandomDialog() {
  tempRandomOpen.value = true
}

function openExportFromTemp() {
  tempRandomOpen.value = false
  openExport()
}

function openExport() {
  if (!hasLayer.value) {
    app.setMessage('请先添加随机组或固定前后缀后再保存', true)
    return
  }
  exportOpen.value = true
}

async function onExportConfirm(payload) {
  exportSaving.value = true
  try {
    const result = await savePromptPresetExport(payload.mode, promptConfig.value, {
      presetId: presetId.value,
      name: payload.name,
      description: payload.description,
    })
    app.sessionPromptPresetId = result.preset.id
    app.sessionPromptPresetName = result.preset.name
    importSnapshot.value = JSON.stringify(serializePromptConfig(app.sessionPrompts))
    exportOpen.value = false
    app.setMessage(
      result.mode === 'overwrite'
        ? `已覆盖预设「${result.preset.name}」`
        : `已保存预设「${result.preset.name}」`,
    )
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    exportSaving.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="rounded-lg border border-border/80 bg-muted/10">
      <div
        class="flex min-h-10 items-center gap-2 border-b border-border/60 px-3 py-2"
      >
        <span class="shrink-0 text-sm font-medium">预设附加</span>

        <template v-if="hasLayer">
          <Badge v-if="presetName" variant="secondary" class="max-w-[9rem] shrink-0 truncate text-[10px]">
            {{ presetName }}
          </Badge>
          <span v-if="layerSummary" class="min-w-0 flex-1 truncate text-xs text-muted-foreground">
            {{ layerSummary }}
          </span>
          <Badge v-if="isDirty" variant="outline" class="shrink-0 text-[10px]">已修改</Badge>
        </template>

        <span v-else class="min-w-0 flex-1" aria-hidden="true" />

        <div class="flex shrink-0 items-center gap-1">
          <Button
            size="sm"
            :variant="hasLayer ? 'outline' : 'default'"
            :disabled="disabled"
            @click="importOpen = true"
          >
            {{ hasLayer ? '更换' : '导入预设' }}
          </Button>
          <Button
            v-if="!showFixedAppend"
            variant="outline"
            size="sm"
            :disabled="disabled"
            @click="openTempRandomDialog"
          >
            {{ hasLayer ? '编辑随机组' : '+ 随机组' }}
          </Button>
          <Button
            v-if="showFixedAppend"
            variant="ghost"
            size="sm"
            class="gap-1 px-2"
            :disabled="disabled"
            @click="toggleEdit"
          >
            <ChevronDown
              :class="cn('h-3.5 w-3.5 transition-transform', editOpen && 'rotate-180')"
            />
            {{ editOpen ? '收起' : '展开' }}
          </Button>
          <Button
            v-if="hasLayer"
            variant="ghost"
            size="sm"
            class="px-2 text-muted-foreground"
            :disabled="disabled"
            @click="clearLayer"
          >
            清除
          </Button>
        </div>
      </div>

      <div v-if="showFixedAppend && editOpen" class="space-y-3 border-b border-border/60 px-3 py-3">
        <p class="text-xs leading-relaxed text-muted-foreground">
          <strong class="font-medium text-foreground">固定前后缀</strong>：包在工作流底稿外一层。
          <strong class="font-medium text-foreground">随机组</strong>：每次生成抽词条。
          预设里的正/负「全文」已随导入生效，合并预览可见；若要改正/负全文请到
          <button
            type="button"
            class="text-primary underline"
            @click="openGlobalPromptModal('global')"
          >
            提示词设置
          </button>。
        </p>
        <PromptConfigEditor
          :fixed="promptConfig.fixed"
          :random-groups="promptConfig.random_groups"
          :disabled="disabled"
          compact
          :show-fixed="showFixedAppend"
          @update:fixed="promptConfig.fixed = $event"
          @update:random-groups="promptConfig.random_groups = $event"
        />
        <div class="flex flex-wrap gap-3 text-xs">
          <label class="flex items-center gap-1.5">
            <input
              v-model="promptConfig.merge.global_before_workflow"
              type="checkbox"
              class="accent-primary"
              :disabled="disabled"
            />
            全局全文在工作流底稿前
          </label>
          <label class="flex items-center gap-1.5">
            <input
              v-model="promptConfig.merge.random_before_workflow"
              type="checkbox"
              class="accent-primary"
              :disabled="disabled"
            />
            随机词在工作流底稿前
          </label>
        </div>
        <Button variant="link" size="sm" class="h-auto p-0 text-xs" :disabled="disabled" @click="openExport">
          保存为预设…
        </Button>
      </div>

      <div class="grid gap-3 p-3 lg:grid-cols-2">
        <div
          v-if="app.promptEncode?.positive?.node_id"
          class="rounded-md border border-border/70 bg-background/50"
        >
          <div class="flex min-h-9 items-center gap-2 border-b border-border/60 px-2.5 py-1.5">
            <Label class="min-w-0 flex-1 truncate text-xs">
              工作流正向
              <span class="font-normal text-muted-foreground">（底稿 #{{ app.promptEncode.positive.node_id }}）</span>
            </Label>
            <Button
              variant="ghost"
              size="sm"
              class="h-7 shrink-0 gap-1 px-2 text-xs"
              @click="positiveOpen = !positiveOpen"
            >
              <ChevronDown :class="cn('h-3.5 w-3.5 transition-transform', positiveOpen && 'rotate-180')" />
              {{ positiveOpen ? '收起' : '展开' }}
            </Button>
          </div>
          <div v-show="positiveOpen" class="p-2">
            <PromptTextarea
              :model-value="workflowText('positive')"
              prompt-side="positive"
              :rows="8"
              class="text-sm"
              :disabled="disabled"
              @update:model-value="setWorkflowText('positive', $event)"
            />
          </div>
        </div>
        <div
          v-if="app.promptEncode?.negative?.node_id"
          class="rounded-md border border-border/70 bg-background/50"
        >
          <div class="flex min-h-9 items-center gap-2 border-b border-border/60 px-2.5 py-1.5">
            <Label class="min-w-0 flex-1 truncate text-xs">
              工作流负向
              <span class="font-normal text-muted-foreground">（底稿 #{{ app.promptEncode.negative.node_id }}）</span>
            </Label>
            <Button
              variant="ghost"
              size="sm"
              class="h-7 shrink-0 gap-1 px-2 text-xs"
              @click="negativeOpen = !negativeOpen"
            >
              <ChevronDown :class="cn('h-3.5 w-3.5 transition-transform', negativeOpen && 'rotate-180')" />
              {{ negativeOpen ? '收起' : '展开' }}
            </Button>
          </div>
          <div v-show="negativeOpen" class="p-2">
            <PromptTextarea
              :model-value="workflowText('negative')"
              prompt-side="negative"
              :rows="8"
              class="text-sm"
              :disabled="disabled"
              @update:model-value="setWorkflowText('negative', $event)"
            />
          </div>
        </div>
      </div>
      <p
        v-if="promptEditorMode !== 'tags'"
        class="border-t border-border/60 px-3 py-2 text-xs leading-snug text-muted-foreground"
      >
        {{ PROMPT_COLON_WEIGHT_HINT }}
      </p>
    </div>

    <PromptMergePreview
      v-if="app.selectedId"
      :workflow-id="app.selectedId"
      :overrides="app.overrides"
      :prompt-config="hasLayer ? promptConfig : null"
      :style-enabled="app.styleEnabled"
      :prompt-seed="previewSeed"
    />

    <PromptPresetImportDialog v-model:open="importOpen" @import="onImport" />

    <TempRandomGroupDialog
      v-model:open="tempRandomOpen"
      :disabled="disabled"
      @save-preset="openExportFromTemp"
    />

    <PromptPresetExportDialog
      v-model:open="exportOpen"
      :imported-preset-id="presetId"
      :imported-preset-name="presetName"
      :saving="exportSaving"
      @confirm="onExportConfirm"
    />
  </div>
</template>
