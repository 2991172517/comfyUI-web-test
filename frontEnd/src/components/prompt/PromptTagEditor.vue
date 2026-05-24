<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { collapseOut, popIn } from '@/lib/gsap/motion.js'
import { api } from '@/api/client.js'
import { cn } from '@/lib/utils'
import { splitPromptTokens } from '@/lib/promptDisplay.js'
import { Copy, Check } from 'lucide-vue-next'
import {
  adjustWeight,
  canAdjustWeight,
  formatTagValue,
  getTagWeight,
  isDefaultWeight,
  lookupKeyForVocabulary,
  parseTagWeight,
  tagValueReservedText,
  weightActiveLineStyle,
  weightBlueZoneStyle,
  weightRedZoneStyle,
  WEIGHT_EPS,
} from '@/lib/promptTagWeight.js'
import {
  encodeMutedStoredToken,
  parseStoredPromptToken,
} from '@/lib/promptMutedTag.js'
import {
  clearVocabularyResolveCache,
  resolveLabelForValue,
  resolveVocabularyValues,
  resolvedItemToTag,
} from '@/lib/vocabularyResolve.js'
import { usePromptAutocomplete } from '@/composables/usePromptAutocomplete.js'
import PromptAutocompleteDropdown from '@/components/prompt/PromptAutocompleteDropdown.vue'
import PromptTagTextField from '@/components/prompt/PromptTagTextField.vue'

const model = defineModel({ type: String, default: '' })

const props = defineProps({
  disabled: { type: Boolean, default: false },
  class: { type: String, default: '' },
  /** positive | negative — 用于生成吸入动画区分栏位 */
  promptSide: { type: String, default: '' },
})

const tags = ref([])
const draft = ref('')
const inputRef = ref(null)
const editorRootRef = ref(null)
const activeTagId = ref(null)
const resolving = ref(false)
const editing = ref({ tagId: null, field: null })
const editDraft = ref('')
const editFieldRef = ref(null)
const undoStack = ref([])
let editClickTimer = null
let syncing = false
let undoing = false

const MAX_UNDO = 50
const copyOk = ref(false)
let copyTimer
let emitTimer = null
const EMIT_DEBOUNCE_MS = 350

const {
  open: acOpen,
  loading: acLoading,
  items: acItems,
  selectedIndex: acSelectedIndex,
  position: acPosition,
  close: acClose,
  scheduleSuggest,
  onKeydown: acOnKeydown,
} = usePromptAutocomplete(inputRef, {
  enabled: true,
  onSelect: (item) => {
    commitTag(item.insertText || item.insert_text || '')
  },
})

function cloneTags(list) {
  return (list || []).map((t) => ({ ...t }))
}

function pushUndo() {
  if (syncing || undoing) return
  undoStack.value.push(cloneTags(tags.value))
  if (undoStack.value.length > MAX_UNDO) undoStack.value.shift()
}

function undoTags() {
  if (props.disabled || undoing || !undoStack.value.length) return false
  undoing = true
  cancelEdit()
  tags.value = cloneTags(undoStack.value.pop())
  undoing = false
  flushEmitUpdate()
  return true
}

function clearUndo() {
  undoStack.value = []
}

function isEditorFocused() {
  const root = editorRootRef.value
  if (!root) return false
  const active = document.activeElement
  return active === root || root.contains(active)
}

function onWindowKeydown(event) {
  if (props.disabled || !isEditorFocused()) return
  const key = event.key.toLowerCase()
  const mod = event.ctrlKey || event.metaKey
  if (!mod || key !== 'z' || event.shiftKey) return
  if (editing.value.tagId) return
  if (document.activeElement === inputRef.value) return
  event.preventDefault()
  undoTags()
}

function deactivateTagSelection() {
  activeTagId.value = null
  cancelEdit()
}

function onDocumentPointerDown(event) {
  if (!activeTagId.value && !editing.value.tagId) return
  const target = event.target
  if (target?.closest?.('[data-tag-chip]')) return
  if (target?.closest?.('[data-prompt-autocomplete]')) return
  deactivateTagSelection()
}

