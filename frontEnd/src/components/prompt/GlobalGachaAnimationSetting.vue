<script setup>
import { onMounted, ref, watch } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { PROMPT_AUTO_SAVE_DEBOUNCE_MS, useDebouncedSave } from '@/composables/useDebouncedSave.js'
import {
  globalConfigToPromptLayers,
  serializeGlobalPromptConfig,
} from '@/composables/usePromptConfig.js'
import { useGachaAnimation } from '@/composables/useGachaAnimation.js'
import { notifyGlobalPromptSaved } from '@/composables/useGlobalPromptQuick.js'
import Switch from '@/components/ui/Switch.vue'

const app = useAppStore()
const { setGlobalEnabled } = useGachaAnimation()
const enabled = ref(true)
const loading = ref(false)
let cachedCfg = null

async function load() {
  loading.value = true
  markReady(false)
  try {
    const res = await api.getGlobalPromptConfig()
    cachedCfg = globalConfigToPromptLayers(res.config)
    enabled.value = res.config?.gacha_animation_enabled !== false
    setGlobalEnabled(enabled.value)
  } finally {
    loading.value = false
    markReady(true)
  }
}

async function persist() {
  if (!cachedCfg) return
  await api.saveGlobalPromptConfig(
    serializeGlobalPromptConfig(cachedCfg, { gacha_animation_enabled: enabled.value }),
  )
  setGlobalEnabled(enabled.value)
  notifyGlobalPromptSaved()
}

const { saving, markReady, schedule, flush } = useDebouncedSave(persist, {
  delay: PROMPT_AUTO_SAVE_DEBOUNCE_MS,
})

watch(enabled, () => schedule())

onMounted(() => load().catch((e) => app.setMessage(e.message, true)))

defineExpose({ flush, load })
</script>

<template>
  <div
    class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border/70 bg-muted/15 px-3 py-2.5"
  >
    <div class="space-y-0.5">
      <p class="text-sm font-medium text-foreground">随机词抽卡动画</p>
      <p class="text-[11px] text-muted-foreground leading-relaxed">
        生成前播放滚轮抽词动画。关闭后仍会抽取随机组/词串组，仅跳过动画。生成页可临时覆盖。
      </p>
    </div>
    <div class="flex items-center gap-2 shrink-0">
      <Switch v-model="enabled" :disabled="loading || saving" aria-label="抽卡动画" />
      <span class="text-xs text-muted-foreground w-6">{{ saving ? '…' : enabled ? '开' : '关' }}</span>
    </div>
  </div>
</template>
