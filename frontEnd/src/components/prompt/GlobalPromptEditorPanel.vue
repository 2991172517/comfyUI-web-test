<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { PROMPT_AUTO_SAVE_DEBOUNCE_MS, useDebouncedSave } from '@/composables/useDebouncedSave.js'
import Label from '@/components/ui/Label.vue'
import Switch from '@/components/ui/Switch.vue'
import PromptTextarea from '@/components/prompt/PromptTextarea.vue'
import { usePromptEditorMode } from '@/composables/usePromptEditorMode.js'
import { PROMPT_COLON_WEIGHT_HINT } from '@/lib/promptFormatValidate.js'
import { emptyBatchPromptConfig, globalConfigToPromptLayers } from '@/composables/usePromptConfig.js'
import { notifyGlobalPromptSaved } from '@/composables/useGlobalPromptQuick.js'

defineProps({
  compact: { type: Boolean, default: false },
})

const app = useAppStore()
const { mode: promptEditorMode } = usePromptEditorMode()
const globalCfg = ref(emptyBatchPromptConfig())
const loading = ref(false)

async function load() {
  loading.value = true
  markReady(false)
  try {
    const res = await api.getGlobalPromptConfig()
    globalCfg.value = globalConfigToPromptLayers(res.config)
  } finally {
    loading.value = false
    await nextTick()
    markReady(true)
  }
}

async function persist() {
  await api.saveGlobalPromptConfig({
    enabled: globalCfg.value.enabled,
    positive: globalCfg.value.positive,
    negative: globalCfg.value.negative,
    merge: globalCfg.value.merge,
    random_groups: globalCfg.value.random_groups,
  })
  notifyGlobalPromptSaved()
}

const { saving, pending, markReady, schedule, flush } = useDebouncedSave(persist, {
  delay: PROMPT_AUTO_SAVE_DEBOUNCE_MS,
})

watch(
  globalCfg,
  () => schedule(),
  { deep: true },
)

onMounted(() => load().catch((e) => app.setMessage(e.message, true)))

defineExpose({ load, flush })
</script>

<template>
  <div class="space-y-4" :class="compact ? 'text-sm' : ''">
    <p v-if="loading" class="text-sm text-muted-foreground">加载中…</p>
    <template v-else>
      <p class="text-[11px] text-muted-foreground">
        修改后自动保存（约 {{ PROMPT_AUTO_SAVE_DEBOUNCE_MS / 1000 }} 秒防抖）。
        <span v-if="pending && !saving" class="text-muted-foreground">待保存…</span>
        <span v-else-if="saving" class="text-primary">保存中…</span>
      </p>
      <label class="flex items-center gap-2 text-sm cursor-pointer select-none">
        <Switch v-model="globalCfg.enabled" aria-label="启用全局提示词" />
        启用全局提示词
      </label>

      <div class="grid gap-3 lg:grid-cols-2">
        <div class="space-y-1.5">
          <Label class="text-xs">全局正向（完整）</Label>
          <PromptTextarea
            v-model="globalCfg.positive"
            :rows="compact ? 8 : 10"
            class="text-xs font-mono"
          />
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs">全局负向（完整）</Label>
          <PromptTextarea
            v-model="globalCfg.negative"
            :rows="compact ? 8 : 10"
            class="text-xs font-mono"
          />
        </div>
      </div>
      <p
        v-if="promptEditorMode !== 'tags'"
        class="text-xs leading-snug text-muted-foreground"
      >
        {{ PROMPT_COLON_WEIGHT_HINT }}
      </p>

      <div
        class="flex flex-wrap gap-4 rounded-md border border-border/70 bg-muted/15 p-3 text-xs"
      >
        <label class="flex items-center gap-2 cursor-pointer select-none">
          <Switch
            v-model="globalCfg.merge.global_before_workflow"
            size="sm"
            aria-label="全局全文排在工作流底稿之前"
          />
          全局全文排在「工作流底稿」之前
        </label>
        <label class="flex items-center gap-2 cursor-pointer select-none">
          <Switch
            v-model="globalCfg.merge.random_before_workflow"
            size="sm"
            aria-label="随机词排在工作流底稿之前"
          />
          随机词排在「工作流底稿」之前
        </label>
      </div>

      <p class="text-[11px] text-muted-foreground">
        全局随机组请在「随机提示词组」标签中编辑。
      </p>
    </template>
  </div>
</template>
