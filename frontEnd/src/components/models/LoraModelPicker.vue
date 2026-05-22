<script setup>
import ModelVisualPicker from '@/components/models/ModelVisualPicker.vue'

defineProps({
  loraCompatMap: { type: Object, default: null },
})

defineOptions({ inheritAttrs: false })
</script>

<template>
  <ModelVisualPicker folder="loras" :lora-compat-map="loraCompatMap" v-bind="$attrs" />
</template>
