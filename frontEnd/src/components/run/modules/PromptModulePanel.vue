<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ChevronDown, Dices, Loader2 } from 'lucide-vue-next'
import { useAppStore } from '@/stores/useAppStore.js'
import {
  applyPromptConfigTo,
  emptyBatchPromptConfig,
  emptyFixedSides,
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
import BundleGroupsQuickViewDialog from '@/components/prompt/BundleGroupsQuickViewDialog.vue'
import PromptPresetExportDialog from '@/components/prompt/PromptPresetExportDialog.vue'
import PromptMergePreview from '@/components/prompt/PromptMergePreview.vue'
import { openGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'
import PromptEditorModeBar from '@/components/prompt/PromptEditorModeBar.vue'
import { usePromptEditorMode } from '@/composables/usePromptEditorMode.js'
import { PROMPT_COLON_WEIGHT_HINT } from '@/lib/promptFormatValidate.js'
import { cn } from '@/lib/utils'
import Switch from '@/components/ui/Switch.vue'
import { useVocabularyRandomMode } from '@/composables/useVocabularyRandomMode.js'
import { useGachaAnimation } from '@/composables/useGachaAnimation.js'
import { useSessionBundleGroups } from '@/composables/useSessionBundleGroups.js'
import { loadGachaAnimationGlobal } from '@/composables/useGachaAnimation.js'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const app = useAppStore()
const { mode: promptEditorMode } = usePromptEditorMode()
const { effectiveEnabled: gachaAnimationEnabled, setSessionOverride: setGachaSession } =
  useGachaAnimation()
const { masterEnabled: bundleGroupsEnabled } = useSessionBundleGroups()

onMounted(() => {
  loadGachaAnimationGlobal()
})

const promptConfig = computed(() => app.sessionPrompts)

const presetName = computed(() => app.sessionPromptPresetName)

const presetId = computed(() => app.sessionPromptPresetId)

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
const bundleQuickOpen = ref(false)

/** 词库六类随机词 UI 暂时隐藏 */
const SHOW_VOCAB_RANDOM_MODE = false

const {
  enabled: vocabRandomEnabled,
  lastPicks: vocabRandomPicks,
  rolling: vocabRandomRolling,
  rollForApp,
  clearFromApp,
} = useVocabularyRandomMode()

const previewSeed = computed(() => {
  const sn = app.workflowTargets?.seed_nodes?.[0]
  return sn?.seed != null ? Number(sn.seed) : null
})

function importSnapshotPayload() {
  return {
    session: serializePromptConfig(app.sessionPrompts),
    workflow: {
      positive: workflowText('positive'),
      negative: workflowText('negative'),
    },
  }
}

const isDirty = computed(() => {
  if (!importSnapshot.value) return false
  return importSnapshot.value !== JSON.stringify(importSnapshotPayload())
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
  const pos = String(cfg.positive ?? '').trim()
  const neg = String(cfg.negative ?? '').trim()
  applyPromptConfigTo(promptConfig.value, {
    ...cfg,
    positive: '',
    negative: '',
    fixed: emptyFixedSides(),
  })
  setWorkflowText('positive', pos)
  setWorkflowText('negative', neg)
  app.sessionPromptPresetId = cfg.preset_id || ''
  app.sessionPromptPresetName = cfg.preset_name || ''
  importSnapshot.value = JSON.stringify(importSnapshotPayload())
  editOpen.value = true
  app.setMessage(`已导入预设「${cfg.preset_name || '未命名'}」：正/负提示词已写入工作流底稿`)
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
  const hasText =
    workflowText('positive').trim() || workflowText('negative').trim()
  if (!hasLayer.value && !hasText) {
    app.setMessage('请先填写工作流提示词或添加随机组后再保存', true)
    return
  }
  exportOpen.value = true
}

async function onVocabRandomToggle(on) {
  if (on) {
    const result = await rollForApp(app)
    if (result.message) app.setMessage(result.message, !result.applied)
  } else {
    clearFromApp(app)
  }
}

async function rerollVocabRandom() {
  const result = await rollForApp(app)
  if (result.message) app.setMessage(result.message, !result.applied)
}

watch(vocabRandomEnabled, (on, prev) => {
  if (on === prev) return
  void onVocabRandomToggle(on)
})

async function onExportConfirm(payload) {
  exportSaving.value = true
  try {
    const result = await savePromptPresetExport(payload.mode, promptConfig.value, {
      presetId: presetId.value,
      name: payload.name,
      description: payload.description,
      workflowPositive: workflowText('positive'),
      workflowNegative: workflowText('negative'),
    })
    app.sessionPromptPresetId = result.preset.id
    app.sessionPromptPresetName = result.preset.name
    importSnapshot.value = JSON.stringify(importSnapshotPayload())
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
            v-if="!hasLayer"
            variant="outline"
            size="sm"
            :disabled="disabled"
            @click="openTempRandomDialog"
          >
            + 随机组
          </Button>
          <Button
            v-if="hasLayer"
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

      <div v-if="hasLayer && editOpen" class="space-y-3 border-b border-border/60 px-3 py-3">
        <p class="text-xs leading-relaxed text-muted-foreground">
          <strong class="font-medium text-foreground">随机组</strong>：每次生成从组内抽词条参与合并。
          正/负提示词在下方「工作流正/负向」中编辑（导入预设时已写入）。
        </p>
        <PromptConfigEditor
          :random-groups="promptConfig.random_groups"
          :random-bundle-groups="promptConfig.random_bundle_groups"
          :disabled="disabled"
          compact
          @update:random-groups="promptConfig.random_groups = $event"
          @update:random-bundle-groups="promptConfig.random_bundle_groups = $event"
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

      <div
        class="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-border/60 bg-muted/5 px-3 py-2"
      >
        <div class="flex items-center gap-2 shrink-0">
          <Label class="text-xs whitespace-nowrap">抽卡动画</Label>
          <Switch
            :model-value="gachaAnimationEnabled"
            size="sm"
            :disabled="disabled"
            aria-label="抽卡动画"
            title="生成前播放随机词滚轮动画"
            @update:model-value="setGachaSession"
          />
        </div>
        <span class="hidden sm:inline text-border text-muted-foreground/50" aria-hidden="true"
          >|</span
        >
        <div class="flex items-center gap-2 min-w-0">
          <button
            type="button"
            class="text-xs font-medium text-foreground hover:text-primary hover:underline whitespace-nowrap disabled:opacity-50"
            :disabled="disabled"
            title="查看全局与当次词串组内容"
            @click="bundleQuickOpen = true"
          >
            词串组
          </button>
          <Switch
            v-model="bundleGroupsEnabled"
            size="sm"
            :disabled="disabled"
            aria-label="随机词串组参与合并"
            title="关闭后不合并全局与当次词串组"
          />
          <Button
            variant="ghost"
            size="sm"
            class="h-6 px-1.5 text-[10px] text-muted-foreground shrink-0"
            :disabled="disabled"
            @click="bundleQuickOpen = true"
          >
            查看
          </Button>
        </div>
      </div>

      <div
        v-if="SHOW_VOCAB_RANDOM_MODE && app.promptEncode?.positive?.node_id"
        class="flex flex-col gap-2 border-b border-border/60 bg-muted/5 px-3 py-2.5"
      >
        <div class="flex flex-wrap items-center gap-2">
          <Label class="shrink-0 text-xs">随机词模式</Label>
          <Switch
            v-model="vocabRandomEnabled"
            size="sm"
            :disabled="disabled || vocabRandomRolling"
            aria-label="随机词模式"
          />
          <span class="text-[11px] text-muted-foreground">
            每次生成从词库六类各抽一词，追加到正向底稿（无抽卡动画）
          </span>
          <Button
            v-if="vocabRandomEnabled"
            variant="outline"
            size="sm"
            class="h-7 gap-1 px-2 text-xs"
            :disabled="disabled || vocabRandomRolling"
            @click="rerollVocabRandom"
          >
            <Loader2 v-if="vocabRandomRolling" class="h-3.5 w-3.5 animate-spin" />
            <Dices v-else class="h-3.5 w-3.5" />
            重新抽取
          </Button>
        </div>
        <div v-if="vocabRandomEnabled && vocabRandomPicks.length" class="flex flex-wrap gap-1.5">
          <Badge
            v-for="pick in vocabRandomPicks"
            :key="pick.name"
            variant="secondary"
            class="text-[10px] font-normal"
          >
            {{ pick.name }}：{{ pick.value }}
          </Badge>
        </div>
      </div>

      <div class="px-3 pt-2">
        <PromptEditorModeBar compact />
      </div>

      <div class="grid gap-3 p-3 pt-1 lg:grid-cols-2">
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

    <BundleGroupsQuickViewDialog v-model:open="bundleQuickOpen" />

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
