<script setup>
import { computed } from 'vue'
import { normalizePreviewMedia } from '@/lib/modelPreviewMedia.js'
import LazyImage from '@/components/ui/LazyImage.vue'

const props = defineProps({
  source: { type: [String, Object], default: null },
  class: { type: String, default: 'max-h-40 rounded-md border object-contain' },
  videoClass: { type: String, default: 'max-h-40 w-full rounded-md border bg-black' },
  /** 详情侧栏等首屏预览可设为 true */
  eager: { type: Boolean, default: false },
})

const media = computed(() => normalizePreviewMedia(props.source))
</script>

<template>
  <video
    v-if="media.url && media.isVideo"
    :src="media.url"
    :class="videoClass"
    controls
    muted
    loop
    playsinline
    preload="metadata"
  />
  <LazyImage
    v-else-if="media.url"
    :src="media.url"
    :class="class"
    :eager="eager"
  />
</template>