onMounted(() => {
  window.addEventListener('keydown', onWindowKeydown)
  document.addEventListener('mousedown', onDocumentPointerDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onWindowKeydown)
  document.removeEventListener('mousedown', onDocumentPointerDown)
  flushEmitUpdate()
})

function serialize() {
  return tags.value
    .map((t) => {
      const v = String(t.value || '').trim()
      if (!v) return null
      return t.muted ? encodeMutedStoredToken(v) : v
    })
    .filter(Boolean)
    .join(', ')
}

function modelMatchesTags(text) {
  const parts = splitPromptTokens(text || '').map(parseStoredPromptToken)
  if (parts.length !== tags.value.length) return false
  return parts.every((part, i) => {
    const tag = tags.value[i]
    if (!tag) return false
    const sameBase =
      lookupKeyForVocabulary(part.value).toLowerCase()
      === lookupKeyForVocabulary(tag.value).toLowerCase()
    const sameMuted = !!part.muted === !!tag.muted
    const sameWeight =
      Math.abs(getTagWeight(part.value) - getTagWeight(tag.value)) < WEIGHT_EPS
    return sameBase && sameMuted && sameWeight
  })
}

function patchTag(id, patch) {
  const i = tags.value.findIndex((t) => t.id === id)
  if (i < 0) return
  const next = { ...tags.value[i], ...patch }
  if (patch.value != null) {
    next.weight = getTagWeight(next.value)
  }
  tags.value.splice(i, 1, next)
}

function tagDedupeKey(value) {
  return lookupKeyForVocabulary(String(value || '').trim()).toLowerCase()
}

function findDuplicateTag(rawValue) {
  const key = tagDedupeKey(rawValue)
  if (!key) return null
  return tags.value.find((t) => tagDedupeKey(t.value) === key) ?? null
}

function focusDraftInput() {
  void nextTick(() => {
    requestAnimationFrame(() => {
      inputRef.value?.focus()
    })
  })
}

function hasChineseLabel(tag) {
  return !!String(tag.label || '').trim()
}

function isEditing(tagId, field) {
  return editing.value.tagId === tagId && editing.value.field === field
}

function displayLabel(tag) {
  return String(tag.label || '').trim()
}

function applyValueWithWeight(oldValue, newBase) {
  const { weight } = parseTagWeight(oldValue)
  return formatTagValue(String(newBase || '').trim(), weight)
}

async function lookupByChineseLabel(label) {
  const q = String(label || '').trim()
  if (!q) return null
  const res = await api.vocabularySuggest(q, { limit: 40 })
  const items = res.items || []
  const exact = items.find((i) => i.label === q)
  if (exact) return exact
  return items.find((i) => String(i.label || '').toLowerCase() === q.toLowerCase()) || null
}

function cancelEdit() {
  clearTimeout(editClickTimer)
  editing.value = { tagId: null, field: null }
  editDraft.value = ''
  editFieldRef.value = null
}

function setEditFieldRef(el) {
  editFieldRef.value = el
}

function startEdit(tag, field) {
  if (props.disabled || tag.muted) return
  editing.value = { tagId: tag.id, field }
  editDraft.value = field === 'label' ? displayLabel(tag) : (tag.value || '')
  nextTick(() => editFieldRef.value?.focus?.())
}

function onTextClick(tag, field) {
  if (props.disabled || tag.muted) return
  activateTag(tag)
  clearTimeout(editClickTimer)
  editClickTimer = window.setTimeout(() => {
    startEdit(tag, field)
  }, 220)
}

function onTagDblClick(tag) {
  if (props.disabled) return
  cancelEdit()
  pushUndo()
  activateTag(tag)
  tag.muted = !tag.muted
  if (tag.muted && activeTagId.value === tag.id) {
    activeTagId.value = null
  }
  flushEmitUpdate()
}

async function applyEnglishEdit(tag, rawText) {
  const text = String(rawText || '').trim()
  if (!text) {
    tag.value = ''
    tag.label = ''
    tag.known = false
    tag.weight = 1
    return
  }
  tag.value = text
  const r = await resolveLabelForValue(text)
  tag.label = r.known ? r.label : ''
  tag.known = r.known && !!tag.label
  tag.weight = getTagWeight(text)
}

