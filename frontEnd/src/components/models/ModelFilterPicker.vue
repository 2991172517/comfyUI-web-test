<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ChevronDown, ImageOff, Search, X } from 'lucide-vue-next'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import { catalogThumb, modelDisplayTitle } from '@/lib/modelDisplay.js'
import { cn } from '@/lib/utils'

const FOLDER_META = {
  loras: { dialogTitle: '筛选 LoRA', emptyMatch: '无匹配 LoRA' },
  checkpoints: { dialogTitle: '筛选 Checkpoint', emptyMatch: '无匹配 Checkpoint' },
}

const props = defineProps({
  label: { type: String, default: '' },
  folder: { type: String, required: true },
  modelValue: { type: String, default: '' },
  /** Checkpoint：文件名列表 */
  options: { type: Array, default: () => [] },
  /** LoRA：{ lora_name, short_name }[]，优先于 options */
  loraRows: { type: Array, default: null },
  catalog: { type: Array, default: () => [] },
  allowEmpty: { type: Boolean, default: true },
  emptyLabel: { type: String, default: '全部' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  triggerClass: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'change'])

const meta = computed(() => FOLDER_META[props.folder] || FOLDER_META.loras)
const open = ref(false)
const query = ref('')

const catalogMap = computed(() => {
  const m = new Map()
  for (const item of props.catalog || []) {
    if (item?.name) m.set(item.name, item)
  }
  return m
})

const entries = computed(() => {
  if (props.loraRows?.length) {
    return props.loraRows.map((l) => ({
      value: String(l.lora_name || ''),
      title: String(l.short_name || modelDisplayTitle(l.lora_name)),
    }))
  }
  const seen = new Set()
  const out = []
  for (const raw of props.options || []) {
    const value = String(raw || '')
    if (!value || seen.has(value)) continue
    seen.add(value)
    out.push({ value, title: modelDisplayTitle(value) })
  }
  return out
})

const displayText = computed(() => {
  if (!props.modelValue) return props.emptyLabel
  const hit = entries.value.find((e) => e.value === props.modelValue)
  return hit?.title || modelDisplayTitle(props.modelValue)
})

const triggerThumb = computed(() => {
  if (!props.modelValue) return null
  return catalogThumb(catalogMap.value.get(props.modelValue))
})

const filteredEntries = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return entries.value
  return entries.value.filter(
    (e) =>
      e.value.toLowerCase().includes(q) ||
      e.title.toLowerCase().includes(q),
  )
})

function thumbFor(value) {
  return catalogThumb(catalogMap.value.get(value))
}

function pick(value) {
  emit('update:modelValue', value)
  emit('change', value)
  closePicker()
}

function openPicker() {
  if (props.disabled || props.loading) return
  open.value = true
}

function closePicker() {
  open.value = false
  query.value = ''
}

function clearValue(ev) {
  ev?.stopPropagation?.()
  pick('')
}

