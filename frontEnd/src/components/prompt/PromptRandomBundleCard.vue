<script setup>
import Input from '@/components/ui/Input.vue'
import PromptTextarea from '@/components/prompt/PromptTextarea.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'

const props = defineProps({
  bundle: { type: Object, required: true },
  index: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
  showWeight: { type: Boolean, default: false },
  weight: { type: Number, default: 1 },
})

const emit = defineEmits(['update:bundle', 'remove', 'update-weight'])

function update(patch) {
  emit('update:bundle', { ...props.bundle, ...patch })
}
</script>

<template>
  <div
    class="grid gap-2 rounded border border-border/60 bg-background/40 p-2 sm:grid-cols-[7rem_1fr_auto] sm:items-start"
  >
    <div class="space-y-0.5">
      <label class="text-[10px] text-muted-foreground">别名</label>
      <Input
        class="h-8 text-xs"
        :model-value="bundle.alias"
        placeholder="如：室内暖光"
        :disabled="disabled"
        @update:model-value="update({ alias: $event })"
      />
    </div>
    <div class="space-y-0.5 min-w-0">
      <label class="text-[10px] text-muted-foreground">词条（逗号分隔，整组加入）</label>
      <PromptTextarea
        class="text-xs font-mono"
        :model-value="bundle.text"
        :rows="3"
        :disabled="disabled"
        placeholder="soft lighting, warm tone, ..."
        @update:model-value="update({ text: $event })"
      />
    </div>
    <div class="flex sm:flex-col items-center gap-1 sm:pt-5">
      <div v-if="showWeight" class="flex items-center gap-1">
        <span class="text-[10px] text-muted-foreground">权重</span>
        <Input
          type="number"
          min="0"
          step="0.1"
          class="h-7 w-14 text-xs text-center"
          :model-value="weight"
          :disabled="disabled"
          @update:model-value="emit('update-weight', $event)"
        />
      </div>
      <IconDeleteButton
        size="sm"
        :disabled="disabled"
        title="删除词条"
        @click="emit('remove')"
      />
    </div>
  </div>
</template>
