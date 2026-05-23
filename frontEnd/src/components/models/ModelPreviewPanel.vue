<script setup>
import { computed, ref } from 'vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import LazyImage from '@/components/ui/LazyImage.vue'
import { cn } from '@/lib/utils'
import { ChevronLeft, ChevronRight, ImageOff, ZoomIn } from 'lucide-vue-next'

const props = defineProps({
  folder: { type: String, default: '' },
  modelName: { type: String, default: '' },
  previews: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  index: { type: Number, default: 0 },
  size: { type: String, default: 'md' },
})

const emit = defineEmits(['update:index'])

const currentIndex = computed({
  get: () => props.index,
  set: (v) => emit('update:index', v),
})

const lightboxRef = ref(null)

function openZoom() {
  const list = props.previews.map((p) => ({
    url: p.url,
    title: props.modelName,
  }))
  if (!list.length) return
  lightboxRef.value?.open(list, currentIndex.value)
}

function prev() {
  const n = props.previews.length
  if (n) currentIndex.value = (currentIndex.value - 1 + n) % n
}

function next() {
  const n = props.previews.length
  if (n) currentIndex.value = (currentIndex.value + 1) % n
}

const sizeClass = {
  sm: 'h-28',
  md: 'h-40',
  lg: 'h-56',
}
</script>

<template>
  <div
    :class="
      cn(
        'relative overflow-hidden rounded-lg border border-border bg-muted/30',
        sizeClass[size] || sizeClass.md,
      )
    "
  >
    <template v-if="loading">
      <div class="flex h-full items-center justify-center text-xs text-muted-foreground">
        加载预览…
      </div>
    </template>
    <template v-else-if="previews.length">
      <div class="h-full w-full cursor-zoom-in" @click="openZoom">
        <LazyImage
          :src="previews[currentIndex].url"
          :alt="modelName"
          class="h-full w-full object-contain bg-black/20"
          fetch-priority="low"
        />
      </div>
      <Button
        v-if="previews.length > 1"
        variant="secondary"
        size="icon"
        class="absolute left-1 top-1/2 h-7 w-7 -translate-y-1/2 opacity-90"
        @click="prev"
      >
        <ChevronLeft class="h-4 w-4" />
      </Button>
      <Button
        v-if="previews.length > 1"
        variant="secondary"
        size="icon"
        class="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 opacity-90"
        @click="next"
      >
        <ChevronRight class="h-4 w-4" />
      </Button>
      <div class="absolute bottom-1 left-1 right-1 flex items-center justify-between gap-1 pointer-events-none">
        <Badge v-if="previews.length > 1" variant="secondary" class="text-[10px] pointer-events-auto">
          {{ currentIndex + 1 }} / {{ previews.length }}
        </Badge>
        <span v-else class="text-[10px] text-muted-foreground/80 truncate max-w-[60%]">
          {{ previews[currentIndex].filename }}
        </span>
        <Button
          variant="secondary"
          size="icon"
          class="h-6 w-6 pointer-events-auto ml-auto"
          title="放大"
          @click="openZoom"
        >
          <ZoomIn class="h-3.5 w-3.5" />
        </Button>
      </div>
    </template>
    <template v-else>
      <div
        class="flex h-full flex-col items-center justify-center gap-1 px-3 text-center text-xs text-muted-foreground"
      >
        <ImageOff class="h-6 w-6 opacity-40" />
        <span>暂无参考图</span>
        <span class="text-[10px] opacity-80 leading-snug">
          在 models/{{ folder || '…' }}/ 下放置与模型同名的文件夹，内含 png/jpg 等图片
        </span>
      </div>
    </template>
    <ImageLightbox ref="lightboxRef" />
  </div>
</template>
