<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import AnimatedCollapse from '@/components/ui/AnimatedCollapse.vue'
import { stripMutedStoredToken } from '@/lib/promptMutedTag.js'

const props = defineProps({
  tokens: { type: Array, default: () => [] },
  weights: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update-weight'])

const WEIGHT_EMIT_DEBOUNCE_MS = 400

const expanded = ref(false)
const drafts = ref([])
const editingIndex = ref(null)
let emitTimer = null

function normalizeWeight(val) {
  const n = Number(val)
  return Number.isFinite(n) && n >= 0 ? n : 1
}

function draftWeightAt(index) {
  const raw = drafts.value[index]
  if (raw != null && raw !== '') return normalizeWeight(raw)
  return Number(props.weights[index] ?? 1) || 0
}

function syncDraftsFromProps() {
  drafts.value = props.tokens.map((_, i) => {
    if (editingIndex.value === i && drafts.value[i] != null && drafts.value[i] !== '') {
      return drafts.value[i]
    }
    return props.weights[i] ?? 1
  })
}

watch(
  () => ({
    tokenCount: props.tokens.length,
    weights: (props.weights || []).join(','),
  }),
  syncDraftsFromProps,
  { immediate: true },
)

const entries = computed(() => {
  const list = props.tokens.map((token, index) => ({
    token: stripMutedStoredToken(String(token || '').trim()),
    index,
    weight: draftWeightAt(index),
  }))
  const total = list.reduce((sum, item) => sum + item.weight, 0) || 1
  const max = Math.max(...list.map((item) => item.weight), 0.001)
  return list
    .map((item) => ({
      ...item,
      percent: (item.weight / total) * 100,
      barRatio: item.weight / max,
    }))
    .sort((a, b) => b.weight - a.weight || a.index - b.index)
})

const collapsedHint = computed(() => {
  const n = props.tokens.length
  if (!n) return '输入词条后可配置随机抽中权重'
  return `${n} 个词条 · 点击展开调整抽中权重与分布`
})

function formatWeight(weight) {
  const n = Number(weight)
  if (!Number.isFinite(n)) return '1'
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, '')
}

function formatPercent(percent) {
  const n = Number(percent)
  if (!Number.isFinite(n)) return '0%'
  return `${n.toFixed(1)}%`
}

function barFillStyle(ratio, weight) {
  const t = Math.max(0, Math.min(1, ratio))
  const lightness = 86 - t * 44
  return {
    width: `${Math.max(t * 100, weight > 0 ? 3 : 0)}%`,
    backgroundColor: `hsl(217, 78%, ${lightness}%)`,
    transition: 'width 0.22s ease-out, background-color 0.22s ease-out',
  }
}

function flushDraftWeights() {
  for (let i = 0; i < props.tokens.length; i++) {
    const normalized = normalizeWeight(drafts.value[i] ?? props.weights[i] ?? 1)
    drafts.value[i] = normalized
    if (Math.abs(normalized - (props.weights[i] ?? 1)) > 0.0001) {
      emit('update-weight', i, normalized)
    }
  }
}

function scheduleDraftEmit() {
  if (emitTimer) clearTimeout(emitTimer)
  emitTimer = setTimeout(() => {
    emitTimer = null
    flushDraftWeights()
  }, WEIGHT_EMIT_DEBOUNCE_MS)
}

function commitWeight(index) {
  if (emitTimer) {
    clearTimeout(emitTimer)
    emitTimer = null
  }
  editingIndex.value = null
  const normalized = normalizeWeight(drafts.value[index])
  drafts.value[index] = normalized
  if (Math.abs(normalized - (props.weights[index] ?? 1)) > 0.0001) {
    emit('update-weight', index, normalized)
  }
}

function bump(index, delta) {
  const current = normalizeWeight(drafts.value[index] ?? props.weights[index] ?? 1)
  const next = Math.max(0, current + delta)
  drafts.value[index] = next
  scheduleDraftEmit()
}

function onDraftInput(index, event) {
  const next = drafts.value.slice()
  next[index] = event.target.value
  drafts.value = next
}

function onDraftFocus(index) {
  editingIndex.value = index
}

function onDraftBlur(index) {
  commitWeight(index)
}

function onDraftEnter(event) {
  event.target?.blur?.()
}

onUnmounted(() => {
  if (emitTimer) {
    clearTimeout(emitTimer)
    emitTimer = null
    flushDraftWeights()
  }
})
</script>

<template>
  <div class="rounded-md border border-border/60 bg-muted/10 overflow-hidden">
    <button
      type="button"
      class="flex w-full items-center justify-between gap-2 px-2.5 py-2 text-left hover:bg-muted/25 transition-colors"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <div class="min-w-0">
        <p class="text-[10px] font-medium text-foreground">随机抽中权重</p>
        <p class="text-[10px] text-muted-foreground mt-0.5 truncate">{{ collapsedHint }}</p>
      </div>
      <ChevronDown
        :class="
          cn(
            'h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform',
            expanded && 'rotate-180',
          )
        "
      />
    </button>

    <AnimatedCollapse v-model="expanded">
    <div class="border-t border-border/50 px-2.5 py-2 space-y-1.5">
      <p v-if="!tokens.length" class="text-[10px] text-muted-foreground">
        暂无词条
      </p>

      <div
        v-for="row in entries"
        :key="row.index"
        class="grid grid-cols-[minmax(4.5rem,7rem)_1fr] gap-x-2 gap-y-0.5 items-center"
      >
        <span
          class="truncate font-mono text-[10px] text-foreground"
          :title="row.token"
        >{{ row.token }}</span>

        <div class="flex min-w-0 items-center gap-1.5">
          <div class="relative h-2 flex-1 min-w-[3rem] overflow-hidden rounded-full bg-muted/50">
            <div
              class="absolute inset-y-0 left-0 rounded-full"
              :style="barFillStyle(row.barRatio, row.weight)"
            />
          </div>

          <span class="shrink-0 font-mono text-[10px] text-muted-foreground tabular-nums w-[4.5rem] text-right">
            {{ formatWeight(row.weight) }} · {{ formatPercent(row.percent) }}
          </span>

          <button
            type="button"
            class="h-6 w-5 shrink-0 rounded text-xs text-muted-foreground hover:bg-muted disabled:opacity-40"
            :disabled="disabled"
            aria-label="降低抽中权重"
            @click="bump(row.index, -1)"
          >
            −
          </button>
          <input
            type="number"
            min="0"
            step="0.1"
            class="h-6 w-11 shrink-0 rounded border-0 bg-transparent px-0 text-center text-[10px] outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
            :value="drafts[row.index]"
            :disabled="disabled"
            @focus="onDraftFocus(row.index)"
            @input="onDraftInput(row.index, $event)"
            @blur="onDraftBlur(row.index)"
            @keydown.enter="onDraftEnter"
          />
          <button
            type="button"
            class="h-6 w-5 shrink-0 rounded text-xs text-muted-foreground hover:bg-muted disabled:opacity-40"
            :disabled="disabled"
            aria-label="提高抽中权重"
            @click="bump(row.index, 1)"
          >
            +
          </button>
        </div>
      </div>
    </div>
    </AnimatedCollapse>
  </div>
</template>