async function applyChineseEdit(tag, rawText) {
  const text = String(rawText || '').trim()
  tag.label = text
  if (!text) {
    tag.known = false
    return
  }
  const hit = await lookupByChineseLabel(text)
  if (hit) {
    const insert = hit.insertText || hit.insert_text || ''
    tag.value = applyValueWithWeight(tag.value, insert)
    tag.known = true
  } else {
    tag.value = ''
    tag.known = false
  }
}

async function commitTagEdit(tag) {
  if (editing.value.tagId !== tag.id) return
  const field = editing.value.field
  const text = editDraft.value
  const prevText = field === 'label' ? displayLabel(tag) : (tag.value || '')
  if (String(text).trim() === String(prevText).trim()) {
    cancelEdit()
    return
  }
  cancelEdit()
  pushUndo()
  resolving.value = true
  try {
    if (field === 'value') {
      await applyEnglishEdit(tag, text)
    } else if (field === 'label') {
      await applyChineseEdit(tag, text)
    }
    flushEmitUpdate()
  } finally {
    resolving.value = false
  }
}
function showWeightBar(tag) {
  return canAdjustWeight(tag.value)
}

function tagWeightValue(tag) {
  return tag.weight ?? getTagWeight(tag.value)
}

function tagActiveLineStyle(tag) {
  return weightActiveLineStyle(tagWeightValue(tag))
}

function tagBlueZoneStyle(tag) {
  return weightBlueZoneStyle(tagWeightValue(tag))
}

function tagRedZoneStyle(tag) {
  return weightRedZoneStyle(tagWeightValue(tag))
}

function isTagActive(tag) {
  return activeTagId.value === tag.id
}

function activateTag(tag) {
  if (props.disabled) return
  activeTagId.value = tag.id
}

function onTagsAreaClick(event) {
  if (event.target.closest('[data-tag-chip]')) return
  deactivateTagSelection()
}

function tagChipClass(tag) {
  const active = isTagActive(tag)
  const activeCls = active
    ? 'z-[1] border-sky-400/55 ring-2 ring-sky-400/15'
    : ''
  if (tag.muted) {
    return cn(
      'border-2 border-dashed border-red-400/55 bg-red-500/5 opacity-60 saturate-75',
      'line-through decoration-muted-foreground/35',
      active && 'border-sky-400/45 ring-sky-400/12',
    )
  }
  if (!showWeightBar(tag)) {
    return cn(
      activeCls,
      hasChineseLabel(tag)
        ? 'border-border bg-muted/30'
        : 'border-dashed border-muted-foreground/35 bg-muted/20',
    )
  }
  return cn('border-border/70 bg-muted/10', activeCls)
}

async function copyAllTags() {
  const text = serialize()
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copyOk.value = true
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copyOk.value = false
    }, 1600)
  } catch {
    /* ignore */
  }
}

async function buildTag(rawValue, resolvedItem = null) {
  const v = String(rawValue || '').trim()
  if (!v) return null
  if (resolvedItem) {
    return resolvedItemToTag(resolvedItem)
  }
  const items = await resolveVocabularyValues([v])
  return items[0] ? resolvedItemToTag(items[0]) : resolvedItemToTag({ value: v, known: false, label: '' })
}

async function commitTag(rawValue) {
  const v = String(rawValue || '').trim()
  if (!v || props.disabled) return
  const dup = findDuplicateTag(v)
  if (dup) {
    draft.value = ''
    acClose()
    activateTag(dup)
    focusDraftInput()
    return
  }
  pushUndo()
  resolving.value = true
  try {
    const tag = await buildTag(v)
    if (tag) {
      tags.value.push(tag)
      await nextTick()
      const chip = editorRootRef.value?.querySelector(`[data-tag-id="${tag.id}"]`)
      if (chip) popIn(chip)
    }
    draft.value = ''
    acClose()
    flushEmitUpdate()
    focusDraftInput()
  } finally {
    resolving.value = false
  }
}

async function commitDraft() {
  await commitTag(draft.value)
}

