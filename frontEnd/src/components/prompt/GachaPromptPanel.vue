<script setup>
import { computed, ref } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { applyPromptConfigTo, serializePromptConfig } from '@/composables/usePromptConfig.js'
import { savePromptPresetExport } from '@/composables/usePromptPresetExport.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import PromptPresetPicker from '@/components/prompt/PromptPresetPicker.vue'
import PromptConfigEditor from '@/components/prompt/PromptConfigEditor.vue'
import PromptPresetExportDialog from '@/components/prompt/PromptPresetExportDialog.vue'
import AnimatedCollapse from '@/components/ui/AnimatedCollapse.vue'

defineProps({ disabled: { type: Boolean, default: false } })

const store = useAppStore()
const exportOpen = ref(false)
const exportSaving = ref(false)
const importSnapshot = ref('')
const configEditOpen = ref(true)

const isDirty = computed(() => {
  if (!importSnapshot.value) return false
  return importSnapshot.value !== JSON.stringify(serializePromptConfig(store.sessionPrompts))
})

function onImport(cfg) {
  applyPromptConfigTo(store.sessionPrompts, cfg)
  store.sessionPromptPresetId = cfg.preset_id || ''
  store.sessionPromptPresetName = cfg.preset_name || ''
  importSnapshot.value = JSON.stringify(serializePromptConfig(store.sessionPrompts))
  store.setMessage(`已导入预设「${cfg.preset_name || '未命名'}」`)
}

function clearSession() {
  store.clearSessionPrompts()
  importSnapshot.value = ''
  store.setMessage('已清空抽卡提示词附加')
}

function openExport() {
  if (!store.hasSessionPrompts()) {
    store.setMessage('请先填写固定提示或添加随机组后再导出', true)
    return
  }
  exportOpen.value = true
}

async function onExportConfirm({ mode, name, description }) {
  exportSaving.value = true
  try {
    const result = await savePromptPresetExport(mode, store.sessionPrompts, {
      presetId: store.sessionPromptPresetId,
      name,
      description,
    })
    store.sessionPromptPresetId = result.preset.id
    store.sessionPromptPresetName = result.preset.name
    importSnapshot.value = JSON.stringify(serializePromptConfig(store.sessionPrompts))
    exportOpen.value = false
    store.setMessage(
      result.mode === 'overwrite'
        ? `已覆盖预设「${result.preset.name}」`
        : `已保存为新预设「${result.preset.name}」`,
    )
  } catch (e) {
    store.setMessage(e.message, true)
  } finally {
    exportSaving.value = false
  }
}
</script>

<template>
  <Card>
    <CardHeader class="pb-2">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <CardTitle class="text-base">抽卡提示词</CardTitle>
          <CardDescription>
            叠加：工作流 → 全局默认 → 本页（固定 + 随机组，抽卡时随机组各抽 1 条）
          </CardDescription>
        </div>
        <div class="flex flex-wrap items-center gap-1.5">
          <Badge v-if="store.sessionPromptPresetName" variant="secondary">
            {{ store.sessionPromptPresetName }}
          </Badge>
          <Badge v-if="isDirty" variant="outline" class="text-[10px]">已修改</Badge>
        </div>
      </div>
    </CardHeader>
    <CardContent class="space-y-4">
      <div class="flex flex-wrap items-end gap-2">
        <div class="flex-1 min-w-[200px]">
          <PromptPresetPicker :disabled="disabled" @import="onImport" />
        </div>
        <Button
          variant="outline"
          size="sm"
          class="shrink-0"
          :disabled="disabled || !store.hasSessionPrompts()"
          @click="openExport"
        >
          导出为预设
        </Button>
      </div>
      <button
        type="button"
        class="text-sm font-medium text-muted-foreground hover:text-foreground mb-2"
        @click="configEditOpen = !configEditOpen"
      >
        {{ configEditOpen ? '收起' : '展开' }}编辑随机组
      </button>
      <AnimatedCollapse v-model="configEditOpen">
        <PromptConfigEditor
          :random-groups="store.sessionPrompts.random_groups"
          :random-bundle-groups="store.sessionPrompts.random_bundle_groups"
          :disabled="disabled"
          compact
          @update:random-groups="store.sessionPrompts.random_groups = $event"
          @update:random-bundle-groups="store.sessionPrompts.random_bundle_groups = $event"
        />
      </AnimatedCollapse>
      <button
        type="button"
        class="text-xs text-muted-foreground underline hover:text-foreground"
        :disabled="disabled"
        @click="clearSession"
      >
        清空本页附加
      </button>
    </CardContent>
  </Card>

  <PromptPresetExportDialog
    v-model:open="exportOpen"
    :imported-preset-id="store.sessionPromptPresetId"
    :imported-preset-name="store.sessionPromptPresetName"
    :saving="exportSaving"
    @confirm="onExportConfirm"
  />
</template>
