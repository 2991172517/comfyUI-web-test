<script setup>
import { nextTick, ref, watch } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import Alert from '@/components/ui/Alert.vue'
import { gsap, prefersReducedMotion, shakeEl } from '@/lib/gsap/motion.js'

const store = useAppStore()
const wrapRef = ref(null)

watch(
  () => store.message,
  async (msg) => {
    if (!msg) return
    await nextTick()
    const el = wrapRef.value
    if (!el || prefersReducedMotion()) return
    gsap.fromTo(
      el,
      { opacity: 0, y: -12 },
      { opacity: 1, y: 0, duration: 0.32, ease: 'power2.out' },
    )
    if (store.error) shakeEl(el)
  },
)
</script>

<template>
  <div v-if="store.message" ref="wrapRef">
    <Alert :variant="store.error ? 'destructive' : 'default'" class="mb-4">
      {{ store.message }}
    </Alert>
  </div>
</template>
