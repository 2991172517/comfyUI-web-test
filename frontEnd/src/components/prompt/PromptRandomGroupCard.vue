<script setup>
import { computed } from 'vue'
import Input from '@/components/ui/Input.vue'
import PromptTextarea from '@/components/prompt/PromptTextarea.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import Switch from '@/components/ui/Switch.vue'
import {
  countCandidates,
  groupModeBadge,
  randomGroupMode,
} from '@/lib/promptTokens.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  group: { type: Object, required: true },
  index: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:group', 'remove'])

const mode = computed(() => randomGroupMode(props.group))
const badgeText = computed(() => groupModeBadge(props.group))

function update(patch) {
  emit('update:group', { ...props.group, ...patch })
}

function updatePrompt(i, val) {
  const prompts = [...(props.group.prompts || [])]
  prompts[i] = val
  update({ prompts })
}

function addCandidate() {
  update({ prompts: [...(props.group.prompts || []), ''] })
}

function removePrompt(i) {
  const prompts = [...(props.group.prompts || [])]
  prompts.splice(i, 1)
  update({ prompts: prompts.length ? prompts : [''] })
}

function switchToPoolMode() {
  const lines = (props.group.prompts || []).map((p) => String(p).trim()).filter(Boolean)
  if (lines.length <= 1) return
  update({ prompts: [lines.join(', ')] })
}
</script>

<template>
  <article
    :class="
      cn(
        'rounded-md border px-3 py-2.5 space-y-2',
        group.enabled ? 'border-primary/35 bg-primary/5' : 'border-border/80 opacity-85',
      )
    "
  >
    <div class="flex items-center gap-2 min-w-0">
      <Switch
        size="sm"
        class="shrink-0"
        :model-value="group.enabled !== false"
        :disabled="disabled"
        :aria-label="`${group.name || '随机组'} 启用`"
        @update:model-value="update({ enabled: $event })"
      />
      <Input
        class="flex-1 min-w-[4rem] h-8 text-sm"
        :model-value="group.name"
        placeholder="组名"
        :disabled="disabled"
        @update:model-value="update({ name: $event })"
      />
      <SelectNative
        class="h-8 text-xs w-[4.5rem] shrink-0"
        :model-value="group.target"
        :disabled="disabled"
        @update:model-value="update({ target: $event })"
      >
        <option value="positive">正向</option>
        <option value="negative">负向</option>
      </SelectNative>
      <Badge variant="outline" class="text-[10px] shrink-0 hidden sm:inline-flex" :title="badgeText">
        {{ badgeText }}
      </Badge>
      <Button
        v-if="countCandidates(group) > 1"
        variant="outline"
        size="sm"
        class="h-8 px-2 text-[10px] shrink-0 hidden md:inline-flex"
        :disabled="disabled"
        title="合并为逗号分隔词条池"
        @click="switchToPoolMode"
      >
        合并池
      </Button>
      <IconDeleteButton
        class="ml-auto"
        :disabled="disabled"
        title="删除组"
        @click="emit('remove')"
      />
    </div>

    <template v-if="mode === 'pool'">
      <PromptTextarea
        :model-value="(group.prompts || [])[0] || ''"
        :rows="4"
        class="text-xs font-mono"
        :disabled="disabled"
        placeholder="词条池，英文或中文逗号分隔"
        @update:model-value="update({ prompts: [$event] })"
      />
    </template>

    <template v-else>
      <div class="space-y-1.5">
        <div
          v-for="(line, i) in group.prompts"
          :key="i"
          class="flex gap-1.5 items-start"
        >
          <span class="text-[10px] text-muted-foreground pt-2 w-8 shrink-0 text-right">{{ i + 1 }}</span>
          <PromptTextarea
            class="flex-1 min-w-0 text-xs font-mono"
            :model-value="line"
            :rows="4"
            :disabled="disabled"
            placeholder="候选方案，逗号分隔多个 tag"
            @update:model-value="updatePrompt(i, $event)"
          />
          <IconDeleteButton
            size="sm"
            :disabled="disabled || (group.prompts || []).length <= 1"
            title="删除方案"
            @click="removePrompt(i)"
          />
        </div>
        <Button variant="ghost" size="sm" class="h-7 text-xs" :disabled="disabled" @click="addCandidate">
          + 方案
        </Button>
      </div>
    </template>
  </article>
</template>
