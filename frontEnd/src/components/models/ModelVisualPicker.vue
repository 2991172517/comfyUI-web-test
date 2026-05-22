<script setup>
import { computed, onMounted, onUnmounted, ref, toRef } from 'vue'
import { ImageOff, Search } from 'lucide-vue-next'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import { useModelAssets } from '@/composables/useModelAssets.js'
import { splitSourceUrl } from '@/lib/modelDescription.js'
import { catalogThumb, modelDisplayTitle } from '@/lib/modelDisplay.js'
import { cn } from '@/lib/utils'

const FOLDER_META = {
  loras: {
    defaultLabel: 'LoRA',
    dialogTitle: '选择 LoRA',
    emptyPick: '点击选择 LoRA…',
    emptyMatch: '无匹配 LoRA',
  },
  checkpoints: {
    defaultLabel: 'Checkpoint',
    dialogTitle: '选择 Checkpoint',
    emptyPick: '点击选择 Checkpoint…',
    emptyMatch: '无匹配 Checkpoint',
  },
}

const props = defineProps({
  folder: { type: String, required: true },
  label: { type: String, default: '' },
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  /** enrich API: { name, previews, has_preview, has_summary }[] */
  catalog: { type: Array, default: () => [] },
  missingValue: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  /** loras 目录：loraName -> recommended | not_recommended | neutral */
  loraCompatMap: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue'])

const meta = computed(() => FOLDER_META[props.folder] || FOLDER_META.loras)
const displayLabel = computed(() => props.label || meta.value.defaultLabel)

const open = ref(false)
const query = ref('')

const catalogMap = computed(() => {
  const m = new Map()
  for (const item of props.catalog || []) {
    if (item?.name) m.set(item.name, item)
  }
  return m
})

function thumbFor(name) {
  return catalogThumb(catalogMap.value.get(name))
}

const optionList = computed(() => {
  let list = [...(props.options || [])]
  if (props.missingValue && props.modelValue && !list.includes(props.modelValue)) {
    list = [props.modelValue, ...list]
  }
  const seen = new Set()
  return list.filter((n) => {
    if (!n || seen.has(n)) return false
    seen.add(n)
    return true
  })
})

const filteredOptions = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return optionList.value
  return optionList.value.filter((name) => {
    const title = modelDisplayTitle(name).toLowerCase()
    return name.toLowerCase().includes(q) || title.includes(q)
  })
})

const { summary, loading: summaryLoading } = useModelAssets(
  toRef(props, 'folder'),
  toRef(props, 'modelValue'),
)

const selectedTitle = computed(() => modelDisplayTitle(props.modelValue))

const summaryDisplay = computed(() => {
  if (!summary.value) return null
  const fromApi = summary.value.sourceUrl
  if (fromApi) {
    return {
      sourceUrl: fromApi,
      content: summary.value.content || '',
      truncated: summary.value.truncated,
    }
  }
  const split = splitSourceUrl(summary.value.content || '')
  return { ...split, truncated: summary.value.truncated }
})

function loraCompatStatus(name) {
  if (props.folder !== 'loras' || !props.loraCompatMap) return 'neutral'
  return props.loraCompatMap[name] || 'neutral'
}

function loraCompatHint(name) {
  const s = loraCompatStatus(name)
  if (s === 'not_recommended') return '不推荐用于当前 Checkpoint，仍可选择'
  if (s === 'recommended') return '推荐用于当前 Checkpoint'
  return ''
}

function pick(name) {
  emit('update:modelValue', name)
  open.value = false
  query.value = ''
}

function openPicker() {
  if (props.disabled || props.loading) return
  open.value = true
}

function closePicker() {
  open.value = false
  query.value = ''
}

