<script setup>
import { computed, onMounted, ref } from 'vue'
import { Sparkles } from 'lucide-vue-next'
import { ensureWebbyNomineeElement } from '@/lib/webbyNomineeElement.js'
import { useGenerateWithTagFX } from '@/composables/useGenerateWithTagFX.js'
import {
  allowsBatch,
  authSingleQuota,
  authSingleRemaining,
  hasSingleQuotaLeft,
} from '@/composables/useAuth.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import '@/assets/webby-nominee.css'
import '@/assets/tag-absorb.css'
import '@/assets/random-gacha.css'

const props = defineProps({
  sweep: { type: Boolean, default: false },
})

const app = useAppStore()
const batch = useBatchStore()
const hostRef = ref(null)

const { animating, generateWithFX } = useGenerateWithTagFX({
  sweep: () => props.sweep,
  getTargetEl: () => hostRef.value?.querySelector('.js-badge') ?? null,
})

onMounted(() => {
  ensureWebbyNomineeElement()
})

const canGenerate = computed(() => {
  if (app.loading || !app.selectedId || !app.healthOk) return false
  if (props.sweep) return allowsBatch() && batch.plannedTotal > 0 && !batch.isBatchRunning
  return !app.isGenerating && hasSingleQuotaLeft()
})

const label = computed(() => {
  if (props.sweep) {
    return batch.isBatchRunning ? '批量中' : '批量'
  }
  return app.isGenerating ? '生成中' : '生成'
})

const altLabel = computed(() => (props.sweep ? '开始!' : 'GO!'))

const quotaHint = computed(() => {
  void authSingleQuota.value
  void authSingleRemaining.value
  if (allowsBatch() || props.sweep) return ''
  const total = authSingleQuota.value
  const left = authSingleRemaining.value
  if (total == null || left == null) return ''
  return `${left}/${total}`
})

async function onGenerate() {
  if (!canGenerate.value) return
  await generateWithFX()
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed bottom-0 left-0 z-40 flex flex-col items-start pointer-events-none px-4 pb-4 pt-2 gap-1"
      aria-label="特效生成按钮"
    >
      <p
        v-if="quotaHint"
        class="pointer-events-none text-[10px] tabular-nums text-muted-foreground pl-1"
      >
        剩余 {{ quotaHint }}
      </p>
      <div ref="hostRef" class="pointer-events-auto -ml-1 sm:ml-0">
        <webby-nominee
          class="webby-generate-fab"
          :class="{ 'is-disabled': !canGenerate }"
        >
          <div class="badge js-badge">
            <button
              type="button"
              class="badge__btn"
              :disabled="!canGenerate || animating"
              :title="
                !hasSingleQuotaLeft() && !allowsBatch() && !sweep
                  ? '本次登录单图额度已用尽'
                  : sweep
                    ? `开始批量（${batch.plannedTotal || 0} 张）`
                    : '生成一张'
              "
              @click="onGenerate"
            >
              <span class="badge__face">
                <Sparkles aria-hidden="true" />
                <span>{{ animating ? '吸入中…' : label }}</span>
              </span>
              <span class="badge__alt">{{ altLabel }}</span>
            </button>
          </div>
          <div class="aura" aria-hidden="true" />
          <div class="overlay" aria-hidden="true" />
          <canvas class="js-canvas" aria-hidden="true" />
        </webby-nominee>
      </div>
    </div>
  </Teleport>
</template>