async function syncFromModel(text) {
  syncing = true
  try {
    clearUndo()
    clearVocabularyResolveCache()
    const parts = splitPromptTokens(text || '')
    if (!parts.length) {
      tags.value = []
      return
    }
    const parsed = parts.map(parseStoredPromptToken)
    resolving.value = true
    const items = await resolveVocabularyValues(parsed.map((p) => p.value))
    tags.value = items.map((item, i) => {
      const tag = resolvedItemToTag(item)
      tag.muted = parsed[i]?.muted ?? false
      return tag
    })
  } finally {
    resolving.value = false
    syncing = false
  }
}

function emitUpdate() {
  if (syncing) return
  if (emitTimer) clearTimeout(emitTimer)
  emitTimer = setTimeout(() => {
    emitTimer = null
    flushEmitUpdate()
  }, EMIT_DEBOUNCE_MS)
}

function flushEmitUpdate() {
  if (emitTimer) {
    clearTimeout(emitTimer)
    emitTimer = null
  }
  if (syncing) return
  const next = serialize()
  if (next !== model.value) model.value = next
}

watch(
  () => model.value,
  (v) => {
    if (syncing) return
    if (serialize() === (v || '')) return
    if (modelMatchesTags(v || '')) return
    syncFromModel(v || '')
  },
  { immediate: true },
)

watch(tags, () => emitUpdate(), { deep: true })

function removeTag(id) {
  pushUndo()
  if (activeTagId.value === id) activeTagId.value = null
  const chip = editorRootRef.value?.querySelector(`[data-tag-id="${id}"]`)
  if (chip) {
    collapseOut(chip).then(() => {
      tags.value = tags.value.filter((t) => t.id !== id)
    })
    return
  }
  tags.value = tags.value.filter((t) => t.id !== id)
}
function onInput() {
  scheduleSuggest()
}

function onInputKeydown(event) {
  if (acOnKeydown(event)) return
  if (event.key === 'Enter') {
    event.preventDefault()
    if (acOpen.value) acClose()
    commitDraft()
    return
  }
  if (event.key === ',' || event.key === '，') {
    event.preventDefault()
    if (acOpen.value) acClose()
    commitDraft()
  }
}

function onInputBlur() {
  window.setTimeout(() => acClose(), 150)
}

async function onPaste(event) {
  const text = event.clipboardData?.getData('text') || ''
  if (!text.includes(',') && !text.includes('，') && !text.includes('\n')) return
  event.preventDefault()
  const parts = splitPromptTokens(text)
  if (!parts.length) return
  pushUndo()
  resolving.value = true
  try {
    const items = await resolveVocabularyValues(parts)
    for (const item of items) {
      const tag = resolvedItemToTag(item)
      if (findDuplicateTag(tag.value)) continue
      tags.value.push(tag)
    }
    draft.value = ''
    flushEmitUpdate()
    focusDraftInput()
  } finally {
    resolving.value = false
  }
}

function onTagWheel(event, tag) {
  if (tag.muted || !canAdjustWeight(tag.value)) return
  if (!isTagActive(tag)) return
  event.preventDefault()
  event.stopPropagation()
  pushUndo()
  const delta = event.deltaY < 0 ? 1 : -1
  patchTag(tag.id, { value: adjustWeight(tag.value, delta) })
}

function onTagChipClick(tag, event) {
  if (props.disabled) return
  event.stopPropagation()
  activateTag(tag)
}

function onAutocompleteSelect(index) {
  const item = acItems.value[index]
  if (!item) return
  commitTag(item.insertText || item.insert_text || '')
}
</script>

