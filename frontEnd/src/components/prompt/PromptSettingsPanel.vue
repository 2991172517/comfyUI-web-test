<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Tags } from 'lucide-vue-next'
import GlobalPromptEditorPanel from '@/components/prompt/GlobalPromptEditorPanel.vue'
import GlobalRandomGroupsPanel from '@/components/prompt/GlobalRandomGroupsPanel.vue'
import GlobalRandomBundleGroupsPanel from '@/components/prompt/GlobalRandomBundleGroupsPanel.vue'
import GlobalGachaAnimationSetting from '@/components/prompt/GlobalGachaAnimationSetting.vue'
import PromptPresetManager from '@/components/prompt/PromptPresetManager.vue'
import {
  PROMPT_EDITOR_MODE_OPTIONS,
  usePromptEditorMode,
} from '@/composables/usePromptEditorMode.js'
import { cn } from '@/lib/utils'

defineProps({
  compact: { type: Boolean, default: false },
})

const activeTab = defineModel({ type: String, default: 'global' })
const { mode: editorMode } = usePromptEditorMode()

const globalPanelRef = ref(null)
const randomPanelRef = ref(null)
const bundlePanelRef = ref(null)
const gachaPanelRef = ref(null)
const presetPanelRef = ref(null)

const tabs = [
  { id: 'global', label: '全局提示词' },
  { id: 'random', label: '随机词组' },
  { id: 'bundles', label: '随机词串组' },
  { id: 'presets', label: '提示词预设' },
]

async function flushActiveTab() {
  const tab = activeTab.value
  if (tab === 'global') await globalPanelRef.value?.flush?.()
  else if (tab === 'random') await randomPanelRef.value?.flush?.()
  else if (tab === 'bundles') await bundlePanelRef.value?.flush?.()
  else if (tab === 'gacha') await gachaPanelRef.value?.flush?.()
  else if (tab === 'presets') await presetPanelRef.value?.flush?.()
}

async function flushPendingSaves() {
  await gachaPanelRef.value?.flush?.()
  await flushActiveTab()
}

async function switchTab(id) {
  if (id === activeTab.value) return
  await flushActiveTab()
  activeTab.value = id
}

defineExpose({ flushPendingSaves, flushActiveTab })
</script>

<template>
  <div class="space-y-4">
    <GlobalGachaAnimationSetting ref="gachaPanelRef" />

    <div class="rounded-lg border border-border bg-muted/15 p-3 space-y-2">
      <p class="text-xs font-medium text-foreground">提示词输入模式（全局）</p>
      <div class="flex flex-wrap gap-2">
        <label
          v-for="opt in PROMPT_EDITOR_MODE_OPTIONS"
          :key="opt.id"
          class="flex cursor-pointer items-start gap-2 rounded-md border px-3 py-2 text-xs transition-colors"
          :class="
            editorMode === opt.id
              ? 'border-primary bg-primary/10'
              : 'border-border hover:bg-muted/40'
          "
        >
          <input
            v-model="editorMode"
            type="radio"
            class="mt-0.5"
            :value="opt.id"
          />
          <span>
            <span class="font-medium text-foreground">{{ opt.label }}</span>
            <span class="block text-muted-foreground">{{ opt.desc }}</span>
          </span>
        </label>
      </div>
      <RouterLink
        to="/settings/tags"
        class="mt-2 inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
      >
        <Tags class="h-3.5 w-3.5" />
        Tag 显示管理（喜好排序 / 删 tag / 删组）
      </RouterLink>
    </div>

    <div
      class="inline-flex rounded-lg border border-border p-0.5 text-sm"
      role="tablist"
    >
      <button
        v-for="t in tabs"
        :key="t.id"
        type="button"
        role="tab"
        :aria-selected="activeTab === t.id"
        :class="
          cn(
            'rounded-md px-4 py-1.5 transition-colors whitespace-nowrap',
            activeTab === t.id
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground',
          )
        "
        @click="switchTab(t.id)"
      >
        {{ t.label }}
      </button>
    </div>

    <div :class="compact ? '' : 'rounded-lg border border-border bg-card p-4 md:p-6'">
      <GlobalPromptEditorPanel
        v-if="activeTab === 'global'"
        ref="globalPanelRef"
        :compact="compact"
      />
      <GlobalRandomGroupsPanel v-else-if="activeTab === 'random'" ref="randomPanelRef" />
      <GlobalRandomBundleGroupsPanel v-else-if="activeTab === 'bundles'" ref="bundlePanelRef" />
      <PromptPresetManager v-else-if="activeTab === 'presets'" ref="presetPanelRef" embedded />
    </div>
  </div>
</template>
