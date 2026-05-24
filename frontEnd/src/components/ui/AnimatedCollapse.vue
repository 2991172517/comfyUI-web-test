<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { expandIn, expandOut } from '@/lib/gsap/expand.js'

const open = defineModel({ type: Boolean, default: false })

const bodyRef = ref(null)
const shown = ref(open.value)
const ready = ref(false)

async function apply(openNow) {
  await nextTick()
  const el = bodyRef.value
  if (!el) {
    shown.value = openNow
    return
  }
  if (openNow) {
    shown.value = true
    await nextTick()
    await expandIn(el)
  } else {
    await expandOut(el)
    shown.value = false
  }
}

watch(open, (v) => {
  if (!ready.value) {
    shown.value = v
    return
  }
  apply(v)
})

onMounted(() => {
  if (open.value) {
    shown.value = true
    nextTick(() => {
      if (bodyRef.value) {
        expandIn(bodyRef.value)
      }
      ready.value = true
    })
  } else {
    ready.value = true
  }
})
</script>

<template>
  <div v-show="shown" ref="bodyRef" class="overflow-hidden">
    <slot />
  </div>
</template>
