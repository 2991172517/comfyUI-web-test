<script setup>
import { computed, ref } from 'vue'
import { cn } from '@/lib/utils'
import { PROMPT_FORMAT_HINT, validateComfyPromptText } from '@/lib/promptFormatValidate.js'

const model = defineModel({ type: String, default: '' })

const props = defineProps({
  rows: { type: Number, default: 6 },
  disabled: { type: Boolean, default: false },
  class: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  /** 关闭校验（非 CLIP 文本字段） */
  validate: { type: Boolean, default: true },
})

const touched = ref(false)
const issues = ref([])

function runValidate() {
  if (!props.validate) {
    issues.value = []
    return
  }
  issues.value = validateComfyPromptText(model.value).issues
}

function onBlur() {
  if (!props.validate) return
  touched.value = true
  runValidate()
}

function onInput() {
  if (touched.value) runValidate()
}

const invalid = computed(() => props.validate && touched.value && issues.value.length > 0)
const hint = computed(() => issues.value.join('；'))
</script>

<template>
  <div class="space-y-1">
    <textarea
      v-model="model"
      :rows="props.rows"
      :disabled="disabled"
      :placeholder="placeholder"
      :class="
        cn(
          'flex min-h-[8.5rem] w-full rounded-md border bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50',
          invalid
            ? 'border-destructive ring-destructive/30 focus-visible:ring-destructive/40'
            : 'border-input focus-visible:ring-ring',
          props.class,
        )
      "
      @blur="onBlur"
      @input="onInput"
    />
    <p v-if="invalid" class="text-[11px] text-destructive leading-snug">
      {{ hint }}。{{ PROMPT_FORMAT_HINT }}
    </p>
  </div>
</template>
