<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
  class: { type: String, default: '' },
  /** 列表缩略图用 low，详情区可用 auto */
  fetchPriority: { type: String, default: 'low' },
  eager: { type: Boolean, default: false },
})

const loaded = ref(false)
const failed = ref(false)

watch(
  () => props.src,
  () => {
    loaded.value = false
    failed.value = false
  },
)
</script>

<template>
  <img
    v-if="src && !failed"
    :src="src"
    :alt="alt"
    :class="class"
    :loading="eager ? 'eager' : 'lazy'"
    decoding="async"
    referrerpolicy="no-referrer"
    :fetchpriority="eager ? 'high' : fetchPriority"
    @load="loaded = true"
    @error="failed = true"
  />
  <slot v-else name="fallback" />
</template>