function onKeydown(e) {
  if (e.key === 'Escape' && open.value) closePicker()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="space-y-1">
    <Label v-if="label" class="text-xs">{{ label }}</Label>
    <div
      role="button"
      tabindex="0"
      :aria-disabled="disabled || loading"
      :class="
        cn(
          'flex h-9 w-full min-w-[11rem] max-w-xs items-center gap-2 rounded-md border border-input',
          'bg-background px-2.5 text-sm shadow-sm transition-colors text-left cursor-pointer',
          'hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          (disabled || loading) && 'pointer-events-none opacity-50',
          !modelValue && 'text-muted-foreground',
          triggerClass,
        )
      "
      @click="openPicker"
      @keydown.enter.prevent="openPicker"
      @keydown.space.prevent="openPicker"
    >
      <span
        v-if="triggerThumb"
        class="h-7 w-7 shrink-0 overflow-hidden rounded border border-border/60 bg-muted/30"
      >
        <img :src="triggerThumb" :alt="displayText" class="h-full w-full object-cover" loading="lazy" />
      </span>
      <span
        v-else-if="modelValue"
        class="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-border/60 bg-muted/20 text-muted-foreground"
      >
        <ImageOff class="h-3.5 w-3.5 opacity-60" />
      </span>
      <span class="min-w-0 flex-1 truncate font-medium">{{ displayText }}</span>
      <span
        v-if="modelValue && allowEmpty"
        role="button"
        tabindex="0"
        class="shrink-0 rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
        title="清除筛选"
        @click.stop="clearValue"
        @keydown.enter.stop.prevent="clearValue"
      >
        <X class="h-3.5 w-3.5" />
      </span>
      <ChevronDown class="h-4 w-4 shrink-0 text-muted-foreground opacity-70" />
    </div>

    <Teleport to="body">
      <div
        v-if="open"
        class="fixed inset-0 z-[80] flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/55"
        role="dialog"
        aria-modal="true"
        :aria-label="meta.dialogTitle"
        @click.self="closePicker"
      >
        <div
          class="flex max-h-[min(88vh,680px)] w-full sm:max-w-3xl flex-col rounded-t-xl sm:rounded-xl border border-border bg-card shadow-xl"
          @click.stop
        >
          <div class="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
            <p class="text-sm font-semibold">{{ meta.dialogTitle }}</p>
            <Button variant="ghost" size="sm" class="h-8" @click="closePicker">关闭</Button>
          </div>

          <div class="px-4 py-3 border-b border-border/80">
            <div class="relative">
              <Search
                class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                v-model="query"
                class="pl-8"
                placeholder="搜索名称…"
                autocomplete="off"
              />
            </div>
            <p class="mt-1.5 text-[10px] text-muted-foreground">
              共 {{ entries.length }} 项 · 显示 {{ filteredEntries.length }} 项
            </p>
          </div>

          <div class="flex-1 overflow-y-auto p-3">
            <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
              <button
                v-if="allowEmpty"
                type="button"
                :class="
                  cn(
                    'flex flex-col items-center justify-center rounded-lg border px-2 py-6 text-center transition-colors min-h-[120px]',
                    !modelValue
                      ? 'border-primary ring-2 ring-primary/30 bg-primary/5'
                      : 'border-dashed border-border hover:border-primary/40 hover:bg-muted/30',
                  )
                "
                @click="pick('')"
              >
                <span class="text-sm font-medium">{{ emptyLabel }}</span>
                <span class="text-[10px] text-muted-foreground mt-1">不限</span>
              </button>

              <button
                v-for="entry in filteredEntries"
                :key="entry.value"
                type="button"
                :class="
                  cn(
                    'flex flex-col overflow-hidden rounded-lg border text-left transition-colors',
                    modelValue === entry.value
                      ? 'border-primary ring-2 ring-primary/30 bg-primary/5'
                      : 'border-border bg-muted/10 hover:border-primary/50 hover:bg-primary/5',
                  )
                "
                @click="pick(entry.value)"
              >
                <div class="aspect-[4/5] w-full bg-muted/30 relative">
                  <img
                    v-if="thumbFor(entry.value)"
                    :src="thumbFor(entry.value)"
                    :alt="entry.title"
                    class="h-full w-full object-cover"
                    loading="lazy"
                  />
                  <div
                    v-else
                    class="flex h-full flex-col items-center justify-center gap-1 px-2 text-muted-foreground"
                  >
                    <ImageOff class="h-5 w-5 opacity-40" />
                    <span class="text-[9px]">无预览</span>
                  </div>
                  <Badge
                    v-if="modelValue === entry.value"
                    class="absolute top-1 right-1 text-[9px] px-1 py-0"
                  >
                    当前
                  </Badge>
                </div>
                <div class="space-y-0.5 p-2 min-w-0">
                  <p class="text-[11px] font-medium leading-tight line-clamp-2" :title="entry.title">
                    {{ entry.title }}
                  </p>
                  <p
                    v-if="entry.title !== entry.value"
                    class="text-[9px] text-muted-foreground font-mono truncate"
                    :title="entry.value"
                  >
                    {{ entry.value }}
                  </p>
                </div>
              </button>
            </div>
            <p
              v-if="!filteredEntries.length && !allowEmpty"
              class="py-8 text-center text-sm text-muted-foreground"
            >
              {{ meta.emptyMatch }}
            </p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
