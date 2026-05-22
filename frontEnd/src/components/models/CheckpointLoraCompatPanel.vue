<script setup>
import { computed, ref } from 'vue'
import { Settings2 } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import CheckpointLoraCompatModal from '@/components/models/CheckpointLoraCompatModal.vue'

const props = defineProps({
  checkpointName: { type: String, required: true },
  allLoras: { type: Array, default: () => [] },
  loraCatalog: { type: Array, default: () => [] },
  recommended: { type: Array, default: () => [] },
  notRecommended: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:recommended', 'update:notRecommended', 'saved'])

const modalOpen = ref(false)

const hasAny = computed(
  () => (props.recommended?.length || 0) + (props.notRecommended?.length || 0) > 0,
)
</script>

<template>
  <div
    class="rounded-lg border border-dashed border-border/80 bg-muted/10 px-3 py-2.5 flex flex-wrap items-center gap-2"
  >
    <div class="flex flex-wrap items-center gap-1.5 min-w-0 flex-1">
      <Badge
        v-if="recommended.length"
        variant="outline"
        class="text-[10px] text-emerald-600 border-emerald-500/40"
      >
        推荐 {{ recommended.length }}
      </Badge>
      <Badge
        v-if="notRecommended.length"
        variant="outline"
        class="text-[10px] text-amber-600 border-amber-500/40"
      >
        不推荐 {{ notRecommended.length }}
      </Badge>
      <span v-if="!hasAny" class="text-[10px] text-muted-foreground">未配置 LoRA 适配</span>
    </div>
    <Button
      variant="outline"
      size="sm"
      class="h-8 gap-1.5 shrink-0 text-xs"
      :disabled="!allLoras.length"
      @click="modalOpen = true"
    >
      <Settings2 class="h-3.5 w-3.5" />
      配置 LoRA 适配
    </Button>

    <CheckpointLoraCompatModal
      v-model:open="modalOpen"
      :checkpoint-name="checkpointName"
      :all-loras="allLoras"
      :lora-catalog="loraCatalog"
      :recommended="recommended"
      :not-recommended="notRecommended"
      @update:recommended="emit('update:recommended', $event)"
      @update:not-recommended="emit('update:notRecommended', $event)"
      @saved="emit('saved')"
    />
  </div>
</template>
