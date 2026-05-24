<script setup>
import { RouterView, useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <RouterView v-slot="{ Component }">
    <Transition name="route-view">
      <div :key="route.fullPath" class="route-motion-shell">
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
