<script setup>
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'

const route = useRoute()

/** 同一路由仅 query 变化时不销毁页面（如局部重绘 bootstrap、生成页 restore） */
const routeMotionKey = computed(() => route.name || route.path)
</script>

<template>
  <RouterView v-slot="{ Component }">
    <Transition name="route-view">
      <div :key="routeMotionKey" class="route-motion-shell">
        <component :is="Component" />
      </div>
    </Transition>
  </RouterView>
</template>

<style>
.route-motion-shell {
  width: 100%;
}

.route-view-enter-active {
  transition: opacity 0.18s ease-out;
}

.route-view-enter-from {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .route-view-enter-active {
    transition: none !important;
  }
}
</style>
