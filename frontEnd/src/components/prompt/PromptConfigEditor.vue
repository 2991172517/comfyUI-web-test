<script setup>
import PromptFixedFields from '@/components/prompt/PromptFixedFields.vue'
import PromptRandomGroupList from '@/components/prompt/PromptRandomGroupList.vue'

defineProps({
  fixed: { type: Object, required: true },
  randomGroups: { type: Array, required: true },
  disabled: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  showFixed: { type: Boolean, default: true },
  showRandom: { type: Boolean, default: true },
})

const emit = defineEmits(['update:randomGroups', 'update:fixed'])
</script>

<template>
  <div :class="compact ? 'space-y-3' : 'space-y-6'">
    <div v-if="showFixed">
      <p :class="compact ? 'text-xs font-medium mb-1.5' : 'text-sm font-medium mb-2'">固定追加</p>
      <PromptFixedFields
        :model-value="fixed"
        :disabled="disabled"
        :compact="compact"
        @update:model-value="emit('update:fixed', $event)"
      />
    </div>
    <div v-if="showRandom">
      <p :class="compact ? 'text-xs font-medium mb-1.5' : 'text-sm font-medium mb-2'">随机组</p>
      <PromptRandomGroupList
        :groups="randomGroups"
        :disabled="disabled"
        @update:groups="emit('update:randomGroups', $event)"
      />
    </div>
  </div>
</template>
