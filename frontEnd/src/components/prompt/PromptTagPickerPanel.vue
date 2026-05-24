<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronDown, Loader2 } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { cn } from '@/lib/utils'
import { lookupKeyForVocabulary } from '@/lib/promptTagWeight.js'
import { splitPromptTokens } from '@/lib/promptDisplay.js'

const props = defineProps({
  /** 当前提示词，用于高亮已选 tag */
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])

const expanded = ref(false)
const hasLoaded = ref(false)
const loadingTree = ref(false)
const tree = ref([])
const errorMsg = ref('')
const expandedId = ref('')
const activeLeafId = ref('')
const prompts = ref([])
const listLoading = ref(false)
const listTotal = ref(0)
const listOffset = ref(0)
const LIST_LIMIT = 80

function findNode(nodes, id) {
  for (const n of nodes || []) {
    if (n.id === id) return n
    const hit = findNode(n.children, id)
    if (hit) return hit
  }
  return null
}

function isLeaf(node) {
  return !node?.children?.length
}

function containsDescendant(node, targetId) {
  if (!node || !targetId) return false
  if (node.id === targetId) return true
  for (const c of node.children || []) {
    if (containsDescendant(c, targetId)) return true
  }
  return false
}

function defaultLeafId(node) {
  if (!node) return ''
  if (isLeaf(node)) return node.id
  return defaultLeafId(node.children[0])
}

const expandedNode = computed(() => findNode(tree.value, expandedId.value))

const childCategories = computed(() => {
  const node = expandedNode.value
  if (!node?.children?.length) return []
  return node.children
})

const activeLeafNode = computed(() => findNode(tree.value, activeLeafId.value))

const selectedKeys = computed(() => {
  const set = new Set()
  for (const part of splitPromptTokens(props.modelValue)) {
    const k = lookupKeyForVocabulary(part).toLowerCase()
    if (k) set.add(k)
  }
  return set
})

function isTagSelected(item) {
  const k = lookupKeyForVocabulary(item.value).toLowerCase()
  return k && selectedKeys.value.has(k)
}

function isActiveLeaf() {
  return activeLeafNode.value && isLeaf(activeLeafNode.value)
}

async function loadTree() {
  loadingTree.value = true
  errorMsg.value = ''
  try {
    const res = await api.vocabularyCategoryTree()
    tree.value = res.tree || []
    hasLoaded.value = true
    if (!expandedId.value && tree.value[0]?.id) {
      openCategory(tree.value[0].id)
    }
  } catch (e) {
    errorMsg.value = e.message || '加载标签分类失败'
  } finally {
    loadingTree.value = false
  }
}

async function ensureLoaded() {
  if (hasLoaded.value || loadingTree.value) return
  await loadTree()
}

async function loadPrompts(reset = true) {
  if (!activeLeafId.value || !isActiveLeaf()) {
    prompts.value = []
    listTotal.value = 0
    return
  }
  if (reset) listOffset.value = 0
  listLoading.value = true
  errorMsg.value = ''
  try {
    const res = await api.vocabularyListPrompts(activeLeafId.value, {
      offset: listOffset.value,
      limit: LIST_LIMIT,
    })
    const items = res.items || []
    prompts.value = reset ? items : [...prompts.value, ...items]
    listTotal.value = res.total ?? 0
  } catch (e) {
    errorMsg.value = e.message || '加载标签失败'
  } finally {
    listLoading.value = false
  }
}

function toggleExpanded() {
  if (props.disabled) return
  expanded.value = !expanded.value
  if (expanded.value) void ensureLoaded()
}

function openCategory(id) {
  if (expandedId.value === id) {
    expandedId.value = ''
    activeLeafId.value = ''
    prompts.value = []
    return
  }
  expandedId.value = id
  const node = findNode(tree.value, id)
  activeLeafId.value = defaultLeafId(node)
}

function selectChild(id) {
  const node = findNode(tree.value, id)
  activeLeafId.value = isLeaf(node) ? id : defaultLeafId(node)
}

function loadMore() {
  if (prompts.value.length >= listTotal.value || listLoading.value) return
  listOffset.value += LIST_LIMIT
  loadPrompts(false)
}

function onPick(item) {
  if (props.disabled) return
  emit('select', item.value)
}

function tagButtonTitle(item) {
  return isTagSelected(item) ? `${item.value}（再次点击移除）` : item.value
}

watch(activeLeafId, () => {
  if (!expanded.value || !hasLoaded.value) return
  if (activeLeafId.value && isActiveLeaf()) loadPrompts(true)
  else {
    prompts.value = []
    listTotal.value = 0
  }
})
</script>

