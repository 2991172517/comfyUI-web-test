<script setup>
import { ref } from 'vue'
import PageAlert from '@/components/layout/PageAlert.vue'
import PromptSettingsPanel from '@/components/prompt/PromptSettingsPanel.vue'

const activeTab = ref('global')
</script>

<template>
  <div class="space-y-4 max-w-4xl mx-auto">
    <PageAlert />
    <PromptSettingsPanel v-model="activeTab" />
  </div>
</template>
