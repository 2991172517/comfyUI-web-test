<script setup>
import { onMounted } from 'vue'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { applyPromptConfigTo } from '@/composables/usePromptConfig.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import PromptPresetPicker from '@/components/prompt/PromptPresetPicker.vue'
import PromptConfigEditor from '@/components/prompt/PromptConfigEditor.vue'
import { openGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'

defineProps({ disabled: { type: Boolean, default: false } })

const app = useAppStore()
const batch = useBatchStore()

onMounted(() => {
  batch.loadBatchPromptConfig().catch((e) => app.setMessage(e.message, true))
})

function onImport(cfg) {
  applyPromptConfigTo(batch.batchPrompts, cfg)
  batch.importedPresetName = cfg.preset_name || ''
  app.setMessage(`已导入预设「${cfg.preset_name || '未命名'}」到本批配置`)
}
</script>

<template>
  <Card>
    <CardHeader class="pb-2">
      <div class="flex flex-wrap items-start justify-between gap-2">
        <div>
          <CardTitle class="text-base">批量提示词</CardTitle>
          <CardDescription>
            工作流 →
            <button
              type="button"
              class="text-primary underline-offset-2 hover:underline"
              @click="openGlobalPromptModal('global')"
            >
              全局默认
            </button>
            → 本页固定 → 各随机组（随机加权 / 按图序号顺序轮询）
          </CardDescription>
        </div>
        <div class="flex items-center gap-2">
          <Badge v-if="batch.importedPresetName" variant="secondary" class="text-[10px]">
            {{ batch.importedPresetName }}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            :disabled="disabled || batch.batchPromptSaving"
            @click="batch.saveBatchPromptConfig"
          >
            {{ batch.batchPromptSaving ? '保存中…' : '保存为批量默认' }}
          </Button>
        </div>
      </div>
    </CardHeader>
    <CardContent class="space-y-4">
      <PromptPresetPicker :disabled="disabled" @import="onImport" />
      <PromptConfigEditor
        :random-groups="batch.batchPrompts.random_groups"
        :random-bundle-groups="batch.batchPrompts.random_bundle_groups"
        :disabled="disabled"
        compact
        @update:random-groups="batch.batchPrompts.random_groups = $event"
        @update:random-bundle-groups="batch.batchPrompts.random_bundle_groups = $event"
      />
    </CardContent>
  </Card>
</template>