<template>
  <div
    data-prompt-tag-picker
    class="rounded-md border border-border/80 bg-muted/20 overflow-hidden"
  >
    <button
      type="button"
      class="flex w-full items-center justify-between gap-2 px-2.5 py-2 text-left transition-colors hover:bg-muted/40 disabled:pointer-events-none disabled:opacity-50"
      :disabled="disabled"
      :aria-expanded="expanded"
      @click="toggleExpanded"
    >
      <span class="text-xs font-medium text-foreground">标签库</span>
      <span class="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
        <Loader2 v-if="expanded && loadingTree" class="h-3 w-3 animate-spin" />
        <span v-else-if="expanded && hasLoaded && tree.length">{{ tree.length }} 个分类</span>
        <span v-else-if="!expanded">点击展开</span>
        <ChevronDown
          class="h-3.5 w-3.5 shrink-0 transition-transform text-muted-foreground"
          :class="expanded ? 'rotate-180' : ''"
        />
      </span>
    </button>

    <div
      v-show="expanded"
      class="space-y-2 border-t border-border/60 p-2"
    >
      <p
        v-if="errorMsg"
        class="rounded border border-destructive/40 bg-destructive/10 px-2 py-1 text-[11px] text-destructive"
      >
        {{ errorMsg }}
      </p>

      <div
        v-if="loadingTree"
        class="flex items-center gap-2 py-3 text-xs text-muted-foreground justify-center"
      >
        <Loader2 class="h-3.5 w-3.5 animate-spin" />
        加载分类…
      </div>

      <template v-else-if="tree.length">
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="cat in tree"
            :key="cat.id"
            type="button"
            class="inline-flex items-center gap-0.5 rounded-md border px-2.5 py-1 text-xs transition-colors"
            :class="
              cn(
                expandedId === cat.id
                  ? 'border-primary bg-primary/15 text-primary font-medium'
                  : 'border-border/70 bg-background/80 text-foreground hover:bg-muted/60',
                disabled && 'pointer-events-none opacity-50',
              )
            "
            :title="cat.name"
            :disabled="disabled"
            @click="openCategory(cat.id)"
          >
            <span class="max-w-[8rem] truncate">{{ cat.name }}</span>
            <ChevronDown
              class="h-3 w-3 shrink-0 transition-transform"
              :class="expandedId === cat.id ? 'rotate-180' : ''"
            />
          </button>
        </div>

        <div
          v-if="expandedNode"
          class="space-y-2 rounded-md border border-dashed border-border/60 bg-background/60 p-2"
        >
          <div v-if="childCategories.length" class="flex flex-wrap gap-1">
            <button
              v-for="child in childCategories"
              :key="child.id"
              type="button"
              class="rounded px-2 py-0.5 text-[11px] transition-colors"
              :class="
                containsDescendant(child, activeLeafId)
                  ? 'bg-primary/15 text-primary font-medium'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
              "
              :disabled="disabled"
              @click="selectChild(child.id)"
            >
              {{ child.name }}
            </button>
          </div>

          <p
            v-else-if="isActiveLeaf() && activeLeafNode"
            class="text-[11px] text-muted-foreground"
          >
            {{ activeLeafNode.name }}
            <span class="text-foreground/70">· {{ listTotal }} 个标签</span>
          </p>

          <div
            v-if="listLoading && !prompts.length"
            class="flex items-center gap-2 py-4 text-xs text-muted-foreground justify-center"
          >
            <Loader2 class="h-3.5 w-3.5 animate-spin" />
            加载标签…
          </div>

          <div
            v-else-if="prompts.length"
            class="flex max-h-48 flex-wrap gap-2 overflow-y-auto pr-0.5"
          >
            <button
              v-for="item in prompts"
              :key="`${item.categoryId}-${item.value}`"
              type="button"
              class="rounded-md border px-2.5 py-1.5 text-left text-xs leading-snug transition-colors max-w-full"
              :class="
                isTagSelected(item)
                  ? 'border-primary/50 bg-primary/20 text-primary'
                  : 'border-border/60 bg-muted/30 text-foreground hover:border-primary/40 hover:bg-primary/10'
              "
              :title="tagButtonTitle(item)"
              :disabled="disabled"
              @click="onPick(item)"
            >
              <span class="block font-medium truncate">{{ item.name || item.value }}</span>
              <span
                v-if="item.name && item.name !== item.value"
                class="block font-mono text-[11px] text-muted-foreground truncate mt-0.5"
              >
                {{ item.value }}
              </span>
            </button>
          </div>

          <p
            v-else-if="!listLoading && isActiveLeaf()"
            class="py-3 text-center text-[11px] text-muted-foreground"
          >
            该分类下暂无标签
          </p>

          <button
            v-if="prompts.length < listTotal"
            type="button"
            class="mx-auto block text-[11px] text-primary hover:underline disabled:opacity-50"
            :disabled="listLoading || disabled"
            @click="loadMore"
          >
            {{ listLoading ? '加载中…' : `加载更多（${prompts.length}/${listTotal}）` }}
          </button>
        </div>
      </template>

      <p
        v-else-if="hasLoaded && !loadingTree"
        class="py-2 text-center text-xs text-muted-foreground"
      >
        暂无标签分类，请先在「Tag 显示管理」中配置
      </p>
    </div>
  </div>
</template>
