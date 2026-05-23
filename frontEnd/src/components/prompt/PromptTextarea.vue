<script setup>
import { computed, ref, nextTick, toRef } from 'vue'
import { cn } from '@/lib/utils'
import { PROMPT_FORMAT_HINT, validateComfyPromptText } from '@/lib/promptFormatValidate.js'
import { applyDotWeightWrap } from '@/lib/promptTokenAtCursor.js'
import { splitPromptTokens, dedupePromptText } from '@/lib/promptDisplay.js'
import { lookupKeyForVocabulary } from '@/lib/promptTagWeight.js'
import { usePromptAutocomplete } from '@/composables/usePromptAutocomplete.js'
import { usePromptEditorMode } from '@/composables/usePromptEditorMode.js'
import PromptAutocompleteDropdown from '@/components/prompt/PromptAutocompleteDropdown.vue'
import PromptTagEditor from '@/components/prompt/PromptTagEditor.vue'

const model = defineModel({ type: String, default: '' })

const props = defineProps({
  rows: { type: Number, default: 6 },
  disabled: { type: Boolean, default: false },
  class: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  validate: { type: Boolean, default: true },
  autocomplete: { type: Boolean, default: true },
  /** 覆盖全局编辑器模式；不传则读全局设置 */
  editorMode: { type: String, default: '' },
})

const { mode: globalMode } = usePromptEditorMode()

const effectiveMode = computed(() => {
  const m = props.editorMode || globalMode.value
  if (m === 'plain' || m === 'tags' || m === 'autocomplete') return m
  return 'autocomplete'
})

const useAutocomplete = computed(
  () => effectiveMode.value === 'autocomplete' && props.autocomplete,
)

const textareaRef = ref(null)
const touched = ref(false)
const issues = ref([])

const {
  open: acOpen,
  loading: acLoading,
  items: acItems,
  selectedIndex: acSelectedIndex,
  position: acPosition,
  close: acClose,
  scheduleSuggest,
  selectItem,
  onKeydown: acOnKeydown,
} = usePromptAutocomplete(textareaRef, {
  enabled: toRef(() => useAutocomplete.value),
})

function runValidate() {
  if (!props.validate) {
    issues.value = []
    return
  }
  issues.value = validateComfyPromptText(model.value).issues
}

function onBlur() {
  if (props.validate) {
    touched.value = true
    runValidate()
  }
  if (effectiveMode.value !== 'tags') {
    const { text, removed } = dedupePromptText(model.value)
    if (removed > 0) model.value = text
  }
  setTimeout(() => acClose(), 200)
}

function tokenExistsInText(text, token) {
  const key = lookupKeyForVocabulary(token).toLowerCase()
  if (!key) return false
  return splitPromptTokens(text).some(
    (part) => lookupKeyForVocabulary(part).toLowerCase() === key,
  )
}

function onInput() {
  if (touched.value) runValidate()
  if (useAutocomplete.value) scheduleSuggest()
}

function onKeydown(event) {
  if (useAutocomplete.value && acOnKeydown(event)) return

  if (
    (event.key === ',' || event.key === '，')
    && effectiveMode.value !== 'tags'
  ) {
    const el = textareaRef.value
    if (el && !props.disabled) {
      const cursor = el.selectionStart ?? 0
      const left = el.value.slice(0, cursor)
      const m = left.match(/([^,，]+)$/)
      const token = (m ? m[1] : '').trim()
      const prior = left.slice(0, left.length - (m ? m[1].length : 0))
      if (token && tokenExistsInText(prior, token)) {
        event.preventDefault()
        return
      }
    }
  }

  if (event.key === '.' && !event.ctrlKey && !event.metaKey && !event.altKey) {
    const el = textareaRef.value
    if (!el || props.disabled) return
    const cursor = el.selectionStart ?? 0
    if (cursor !== el.selectionEnd) return
    const result = applyDotWeightWrap(el.value, cursor)
    if (result) {
      event.preventDefault()
      event.stopPropagation()
      acClose()
      const { newText, newCursor } = result
      model.value = newText
      nextTick(() => {
        const target = textareaRef.value
        if (!target) return
        target.focus()
        try {
          target.setSelectionRange(newCursor, newCursor)
        } catch {
          /* ignore if element detached */
        }
      })
      if (touched.value) runValidate()
    }
  }
}

function onAutocompleteSelect(index) {
  const t = selectItem(index)
  if (t != null) model.value = t
}

const invalid = computed(() => props.validate && touched.value && issues.value.length > 0)
const hint = computed(() => issues.value.join('；'))
</script>

<template>
  <div class="space-y-1">
    <PromptTagEditor
      v-if="effectiveMode === 'tags'"
      v-model="model"
      :disabled="disabled"
      :class="props.class"
    />

    <template v-else>
      <textarea
        ref="textareaRef"
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
        @keydown="onKeydown"
      />
      <PromptAutocompleteDropdown
        v-if="useAutocomplete"
        :open="acOpen"
        :loading="acLoading"
        :items="acItems"
        :selected-index="acSelectedIndex"
        :position="acPosition"
        @select="onAutocompleteSelect"
        @close="acClose"
      />
    </template>

    <p v-if="invalid" class="text-[11px] text-destructive leading-snug">
      {{ hint }}。{{ PROMPT_FORMAT_HINT }}
    </p>
  </div>
</template>