<template>
  <div
    ref="editorRootRef"
    data-prompt-tag-editor
    :data-prompt-side="promptSide || undefined"
    tabindex="-1"
    :class="
      cn(
        'flex h-full max-h-full min-h-0 w-full flex-col rounded-md border border-input bg-background px-2 py-2 text-sm shadow-sm focus-within:ring-2 focus-within:ring-ring',
        props.class,
      )
    "
  >
    <div class="flex min-h-[5rem] min-h-0 flex-1 flex-wrap content-start gap-1.5 overflow-y-auto overscroll-contain pb-2" @click="onTagsAreaClick">
      <div
        v-for="tag in tags"
        :key="tag.id"
        data-tag-chip
        :data-tag-id="tag.id"
        :data-tag-muted="tag.muted ? '' : undefined"
        class="group relative flex max-w-full min-h-[3rem] overflow-hidden rounded-md border pl-2 pr-6 transition-[box-shadow,border-color] duration-150"
        :class="[
          tagChipClass(tag),
          showWeightBar(tag) ? 'py-0' : 'py-1.5',
        ]"
        :title="
          tag.muted
            ? '已屏蔽（双击恢复）'
            : isTagActive(tag) && showWeightBar(tag)
              ? `已选中 · 滚轮调权重（${tagWeightValue(tag).toFixed(2)}）· 双击屏蔽`
              : showWeightBar(tag)
                ? '先点击选中，再滚轮调权重 · 双击屏蔽'
                : isTagActive(tag)
                  ? '已选中 · 双击屏蔽 · 点击中英文可编辑'
                  : '点击选中 · 双击屏蔽 · 点击中英文可编辑'
        "
        @click="onTagChipClick(tag, $event)"
        @dblclick="onTagDblClick(tag)"
        @wheel="onTagWheel($event, tag)"
      >
        <!-- 背景层：铺满整个 tag 芯片 -->
        <div
          v-if="showWeightBar(tag)"
          :key="`${tag.id}-w-${tagWeightValue(tag).toFixed(2)}`"
          class="pointer-events-none absolute inset-0 z-0 overflow-hidden rounded-[inherit]"
          aria-hidden="true"
        >
          <div
            class="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-transparent via-foreground/30 to-transparent"
          />

          <div
            v-if="tagBlueZoneStyle(tag)"
            class="absolute inset-x-0 overflow-hidden"
            :style="tagBlueZoneStyle(tag)"
          >
            <div
              class="absolute inset-0 bg-gradient-to-b from-blue-600/70 via-blue-500/45 to-blue-400/28 blur-sm"
            />
          </div>

          <div
            v-if="tagRedZoneStyle(tag)"
            class="absolute inset-x-0 overflow-hidden"
            :style="tagRedZoneStyle(tag)"
          >
            <div
              class="absolute inset-0 bg-gradient-to-t from-red-600/68 via-red-500/42 to-red-400/26 blur-sm"
            />
          </div>

          <div
            v-if="!isDefaultWeight(tagWeightValue(tag))"
            class="absolute inset-x-0 z-[1] h-px -translate-y-1/2 bg-gradient-to-r from-transparent via-white/55 to-transparent shadow-[0_0_6px_rgba(255,255,255,0.25)]"
            :style="tagActiveLineStyle(tag)"
          />
        </div>

        <button
          type="button"
          class="absolute right-0.5 top-0.5 z-20 rounded p-0.5 text-muted-foreground opacity-0 hover:bg-destructive/20 hover:text-destructive group-hover:opacity-100"
          :disabled="disabled"
          aria-label="删除标签"
          @click.stop="removeTag(tag.id)"
        >
          ×
        </button>

        <!-- 文字层：固定 50/50，与 tag 同尺寸 -->
        <div
          v-if="showWeightBar(tag)"
          class="relative z-10 flex min-h-[3rem] w-full min-w-0 flex-1 flex-col"
        >
          <div class="flex min-h-0 flex-1 items-center justify-center px-0.5">
            <PromptTagTextField
              v-if="hasChineseLabel(tag) || isEditing(tag.id, 'label')"
              :ref="isEditing(tag.id, 'label') ? setEditFieldRef : null"
              v-model="editDraft"
              :text="displayLabel(tag)"
              :editing="isEditing(tag.id, 'label')"
              :disabled="disabled"
              :edit-locked="tag.muted"
              placeholder="中文"
              @click="onTextClick(tag, 'label')"
              @dblclick="onTagDblClick(tag)"
              @commit="commitTagEdit(tag)"
              @cancel="cancelEdit"
            />
          </div>

          <div class="flex min-h-0 flex-1 items-center justify-center px-0.5">
            <div
              v-if="tag.value || isEditing(tag.id, 'value') || !hasChineseLabel(tag)"
              class="grid max-w-full justify-items-center text-center"
            >
              <span
                class="invisible col-start-1 row-start-1 font-mono text-xs leading-snug whitespace-pre"
                aria-hidden="true"
              >{{ tagValueReservedText(tag.value) }}</span>
              <PromptTagTextField
                :ref="isEditing(tag.id, 'value') ? setEditFieldRef : null"
                v-model="editDraft"
                class="col-start-1 row-start-1"
                :text="tag.value"
                :editing="isEditing(tag.id, 'value')"
                :disabled="disabled"
                :edit-locked="tag.muted"
                mono
                placeholder="英文"
                @click="onTextClick(tag, 'value')"
                @dblclick="onTagDblClick(tag)"
                @commit="commitTagEdit(tag)"
                @cancel="cancelEdit"
              />
            </div>
          </div>
        </div>

        <!-- 不可调权重：普通展示 -->
        <div
          v-else
          class="relative z-[1] min-w-0 flex-1 py-1.5 pr-1"
          :class="hasChineseLabel(tag) ? 'flex flex-col' : 'leading-tight'"
        >
          <template v-if="hasChineseLabel(tag) || isEditing(tag.id, 'label') || isEditing(tag.id, 'value')">
            <div class="pb-1 text-center leading-snug">
              <PromptTagTextField
                :ref="isEditing(tag.id, 'label') ? setEditFieldRef : null"
                v-model="editDraft"
                :text="displayLabel(tag)"
                :editing="isEditing(tag.id, 'label')"
                :disabled="disabled"
                :edit-locked="tag.muted"
                placeholder="中文"
                @click="onTextClick(tag, 'label')"
                @dblclick="onTagDblClick(tag)"
                @commit="commitTagEdit(tag)"
                @cancel="cancelEdit"
              />
            </div>
            <div
              class="h-px w-full shrink-0 bg-gradient-to-r from-transparent via-foreground/25 to-transparent"
              aria-hidden="true"
            />
            <div class="pt-1 text-center break-all leading-snug">
              <PromptTagTextField
                :ref="isEditing(tag.id, 'value') ? setEditFieldRef : null"
                v-model="editDraft"
                :text="tag.value"
                :editing="isEditing(tag.id, 'value')"
                :disabled="disabled"
                :edit-locked="tag.muted"
                mono
                placeholder="英文"
                @click="onTextClick(tag, 'value')"
                @dblclick="onTagDblClick(tag)"
                @commit="commitTagEdit(tag)"
                @cancel="cancelEdit"
              />
            </div>
          </template>
          <div
            v-else
            class="text-center break-all leading-snug"
          >
            <PromptTagTextField
              :ref="isEditing(tag.id, 'value') ? setEditFieldRef : null"
              v-model="editDraft"
              :text="tag.value"
              :editing="isEditing(tag.id, 'value')"
              :disabled="disabled"
              :edit-locked="tag.muted"
              mono
              placeholder="英文"
              @click="onTextClick(tag, 'value')"
              @dblclick="onTagDblClick(tag)"
              @commit="commitTagEdit(tag)"
              @cancel="cancelEdit"
            />
          </div>
        </div>
      </div>

      <p
        v-if="!tags.length && !draft"
        class="px-1 py-2 text-xs text-muted-foreground"
      >
        先点击 tag 选中（蓝色边框），再滚轮调权重；双击屏蔽；Ctrl+Z 撤回
      </p>
    </div>

    <div class="relative flex shrink-0 items-center gap-1 border-t border-border/60 pt-2">
      <input
        ref="inputRef"
        v-model="draft"
        type="text"
        class="min-w-0 flex-1 bg-transparent px-1 py-1 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50"
        :disabled="disabled || resolving"
        placeholder="输入 tag（中英文均可）…"
        @input="onInput"
        @keydown="onInputKeydown"
        @blur="onInputBlur"
        @paste="onPaste"
      />
      <button
        type="button"
        class="shrink-0 rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40"
        :disabled="disabled || !tags.length"
        :title="copyOk ? '已复制' : '复制全部 tag'"
        @click="copyAllTags"
      >
        <Check
          v-if="copyOk"
          class="h-4 w-4 text-primary"
        />
        <Copy
          v-else
          class="h-4 w-4"
        />
      </button>
      <PromptAutocompleteDropdown
        :open="acOpen"
        :loading="acLoading"
        :items="acItems"
        :selected-index="acSelectedIndex"
        :position="acPosition"
        @select="onAutocompleteSelect"
        @close="acClose"
      />
    </div>
  </div>
</template>
