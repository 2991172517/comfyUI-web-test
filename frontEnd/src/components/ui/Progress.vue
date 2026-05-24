<script setup>
import { onMounted, ref, watch } from 'vue'
import { cn } from '@/lib/utils'
import { tweenWidthPercent } from '@/lib/gsap/motion.js'

const props = defineProps({
  value: { type: Number, default: 0 },
  class: { type: String, default: '' },
})

const barRef = ref(null)

function applyWidth(v) {
  tweenWidthPercent(barRef.value, v)
}

onMounted(() => applyWidth(props.value))
watch(() => props.value, applyWidth)
</script>

<template>
  <div
    role="progressbar"
    :aria-valuenow="value"
    :class="cn('relative h-2 w-full overflow-hidden rounded-full bg-secondary', $props.class)"
  >
    <div ref="barRef" class="h-full bg-primary" style="width: 0%" />
  </div>
</template>
