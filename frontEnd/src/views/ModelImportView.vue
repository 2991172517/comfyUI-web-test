<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { openModelImportModal } from '@/composables/useModelImportModal.js'

const router = useRouter()

onMounted(() => {
  openModelImportModal()
  router.replace('/generate')
})
</script>

<template>
  <p class="text-sm text-muted-foreground">正在打开模型下载…</p>
</template>
