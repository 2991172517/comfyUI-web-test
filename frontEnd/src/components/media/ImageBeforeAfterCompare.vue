<script setup>
import { computed, ref } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  beforeSrc: { type: String, default: '' },
  afterSrc: { type: String, default: '' },
  beforeLabel: { type: String, default: '重绘前' },
  afterLabel: { type: String, default: '重绘后' },
  class: { type: String, default: '' },
})

const split = ref(50)

const ready = computed(() => !!props.beforeSrc && !!props.afterSrc)
const clipStyle = computed(() => ({
  clipPath: `inset(0 ${100 - split.value}% 0 0)`,
}))
</script>

<template>
  <div
    v-if="ready"
    :class="cn('space-y-2', props.class)"
  >
    <div
      class="relative mx-auto w-full overflow-hidden rounded-lg border border-border bg-muted/20"
    >
      <img
        :src="afterSrc"
        alt="after"
        class="block h-auto w-full max-h-[min(70vh,720px)] object-contain"
        draggable="false"
      />
      <img
        :src="beforeSrc"
        alt="before"
        class="absolute inset-0 block h-full w-full max-h-[min(70vh,720px)] object-contain pointer-events-none"
        :style="clipStyle"
        draggable="false"
      />
      <div
        class="absolute inset-y-0 w-0.5 -translate-x-1/2 bg-primary shadow-md pointer-events-none"
        :style="{ left: `${split}%` }"
      />
      <div
        class="absolute top-2 left-2 rounded bg-background/85 px-2 py-0.5 text-[10px] font-medium"
      >
        {{ beforeLabel }}
      </div>
      <div
        class="absolute top-2 right-2 rounded bg-background/85 px-2 py-0.5 text-[10px] font-medium"
      >
        {{ afterLabel }}
      </div>
    </div>
    <div class="flex items-center gap-3 px-1">
      <span class="text-[10px] text-muted-foreground shrink-0">{{ beforeLabel }}</span>
      <input
        v-model.number="split"
        type="range"
        min="0"
        max="100"
        step="1"
        class="flex-1 accent-primary"
        aria-label="拖动对比重绘前后"
      />
      <span class="text-[10px] text-muted-foreground shrink-0">{{ afterLabel }}</span>
    </div>
  </div>
</template>
