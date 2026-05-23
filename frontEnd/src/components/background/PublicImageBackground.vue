<script setup>
defineProps({
  /** public 目录下的路径，如 /bg-images/xxx.png */
  src: { type: String, default: '/bg-images/coolbackgrounds-fractalize-spectrum.png' },
  /** 固定全屏背景 */
  fixed: { type: Boolean, default: true },
  /** 半透明遮罩，保证前景可读 */
  overlay: { type: Boolean, default: true },
  overlayClass: { type: String, default: 'bg-black/40' },
})
</script>

<template>
  <div
    class="public-image-background"
    :class="fixed ? 'fixed inset-0' : 'relative min-h-full w-full'"
  >
    <div class="pointer-events-none absolute inset-0 z-0 overflow-hidden" aria-hidden="true">
      <img
        :src="src"
        alt=""
        class="h-full w-full object-cover object-center"
        decoding="async"
        fetchpriority="high"
      />
      <div v-if="overlay" class="absolute inset-0" :class="overlayClass" />
    </div>
    <div class="relative z-10 min-h-full">
      <slot />
    </div>
  </div>
</template>
