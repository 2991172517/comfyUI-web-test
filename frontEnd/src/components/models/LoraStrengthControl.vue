<script setup>
import Slider from '@/components/ui/Slider.vue'
import Switch from '@/components/ui/Switch.vue'
import Label from '@/components/ui/Label.vue'

const props = defineProps({
  model: { type: Number, default: 1 },
  clip: { type: Number, default: 1 },
  sync: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 2 },
  step: { type: Number, default: 0.05 },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['update:model', 'update:clip', 'update:sync'])

function onModel(v) {
  emit('update:model', v)
  if (props.sync) emit('update:clip', v)
}

function onClip(v) {
  emit('update:clip', v)
}

function onSync(v) {
  emit('update:sync', v)
  if (v) emit('update:clip', props.model)
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between gap-2">
      <Label class="text-xs text-muted-foreground mb-0">同步 model / clip</Label>
      <Switch
        :model-value="sync"
        size="sm"
        aria-label="同步 strength_model 与 strength_clip"
        :disabled="disabled"
        @update:model-value="onSync"
      />
    </div>

    <div :class="compact ? 'space-y-2' : 'space-y-3'">
      <div class="space-y-1.5">
        <Label class="text-xs">strength_model</Label>
        <Slider
          :model-value="model"
          :min="min"
          :max="max"
          :step="step"
          :disabled="disabled"
          @update:model-value="onModel"
        />
      </div>
      <div v-if="!sync" class="space-y-1.5">
        <Label class="text-xs">strength_clip</Label>
        <Slider
          :model-value="clip"
          :min="min"
          :max="max"
          :step="step"
          :disabled="disabled"
          @update:model-value="onClip"
        />
      </div>
    </div>
  </div>
</template>
