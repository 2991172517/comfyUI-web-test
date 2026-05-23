<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  editing: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  editLocked: { type: Boolean, default: false },
  placeholder: { type: String, default: '点击编辑' },
  mono: { type: Boolean, default: false },
  class: { type: String, default: '' },
})

const draft = defineModel({ type: String, default: '' })
const inputRef = ref(null)

const typography = computed(() => [
  props.mono
    ? 'font-mono text-xs text-foreground/90'
    : 'text-sm font-medium text-foreground',
  'px-1 text-center leading-snug',
])

const displayText = computed(() => props.text || props.placeholder)
const isEmpty = computed(() => !props.text && !props.editing)
const sizeText = computed(() => (props.editing ? draft.value : props.text) || props.placeholder || '\u00a0')

defineExpose({
  focus: () => {
    const el = inputRef.value
    if (!el) return
    el.focus()
    el.select()
  },
})

const emit = defineEmits(['click', 'commit', 'cancel', 'dblclick'])

function onButtonClick(event) {
  if (props.disabled || props.editLocked) return
  emit('click', event)
}

function onButtonDblClick(event) {
  if (props.disabled) return
  emit('dblclick', event)
}
</script>

<template>
  <span
    class="relative inline-block max-w-full min-w-0"
    :class="props.class"
  >
    <span
      class="invisible inline-block max-w-full whitespace-pre px-1 text-center leading-snug"
      :class="mono ? 'font-mono text-xs' : 'text-sm font-medium'"
      aria-hidden="true"
    >{{ sizeText }}</span>

    <button
      v-if="!editing"
      type="button"
      class="absolute inset-0 w-full rounded hover:bg-muted/40 disabled:cursor-not-allowed"
      :class="[
        typography,
        isEmpty ? 'text-muted-foreground/60 italic' : '',
        editLocked ? 'cursor-default hover:bg-transparent' : 'cursor-text',
      ]"
      :disabled="disabled"
      @click.stop="onButtonClick"
      @dblclick.stop="onButtonDblClick"
    >
      {{ displayText }}
    </button>

    <input
      v-else
      ref="inputRef"
      v-model="draft"
      type="text"
      class="absolute inset-0 w-full min-w-0 border-0 bg-transparent p-0 px-1 text-center leading-snug outline-none caret-foreground selection:bg-primary/20"
      :class="typography"
      @click.stop
      @mousedown.stop
      @blur="emit('commit')"
      @keydown.enter.prevent="emit('commit')"
      @keydown.escape.prevent="emit('cancel')"
    />
  </span>
</template>
