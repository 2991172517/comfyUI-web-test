<script setup>
import { onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Tags } from 'lucide-vue-next'
import GlobalPromptEditorPanel from '@/components/prompt/GlobalPromptEditorPanel.vue'
import GlobalRandomGroupsPanel from '@/components/prompt/GlobalRandomGroupsPanel.vue'
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
const presetPanelRef = ref(null)

const tabs = [
  { id: 'global', label: '全局提示词' },
  { id: 'random', label: '随机提示词组' },
  { id: 'presets', label: '提示词预设' },
]

async function flushPendingSaves() {
  await Promise.all([
    globalPanelRef.value?.flush?.(),
    randomPanelRef.value?.flush?.(),
    presetPanelRef.value?.flush?.(),
  ])
}

defineExpose({ flushPendingSaves })

onUnmounted(() => {
  void flushPendingSaves()
})
</script>

<template>
  <div class="space-y-4">
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
        Tag 词库管理（分类 / 增删 / 默认权重）
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
        @click="activeTab = t.id"
      >
        {{ t.label }}
      </button>
    </div>

    <div :class="compact ? '' : 'rounded-lg border border-border bg-card p-4 md:p-6'">
      <GlobalPromptEditorPanel
        ref="globalPanelRef"
        v-show="activeTab === 'global'"
        :compact="compact"
      />
      <GlobalRandomGroupsPanel ref="randomPanelRef" v-show="activeTab === 'random'" />
      <PromptPresetManager ref="presetPanelRef" v-show="activeTab === 'presets'" embedded />
    </div>
  </div>
</template>
