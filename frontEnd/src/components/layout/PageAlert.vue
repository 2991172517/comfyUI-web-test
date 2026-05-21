<script setup>
import { useAppStore } from '@/stores/useAppStore.js'
import Alert from '@/components/ui/Alert.vue'

const store = useAppStore()
</script>

<template>
  <Alert
    v-if="store.message"
    :variant="store.error ? 'destructive' : 'default'"
    class="mb-4"
  >
    {{ store.message }}
  </Alert>
</template>
