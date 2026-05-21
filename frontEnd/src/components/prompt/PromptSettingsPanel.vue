<script setup>
import GlobalPromptEditorPanel from '@/components/prompt/GlobalPromptEditorPanel.vue'
import GlobalRandomGroupsPanel from '@/components/prompt/GlobalRandomGroupsPanel.vue'
import PromptPresetManager from '@/components/prompt/PromptPresetManager.vue'
import { cn } from '@/lib/utils'

defineProps({
  compact: { type: Boolean, default: false },
})

const activeTab = defineModel({ type: String, default: 'global' })

const tabs = [
  { id: 'global', label: '全局提示词' },
  { id: 'random', label: '随机提示词组' },
  { id: 'presets', label: '提示词预设' },
]
</script>

<template>
  <div class="space-y-4">
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
      <GlobalPromptEditorPanel v-show="activeTab === 'global'" :compact="compact" />
      <GlobalRandomGroupsPanel v-show="activeTab === 'random'" />
      <PromptPresetManager v-show="activeTab === 'presets'" embedded />
    </div>
  </div>
</template>
