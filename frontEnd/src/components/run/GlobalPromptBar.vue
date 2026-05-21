<script setup>
import { onMounted, watch } from 'vue'
import Switch from '@/components/ui/Switch.vue'
import { openGlobalPromptModal } from '@/composables/useGlobalPromptModal.js'
import {
  globalPromptRevision,
  useGlobalPromptQuick,
} from '@/composables/useGlobalPromptQuick.js'

const {
  summary,
  loading,
  saving,
  load,
  setGlobalEnabled,
  setRandomGroupsMaster,
  shouldSkipBarReload,
} = useGlobalPromptQuick()

onMounted(() => load())

watch(globalPromptRevision, () => {
  if (shouldSkipBarReload()) return
  load()
})
</script>

<template>
  <div
    class="rounded-lg border border-dashed border-primary/30 bg-primary/5 px-3 py-2 text-xs space-y-2"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="text-muted-foreground space-y-0.5 min-w-0">
        <p class="font-medium text-foreground">全局提示词</p>
        <p v-if="loading && !saving" class="text-muted-foreground">加载中…</p>
        <p v-else class="truncate">
          {{ summary.pos }} · {{ summary.neg }} ·
          <span :class="summary.randomActive ? 'text-emerald-600' : 'text-amber-600'">
            {{ summary.randomText }}
          </span>
          · {{ summary.merge }}
        </p>
      </div>
      <button
        type="button"
        class="shrink-0 text-primary underline-offset-2 hover:underline text-xs"
        @click="openGlobalPromptModal('global')"
      >
        编辑全局 / 预设 →
      </button>
    </div>

    <div
      class="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-primary/15 pt-2"
      :class="saving ? 'opacity-70 pointer-events-none' : ''"
    >
      <label class="inline-flex items-center gap-2 cursor-pointer select-none">
        <Switch
          size="sm"
          :model-value="summary.enabled"
          :disabled="loading || saving"
          aria-label="全局正/负全文"
          @update:model-value="setGlobalEnabled"
        />
        <span class="text-foreground">全局正/负全文</span>
        <span
          class="text-[10px]"
          :class="summary.enabled ? 'text-emerald-600' : 'text-muted-foreground'"
        >
          {{ summary.enabled ? '开' : '关' }}
        </span>
      </label>

      <label class="inline-flex items-center gap-2 cursor-pointer select-none">
        <Switch
          size="sm"
          :model-value="summary.randomActive"
          :disabled="loading || saving || summary.rndTotal === 0"
          aria-label="全局随机组"
          @update:model-value="setRandomGroupsMaster"
        />
        <span class="text-foreground">全局随机组</span>
        <span
          class="text-[10px]"
          :class="summary.randomActive ? 'text-emerald-600' : 'text-muted-foreground'"
        >
          {{
            summary.rndTotal === 0
              ? '无组'
              : summary.randomActive
                ? '开'
                : '关'
          }}
        </span>
      </label>

      <span v-if="saving" class="text-[10px] text-primary">保存中…</span>
    </div>
  </div>
</template>
