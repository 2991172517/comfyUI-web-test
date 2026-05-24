<script setup>
import { computed, ref } from 'vue'
import AnimatedCollapse from '@/components/ui/AnimatedCollapse.vue'
import Button from '@/components/ui/Button.vue'
import { displayPromptComma } from '@/lib/promptDisplay.js'
import { Check, Copy } from 'lucide-vue-next'

const props = defineProps({
  meta: { type: Object, default: null },
  workflowId: { type: String, default: '' },
  compact: { type: Boolean, default: false },
  promptsOpen: { type: Boolean, default: false },
})

const copiedSide = ref('')
const showPosRaw = ref(false)
const showNegRaw = ref(false)

const posComma = computed(() => displayPromptComma(props.meta, 'positive'))
const negComma = computed(() => displayPromptComma(props.meta, 'negative'))

function samplerLine(s) {
  if (!s || typeof s !== 'object') return ''
  const parts = []
  if (s.sampler_name) parts.push(String(s.sampler_name))
  if (s.steps != null && s.steps !== '') parts.push(`steps=${s.steps}`)
  if (s.cfg != null && s.cfg !== '') parts.push(`cfg=${s.cfg}`)
  if (s.scheduler) parts.push(`scheduler=${s.scheduler}`)
  if (s.denoise != null && s.denoise !== '') parts.push(`denoise=${s.denoise}`)
  if (s.seed != null && s.seed !== '') parts.push(`seed=${s.seed}`)
  return parts.join(' · ')
}

const primarySamplerLine = computed(() => samplerLine(props.meta?.sampler))
const pass2SamplerLine = computed(() => samplerLine(props.meta?.sampler_pass2))

async function copyText(text, side) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copiedSide.value = side
    setTimeout(() => {
      if (copiedSide.value === side) copiedSide.value = ''
    }, 2000)
  } catch {
    /* ignore */
  }
}
</script>

<template>
  <div
    v-if="meta"
    :class="[
      'space-y-2 text-xs text-muted-foreground',
      compact ? '' : 'rounded-lg border border-border/60 bg-muted/20 p-3',
    ]"
  >
    <p v-if="workflowId">
      <span class="text-foreground/80">工作流</span>
      <span class="ml-1 font-mono">{{ workflowId }}</span>
    </p>
    <p v-if="meta.checkpoint">
      <span class="text-foreground/80">Checkpoint</span>
      <span class="ml-1">{{ meta.checkpoint }}</span>
    </p>
    <div v-if="meta.loras?.length">
      <span class="text-foreground/80">LoRA</span>
      <ul class="mt-1 space-y-0.5">
        <li v-for="l in meta.loras" :key="l.node_id" class="font-mono text-[11px]">
          #{{ l.node_id }} {{ l.short_name || l.lora_name }}
          <span class="text-primary/90">w={{ l.strength_model }}</span>
          <span v-if="l.strength_clip != l.strength_model" class="opacity-70">
            clip={{ l.strength_clip }}
          </span>
        </li>
      </ul>
    </div>
    <div v-if="primarySamplerLine">
      <span class="text-foreground/80">采样器</span>
      <span class="ml-1 font-mono">{{ primarySamplerLine }}</span>
    </div>
    <div v-if="pass2SamplerLine">
      <span class="text-foreground/80">放大采样</span>
      <span class="ml-1 font-mono">{{ pass2SamplerLine }}</span>
    </div>

    <div v-if="posComma" class="space-y-1">
      <div class="flex items-center justify-between gap-2">
        <span class="text-foreground/80">正向提示词（完整，逗号分隔）</span>
        <Button
          variant="outline"
          size="sm"
          class="h-7 shrink-0 gap-1 px-2 text-[10px]"
          @click="copyText(posComma, 'pos')"
        >
          <Check v-if="copiedSide === 'pos'" class="h-3 w-3 text-emerald-500" />
          <Copy v-else class="h-3 w-3" />
          {{ copiedSide === 'pos' ? '已复制' : '复制' }}
        </Button>
      </div>
      <textarea
        readonly
        :value="posComma"
        rows="3"
        class="w-full resize-y rounded-md border border-border bg-background/90 p-2 font-mono text-[11px] leading-relaxed text-foreground select-all"
        @focus="($event.target).select()"
      />
    </div>

    <div v-if="negComma" class="space-y-1">
      <div class="flex items-center justify-between gap-2">
        <span class="text-foreground/80">负向提示词（完整，逗号分隔）</span>
        <Button
          variant="outline"
          size="sm"
          class="h-7 shrink-0 gap-1 px-2 text-[10px]"
          @click="copyText(negComma, 'neg')"
        >
          <Check v-if="copiedSide === 'neg'" class="h-3 w-3 text-emerald-500" />
          <Copy v-else class="h-3 w-3" />
          {{ copiedSide === 'neg' ? '已复制' : '复制' }}
        </Button>
      </div>
      <textarea
        readonly
        :value="negComma"
        rows="2"
        class="w-full resize-y rounded-md border border-border bg-background/90 p-2 font-mono text-[11px] leading-relaxed text-foreground select-all"
        @focus="($event.target).select()"
      />
    </div>

    <div v-if="meta.prompt_positive && meta.prompt_positive !== posComma">
      <button
        type="button"
        class="text-foreground/80 hover:text-foreground transition-colors"
        @click="showPosRaw = !showPosRaw"
      >
        {{ showPosRaw ? '收起' : '展开' }}正向原文（含换行）
      </button>
      <AnimatedCollapse v-model="showPosRaw">
        <pre
          class="mt-1 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-background/80 p-2 text-[11px] leading-relaxed"
          >{{ meta.prompt_positive }}</pre
        >
      </AnimatedCollapse>
    </div>
    <div v-if="meta.prompt_negative && meta.prompt_negative !== negComma">
      <button
        type="button"
        class="text-foreground/80 hover:text-foreground transition-colors"
        @click="showNegRaw = !showNegRaw"
      >
        {{ showNegRaw ? '收起' : '展开' }}负向原文（含换行）
      </button>
      <AnimatedCollapse v-model="showNegRaw">
        <pre
          class="mt-1 max-h-24 overflow-auto whitespace-pre-wrap rounded bg-background/80 p-2 text-[11px] leading-relaxed"
          >{{ meta.prompt_negative }}</pre
        >
      </AnimatedCollapse>
    </div>
  </div>
</template>
