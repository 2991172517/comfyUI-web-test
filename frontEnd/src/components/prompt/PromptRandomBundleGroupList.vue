<script setup>
import Button from '@/components/ui/Button.vue'
import PromptRandomBundleGroupCard from '@/components/prompt/PromptRandomBundleGroupCard.vue'
import { newRandomBundleGroup } from '@/composables/usePromptConfig.js'

const props = defineProps({
  groups: { type: Array, required: true },
  disabled: { type: Boolean, default: false },
  addLabel: { type: String, default: '+ 新建随机词串组' },
  gachaPreview: { type: Boolean, default: false },
})

const emit = defineEmits(['update:groups'])

function updateAt(i, g) {
  const next = [...props.groups]
  next[i] = g
  emit('update:groups', next)
}

function removeAt(i) {
  const next = [...props.groups]
  next.splice(i, 1)
  emit('update:groups', next)
}

function addGroup() {
  emit('update:groups', [...props.groups, newRandomBundleGroup()])
}
</script>

<template>
  <div class="space-y-3">
    <Button class="w-full h-10 text-sm font-medium" :disabled="disabled" @click="addGroup">
      {{ addLabel }}
    </Button>
    <p v-if="!groups.length" class="text-xs text-muted-foreground text-center py-2">
      暂无词串组
    </p>
    <PromptRandomBundleGroupCard
      v-for="(g, i) in groups"
      :key="g.id"
      :group="g"
      :disabled="disabled"
      :gacha-preview="gachaPreview"
      @update:group="updateAt(i, $event)"
      @remove="removeAt(i)"
    />
  </div>
</template>
