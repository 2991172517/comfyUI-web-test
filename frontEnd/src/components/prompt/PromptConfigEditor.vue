<script setup>
import PromptRandomGroupList from '@/components/prompt/PromptRandomGroupList.vue'
import PromptRandomBundleGroupList from '@/components/prompt/PromptRandomBundleGroupList.vue'

defineProps({
  randomGroups: { type: Array, required: true },
  randomBundleGroups: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  showRandom: { type: Boolean, default: true },
  showBundles: { type: Boolean, default: true },
})

const emit = defineEmits(['update:randomGroups', 'update:randomBundleGroups'])
</script>

<template>
  <div :class="compact ? 'space-y-3' : 'space-y-6'">
    <div v-if="showRandom">
      <p :class="compact ? 'text-xs font-medium mb-1.5' : 'text-sm font-medium mb-2'">
        随机词组 <span class="font-normal text-muted-foreground">（每次抽 1 个 tag）</span>
      </p>
      <PromptRandomGroupList
        :groups="randomGroups"
        :disabled="disabled"
        @update:groups="emit('update:randomGroups', $event)"
      />
    </div>
    <div v-if="showBundles">
      <p :class="compact ? 'text-xs font-medium mb-1.5' : 'text-sm font-medium mb-2'">
        随机词串组 <span class="font-normal text-muted-foreground">（每次抽 1 整组）</span>
      </p>
      <PromptRandomBundleGroupList
        :groups="randomBundleGroups"
        :disabled="disabled"
        @update:groups="emit('update:randomBundleGroups', $event)"
      />
    </div>
  </div>
</template>