function onKeydown(e) {
  if (e.key === 'Escape' && open.value) closePicker()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="space-y-2">
    <Label v-if="displayLabel">{{ displayLabel }}</Label>

    <div
      v-if="modelValue"
      role="button"
      tabindex="0"
      :class="
        cn(
          'flex gap-3 rounded-lg border border-border bg-muted/15 p-3 text-left transition-colors w-full',
          disabled || loading
            ? 'opacity-60 cursor-not-allowed'
            : 'cursor-pointer hover:border-primary/40 hover:bg-muted/25',
        )
      "
      :aria-disabled="disabled || loading"
      @click="openPicker"
      @keydown.enter.prevent="openPicker"
      @keydown.space.prevent="openPicker"
    >
      <div
        class="relative h-24 w-24 shrink-0 overflow-hidden rounded-md border border-border bg-muted/40 pointer-events-none"
      >
        <img
          v-if="thumbFor(modelValue)"
          :src="thumbFor(modelValue)"
          :alt="selectedTitle"
          class="h-full w-full object-cover"
          loading="lazy"
        />
        <div
          v-else
          class="flex h-full flex-col items-center justify-center gap-0.5 px-1 text-center text-muted-foreground"
        >
          <ImageOff class="h-5 w-5 opacity-50" />
          <span class="text-[9px]">无预览</span>
        </div>
      </div>
      <div class="min-w-0 flex-1 space-y-1.5">
        <div class="pointer-events-none">
          <p class="text-sm font-semibold leading-snug truncate" :title="selectedTitle">
            {{ selectedTitle }}
          </p>
          <p class="text-[10px] text-muted-foreground font-mono truncate" :title="modelValue">
            {{ modelValue }}
          </p>
        </div>

        <div
          v-if="summaryDisplay"
          class="rounded-md border border-border/70 bg-background/60 p-2 max-h-32 overflow-auto"
          @click.stop
        >
          <a
            v-if="summaryDisplay.sourceUrl"
            :href="summaryDisplay.sourceUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="text-[11px] text-primary hover:underline block mb-1.5 break-all font-medium"
            @click.stop
          >
            {{ summaryDisplay.sourceUrl }}
          </a>
          <pre
            v-if="summaryDisplay.content"
            class="whitespace-pre-wrap break-words text-[11px] text-muted-foreground leading-relaxed"
            >{{ summaryDisplay.content }}</pre
          >
          <p v-if="summaryDisplay.truncated" class="text-[10px] text-muted-foreground/70 mt-1">
            （内容已截断）
          </p>
        </div>
        <p
          v-else-if="summaryLoading"
          class="text-[10px] text-muted-foreground pointer-events-none"
        >
          加载说明…
        </p>
        <p v-else class="text-[10px] text-muted-foreground pointer-events-none">
          暂无模型说明（可在模型同名文件夹内放置 模型说明.txt）
        </p>
      </div>
    </div>

    <button
      v-else
      type="button"
      class="w-full rounded-lg border border-dashed border-border px-4 py-6 text-sm text-muted-foreground hover:border-primary/40 hover:bg-muted/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="disabled || loading"
      @click="openPicker"
    >
      {{ loading ? '加载模型列表…' : meta.emptyPick }}
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        class="fixed inset-0 z-[80] flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/55"
        role="dialog"
        aria-modal="true"
        :aria-label="`${displayLabel} 选择器`"
        @click.self="closePicker"
      >
        <div
          class="flex max-h-[min(88vh,720px)] w-full sm:max-w-3xl flex-col rounded-t-xl sm:rounded-xl border border-border bg-card shadow-xl"
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
                placeholder="搜索文件名或短名…"
                autocomplete="off"
              />
            </div>
            <p class="mt-1.5 text-[10px] text-muted-foreground">
              共 {{ optionList.length }} 个 · 显示 {{ filteredOptions.length }} 个
              <span v-if="folder === 'loras' && loraCompatMap">
                · 灰字为不推荐（仍可选）
              </span>
            </p>
          </div>

          <div class="flex-1 overflow-y-auto p-3">
            <p
              v-if="!filteredOptions.length"
              class="py-8 text-center text-sm text-muted-foreground"
            >
              {{ meta.emptyMatch }}
            </p>
            <div v-else class="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
              <button
                v-for="name in filteredOptions"
                :key="name"
                type="button"
                :disabled="disabled"
                :title="loraCompatHint(name) || modelDisplayTitle(name)"
                :class="
                  cn(
                    'flex flex-col overflow-hidden rounded-lg border text-left transition-colors',
                    'hover:border-primary/50 hover:bg-primary/5',
                    modelValue === name
                      ? 'border-primary ring-2 ring-primary/30 bg-primary/5'
                      : loraCompatStatus(name) === 'not_recommended'
                        ? 'border-amber-500/35 bg-muted/5 opacity-60 grayscale-[0.35]'
                        : loraCompatStatus(name) === 'recommended'
                          ? 'border-emerald-500/30 bg-emerald-500/5'
                          : 'border-border bg-muted/10',
                  )
                "
                @click="pick(name)"
              >
                <div class="aspect-[4/5] w-full bg-muted/30 relative">
                  <img
                    v-if="thumbFor(name)"
                    :src="thumbFor(name)"
                    :alt="modelDisplayTitle(name)"
                    class="h-full w-full object-cover"
                    loading="lazy"
                  />
                  <div
                    v-else
                    class="flex h-full flex-col items-center justify-center gap-1 px-2 text-muted-foreground"
                  >
                    <ImageOff class="h-6 w-6 opacity-40" />
                    <span class="text-[9px] text-center leading-tight">无预览图</span>
                  </div>
                  <Badge
                    v-if="loraCompatStatus(name) === 'not_recommended'"
                    variant="outline"
                    class="absolute top-1 left-1 text-[8px] px-1 py-0 border-amber-500/50 text-amber-700 dark:text-amber-300 bg-background/90"
                  >
                    不推荐
                  </Badge>
                  <Badge
                    v-else-if="loraCompatStatus(name) === 'recommended'"
                    variant="outline"
                    class="absolute top-1 left-1 text-[8px] px-1 py-0 border-emerald-500/50 text-emerald-700 dark:text-emerald-300 bg-background/90"
                  >
                    推荐
                  </Badge>
                  <Badge
                    v-if="modelValue === name"
                    class="absolute top-1 right-1 text-[9px] px-1 py-0"
                  >
                    当前
                  </Badge>
                </div>
                <div class="space-y-0.5 p-2 min-w-0">
                  <p
                    class="text-[11px] font-medium leading-tight line-clamp-2"
                    :title="modelDisplayTitle(name)"
                  >
                    {{ modelDisplayTitle(name) }}
                  </p>
                  <p
                    :class="
                      cn(
                        'text-[9px] font-mono truncate',
                        loraCompatStatus(name) === 'not_recommended'
                          ? 'text-amber-700/80 dark:text-amber-300/80'
                          : 'text-muted-foreground',
                      )
                    "
                    :title="name"
                  >
                    {{ name }}
                  </p>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
