<script setup>
import { computed, ref } from 'vue'
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
import PromptPresetExportDialog from '@/components/prompt/PromptPresetExportDialog.vue'
import PromptMergePreview from '@/components/prompt/PromptMergePreview.vue'
import { openGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const app = useAppStore()

const promptConfig = computed(() => app.sessionPrompts)

const presetName = computed(() => app.sessionPromptPresetName)

const presetId = computed(() => app.sessionPromptPresetId)

const hasLayer = computed(() => promptConfigHasContent(promptConfig.value))
const layerSummary = computed(() => promptConfigSummary(promptConfig.value))

const importOpen = ref(false)
const exportOpen = ref(false)
const exportSaving = ref(false)
const importSnapshot = ref('')
const editOpen = ref(false)

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
  editOpen.value = true
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

function openExport() {
  if (!hasLayer.value) {
    app.setMessage('请先导入或编辑预设内容', true)
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
    <div class="grid gap-3 lg:grid-cols-2">
      <div v-if="app.promptEncode?.positive?.node_id" class="space-y-1.5">
        <Label class="text-xs">
          工作流正向
          <span class="text-muted-foreground font-normal">（底稿 #{{ app.promptEncode.positive.node_id }}）</span>
        </Label>
        <PromptTextarea
          :model-value="workflowText('positive')"
          :rows="8"
          class="text-sm"
          :disabled="disabled"
          @update:model-value="setWorkflowText('positive', $event)"
        />
      </div>
      <div v-if="app.promptEncode?.negative?.node_id" class="space-y-1.5">
        <Label class="text-xs">
          工作流负向
          <span class="text-muted-foreground font-normal">（底稿 #{{ app.promptEncode.negative.node_id }}）</span>
        </Label>
        <PromptTextarea
          :model-value="workflowText('negative')"
          :rows="8"
          class="text-sm"
          :disabled="disabled"
          @update:model-value="setWorkflowText('negative', $event)"
        />
      </div>
    </div>

    <!-- 预设附加：默认仅按钮，导入后显示摘要 -->
    <div class="rounded-lg border border-border/80 bg-muted/15 px-3 py-3 space-y-3">
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-sm font-medium">
          预设附加
        </span>
        <template v-if="hasLayer">
          <Badge v-if="presetName" variant="secondary" class="text-[10px]">{{ presetName }}</Badge>
          <span v-if="layerSummary" class="text-[11px] text-muted-foreground">{{ layerSummary }}</span>
          <Badge v-if="isDirty" variant="outline" class="text-[10px]">已修改</Badge>
        </template>
      </div>

      <div v-if="!hasLayer" class="flex flex-wrap items-center gap-2">
        <Button size="sm" :disabled="disabled" @click="importOpen = true">导入预设</Button>
        <p class="text-[11px] text-muted-foreground">
          不导入则仅使用上方工作流底稿 + 全局提示词（悬浮按钮可编辑）
        </p>
      </div>

      <template v-else>
        <div class="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" :disabled="disabled" @click="importOpen = true">
            更换预设
          </Button>
          <Button variant="ghost" size="sm" :disabled="disabled" @click="editOpen = !editOpen">
            {{ editOpen ? '收起编辑' : '微调' }}
          </Button>
          <Button variant="ghost" size="sm" class="text-muted-foreground" :disabled="disabled" @click="clearLayer">
            清除
          </Button>
        </div>

        <div v-if="editOpen" class="space-y-3 pt-1 border-t border-border/60">
          <p class="text-[11px] text-muted-foreground leading-relaxed">
            <strong class="text-foreground font-medium">固定前后缀</strong>：包在工作流底稿外一层。
            <strong class="text-foreground font-medium">随机组</strong>：每次生成抽词条。
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
            :show-fixed="true"
            @update:fixed="promptConfig.fixed = $event"
            @update:random-groups="promptConfig.random_groups = $event"
          />
          <div class="flex flex-wrap gap-3 text-[11px]">
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
      </template>
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

    <PromptPresetExportDialog
      v-model:open="exportOpen"
      :imported-preset-id="presetId"
      :imported-preset-name="presetName"
      :saving="exportSaving"
      @confirm="onExportConfirm"
    />
  </div>
</template>
