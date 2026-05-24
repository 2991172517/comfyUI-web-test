<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ImageOff, Search, ThumbsDown, ThumbsUp, Minus } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Badge from '@/components/ui/Badge.vue'
import { catalogThumb, modelDisplayTitle } from '@/lib/modelDisplay.js'
import { cn } from '@/lib/utils'
import { useModalMotion } from '@/composables/useModalMotion.js'

const open = defineModel('open', { type: Boolean, default: false })
const backdropRef = ref(null)
const panelRef = ref(null)
useModalMotion(open, backdropRef, panelRef)

const props = defineProps({
  checkpointName: { type: String, required: true },
  allLoras: { type: Array, default: () => [] },
  loraCatalog: { type: Array, default: () => [] },
  recommended: { type: Array, default: () => [] },
  notRecommended: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:recommended', 'update:notRecommended', 'saved'])

const query = ref('')
const filterMode = ref('all')
const saving = ref(false)
let saveTimer = null

const draftRecommended = ref([])
const draftNotRecommended = ref([])

watch(open, (isOpen) => {
    if (isOpen) {
      draftRecommended.value = [...(props.recommended || [])]
      draftNotRecommended.value = [...(props.notRecommended || [])]
      query.value = ''
      filterMode.value = 'all'
    }
  },
)

const catalogMap = computed(() => {
  const m = new Map()
  for (const item of props.loraCatalog || []) {
    if (item?.name) m.set(item.name, item)
  }
  return m
})

function thumbFor(name) {
  return catalogThumb(catalogMap.value.get(name))
}

function statusFor(name) {
  if (draftRecommended.value.includes(name)) return 'recommended'
  if (draftNotRecommended.value.includes(name)) return 'not_recommended'
  return 'neutral'
}

const optionList = computed(() => {
  const seen = new Set()
  return [...(props.allLoras || [])].map(String).filter((n) => {
    if (!n || seen.has(n)) return false
    seen.add(n)
    return true
  })
})

const filteredOptions = computed(() => {
  const q = query.value.trim().toLowerCase()
  let list = optionList.value
  if (q) {
    list = list.filter((name) => {
      const title = modelDisplayTitle(name).toLowerCase()
      return name.toLowerCase().includes(q) || title.includes(q)
    })
  }
  if (filterMode.value === 'recommended') {
    list = list.filter((n) => draftRecommended.value.includes(n))
  } else if (filterMode.value === 'not_recommended') {
    list = list.filter((n) => draftNotRecommended.value.includes(n))
  } else if (filterMode.value === 'neutral') {
    list = list.filter(
      (n) =>
        !draftRecommended.value.includes(n) && !draftNotRecommended.value.includes(n),
    )
  }
  return list
})

function emitDraft() {
  emit('update:recommended', [...draftRecommended.value])
  emit('update:notRecommended', [...draftNotRecommended.value])
  scheduleSave()
}

function setStatus(name, status) {
  const rec = new Set(draftRecommended.value)
  const avoid = new Set(draftNotRecommended.value)
  rec.delete(name)
  avoid.delete(name)
  if (status === 'recommended') rec.add(name)
  else if (status === 'not_recommended') avoid.add(name)
  draftRecommended.value = [...rec]
  draftNotRecommended.value = [...avoid]
  emitDraft()
}

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(saveNow, 450)
}

async function saveNow() {
  if (!props.checkpointName) return
  saving.value = true
  try {
    await api.saveCheckpointLoraCompat({
      checkpoint: props.checkpointName,
      recommended: draftRecommended.value,
      not_recommended: draftNotRecommended.value,
    })
    emit('saved')
  } finally {
    saving.value = false
  }
}

function close() {
  open.value = false
}

function onKeydown(e) {
  if (e.key === 'Escape' && open.value) close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  if (saveTimer) clearTimeout(saveTimer)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="backdropRef"
      class="fixed inset-0 z-[85] flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/55"
      role="dialog"
      aria-modal="true"
      aria-label="LoRA 适配配置"
      @click.self="close"
    >
      <div
        ref="panelRef"
        class="flex max-h-[min(90vh,780px)] w-full sm:max-w-4xl flex-col rounded-t-xl sm:rounded-xl border border-border bg-card shadow-xl"
        @click.stop
      >
        <div class="flex flex-wrap items-start justify-between gap-3 border-b border-border px-4 py-3">
          <div class="min-w-0">
            <p class="text-sm font-semibold">LoRA 适配配置</p>
            <p class="text-[11px] text-muted-foreground mt-0.5 truncate" :title="checkpointName">
              针对 Checkpoint：<span class="font-mono text-foreground">{{ checkpointName }}</span>
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span v-if="saving" class="text-[10px] text-muted-foreground">保存中…</span>
            <Button variant="ghost" size="sm" class="h-8" @click="close">完成</Button>
          </div>
        </div>

        <div class="px-4 py-3 border-b border-border/80 space-y-2">
          <div class="relative">
            <Search
              class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              v-model="query"
              class="pl-8 h-9"
              placeholder="搜索 LoRA 文件名或短名…"
              autocomplete="off"
            />
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <div class="inline-flex rounded-lg border border-border p-0.5 text-[11px]">
              <button
                v-for="m in [
                  { id: 'all', label: '全部' },
                  { id: 'recommended', label: '推荐' },
                  { id: 'not_recommended', label: '不推荐' },
                  { id: 'neutral', label: '未标记' },
                ]"
                :key="m.id"
                type="button"
                :class="
                  cn(
                    'rounded-md px-2.5 py-1 transition-colors',
                    filterMode === m.id
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground',
                  )
                "
                @click="filterMode = m.id"
              >
                {{ m.label }}
              </button>
            </div>
            <Badge variant="outline" class="text-emerald-600 border-emerald-500/40 text-[10px]">
              推荐 {{ draftRecommended.length }}
            </Badge>
            <Badge variant="outline" class="text-amber-600 border-amber-500/40 text-[10px]">
              不推荐 {{ draftNotRecommended.length }}
            </Badge>
            <p class="text-[10px] text-muted-foreground ml-auto">
              {{ filteredOptions.length }} / {{ optionList.length }} 个
            </p>
          </div>
          <p class="text-[10px] text-muted-foreground">
            生成页选 LoRA 时：不推荐会灰显并提示，但仍可手动选择。
          </p>
        </div>

        <div class="flex-1 overflow-y-auto p-3 min-h-[200px]">
          <p
            v-if="!filteredOptions.length"
            class="py-12 text-center text-sm text-muted-foreground"
          >
            {{ optionList.length ? '无匹配 LoRA' : '本地 loras 目录为空' }}
          </p>
          <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            <article
              v-for="name in filteredOptions"
              :key="name"
              :class="
                cn(
                  'flex flex-col overflow-hidden rounded-xl border bg-card transition-shadow',
                  statusFor(name) === 'recommended' &&
                    'border-emerald-500/50 ring-1 ring-emerald-500/25 shadow-sm',
                  statusFor(name) === 'not_recommended' &&
                    'border-amber-500/45 ring-1 ring-amber-500/20 opacity-90',
                  statusFor(name) === 'neutral' && 'border-border',
                )
              "
            >
              <div class="relative aspect-[4/5] w-full bg-muted/30">
                <img
                  v-if="thumbFor(name)"
                  :src="thumbFor(name)"
                  :alt="modelDisplayTitle(name)"
                  class="h-full w-full object-cover"
                  loading="lazy"
                />
                <div
                  v-else
                  class="flex h-full flex-col items-center justify-center gap-1 text-muted-foreground"
                >
                  <ImageOff class="h-7 w-7 opacity-40" />
                  <span class="text-[9px]">无预览</span>
                </div>
                <Badge
                  v-if="statusFor(name) === 'recommended'"
                  class="absolute top-1.5 left-1.5 text-[9px] px-1.5 py-0 bg-emerald-600 hover:bg-emerald-600"
                >
                  推荐
                </Badge>
                <Badge
                  v-else-if="statusFor(name) === 'not_recommended'"
                  variant="outline"
                  class="absolute top-1.5 left-1.5 text-[9px] px-1.5 py-0 border-amber-500/60 text-amber-800 dark:text-amber-200 bg-background/90"
                >
                  不推荐
                </Badge>
              </div>
              <div class="p-2 space-y-1.5 min-w-0 border-t border-border/60">
                <p
                  class="text-[11px] font-medium leading-tight line-clamp-2"
                  :title="modelDisplayTitle(name)"
                >
                  {{ modelDisplayTitle(name) }}
                </p>
                <p class="text-[9px] text-muted-foreground font-mono truncate" :title="name">
                  {{ name }}
                </p>
                <div class="grid grid-cols-3 gap-1 pt-0.5">
                  <button
                    type="button"
                    :class="
                      cn(
                        'flex flex-col items-center gap-0.5 rounded-md border py-1 text-[9px] transition-colors',
                        statusFor(name) === 'neutral'
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border hover:bg-muted/50 text-muted-foreground',
                      )
                    "
                    title="未标记"
                    @click="setStatus(name, 'neutral')"
                  >
                    <Minus class="h-3 w-3" />
                    默认
                  </button>
                  <button
                    type="button"
                    :class="
                      cn(
                        'flex flex-col items-center gap-0.5 rounded-md border py-1 text-[9px] transition-colors',
                        statusFor(name) === 'recommended'
                          ? 'border-emerald-500 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                          : 'border-border hover:bg-emerald-500/10 text-muted-foreground',
                      )
                    "
                    title="推荐用于此 Checkpoint"
                    @click="setStatus(name, 'recommended')"
                  >
                    <ThumbsUp class="h-3 w-3" />
                    推荐
                  </button>
                  <button
                    type="button"
                    :class="
                      cn(
                        'flex flex-col items-center gap-0.5 rounded-md border py-1 text-[9px] transition-colors',
                        statusFor(name) === 'not_recommended'
                          ? 'border-amber-500 bg-amber-500/15 text-amber-800 dark:text-amber-200'
                          : 'border-border hover:bg-amber-500/10 text-muted-foreground',
                      )
                    "
                    title="不推荐用于此 Checkpoint"
                    @click="setStatus(name, 'not_recommended')"
                  >
                    <ThumbsDown class="h-3 w-3" />
                    不推荐
                  </button>
                </div>
              </div>
            </article>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
