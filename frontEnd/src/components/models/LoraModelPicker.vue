<script setup>
import ModelVisualPicker from '@/components/models/ModelVisualPicker.vue'

defineOptions({ inheritAttrs: false })
</script>

<template>
  <ModelVisualPicker folder="loras" v-bind="$attrs" />
</template>
