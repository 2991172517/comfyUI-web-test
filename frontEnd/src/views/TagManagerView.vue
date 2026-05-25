<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ArrowLeft,
  Heart,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  ThumbsDown,
  Trash2,
  X,
} from 'lucide-vue-next'
import PageAlert from '@/components/layout/PageAlert.vue'
import TagCategoryTree from '@/components/prompt/TagCategoryTree.vue'
import VocabularyMergePanel from '@/components/prompt/VocabularyMergePanel.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import { cn } from '@/lib/utils'
import { api } from '@/api/client.js'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'

const { confirmDelete } = useConfirmDialog()
const loadingTree = ref(true)
const tree = ref([])
const rootName = ref('标签库')
const selectedCategoryId = ref('')
const prompts = ref([])
const total = ref(0)
const offset = ref(0)
const limit = 80
const searchQ = ref('')
const categoryFilterQ = ref('')
const globalSearchMode = ref(false)
const listLoading = ref(false)
const preferenceBusyKey = ref('')
const expandedCategoryIds = ref({})

const showAdd = ref(false)
const addValue = ref('')
const addName = ref('')
const addBusy = ref(false)
const errorMsg = ref('')

const PREF_ORDER = { like: 0, dislike: 2 }

function findNode(nodes, id) {
  for (const n of nodes || []) {
    if (n.id === id) return n
    const hit = findNode(n.children, id)
    if (hit) return hit
  }
  return null
}

function filterTree(nodes, query) {
  const q = String(query || '').trim().toLowerCase()
  if (!q) return nodes || []
  const out = []
  for (const n of nodes || []) {
    const children = filterTree(n.children, q)
    const nameMatch = String(n.name || '').toLowerCase().includes(q)
    if (nameMatch || children.length) {
      out.push({ ...n, children })
    }
  }
  return out
}

const filteredTree = computed(() => filterTree(tree.value, categoryFilterQ.value))

const selectedName = computed(() => {
  const n = findNode(tree.value, selectedCategoryId.value)
  return n?.name || ''
})

const selectedNode = computed(() => findNode(tree.value, selectedCategoryId.value))

const listTitle = computed(() => {
  if (globalSearchMode.value && searchQ.value.trim()) {
    return `全局搜索「${searchQ.value.trim()}」`
  }
  return selectedName.value || '请选择分类'
})

function sortByPreference(items) {
  return [...items].sort((a, b) => {
    const ao = PREF_ORDER[a.preference] ?? 1
    const bo = PREF_ORDER[b.preference] ?? 1
    if (ao !== bo) return ao - bo
    const an = (a.name || a.value || '').toLowerCase()
    const bn = (b.name || b.value || '').toLowerCase()
    return an.localeCompare(bn)
  })
}

function mapSuggestItem(item) {
  return {
    value: item.insertText || item.insert_text || '',
    name: item.label || '',
    categoryId: item.categoryId || item.category_id || '',
    categoryPath: item.category || null,
    sourceId: item.sourceId || item.source_id || '',
    preference: item.preference ?? null,
  }
}

function findPathToCategory(nodes, id, path = []) {
  for (const n of nodes || []) {
    const next = [...path, n.id]
    if (n.id === id) return next
    const hit = findPathToCategory(n.children, id, next)
    if (hit) return hit
  }
  return null
}

function expandPathToCategory(id) {
  const path = findPathToCategory(tree.value, id)
  if (!path?.length) return
  const next = { ...expandedCategoryIds.value }
  for (const cid of path.slice(0, -1)) {
    next[cid] = true
  }
  expandedCategoryIds.value = next
}

function toggleCategoryExpand(id) {
  expandedCategoryIds.value = {
    ...expandedCategoryIds.value,
    [id]: !expandedCategoryIds.value[id],
  }
}

function itemKey(item) {
  return `${item.categoryId}::${item.value}`
}

async function loadTree() {
  loadingTree.value = true
  errorMsg.value = ''
  try {
    const res = await api.vocabularyCategoryTree()
    rootName.value = res.rootCategoryName || '标签库'
    tree.value = res.tree || []
    if (selectedCategoryId.value && !findNode(tree.value, selectedCategoryId.value)) {
      selectedCategoryId.value = ''
    }
    if (!selectedCategoryId.value && tree.value[0]?.id) {
      selectedCategoryId.value = tree.value[0].id
    }
  } catch (e) {
    errorMsg.value = e.message || '加载分类失败'
  } finally {
    loadingTree.value = false
  }
}

async function loadGlobalSearch() {
  const q = searchQ.value.trim()
  if (!q) {
    globalSearchMode.value = false
    await loadPrompts(true)
    return
  }
  listLoading.value = true
  errorMsg.value = ''
  globalSearchMode.value = true
  offset.value = 0
  try {
    const res = await api.vocabularySuggest(q, { limit: 50 })
    const items = sortByPreference((res.items || []).map(mapSuggestItem))
    prompts.value = items
    total.value = items.length
  } catch (e) {
    errorMsg.value = e.message || '搜索失败'
  } finally {
    listLoading.value = false
  }
}

async function loadPrompts(resetOffset = true) {
  const q = searchQ.value.trim()
  if (q) {
    await loadGlobalSearch()
    return
  }
  globalSearchMode.value = false
  if (!selectedCategoryId.value) return
  if (resetOffset) offset.value = 0
  listLoading.value = true
  errorMsg.value = ''
  try {
    const res = await api.vocabularyListPrompts(selectedCategoryId.value, {
      q: '',
      offset: offset.value,
      limit,
    })
    const items = res.items || []
    prompts.value = resetOffset ? items : [...prompts.value, ...items]
    total.value = res.total ?? 0
  } catch (e) {
    errorMsg.value = e.message || '加载词条失败'
  } finally {
    listLoading.value = false
  }
}

async function submitAdd() {
  if (!addValue.value.trim() || !selectedCategoryId.value) return
  addBusy.value = true
  try {
    await api.vocabularyCreatePrompt({
      categoryId: selectedCategoryId.value,
      value: addValue.value.trim(),
      name: addName.value.trim() || addValue.value.trim(),
    })
    showAdd.value = false
    addValue.value = ''
    addName.value = ''
    await loadPrompts(true)
  } catch (e) {
    errorMsg.value = e.message || '添加失败'
  } finally {
    addBusy.value = false
  }
}

async function removePrompt(item) {
  if (!(await confirmDelete({ message: `确定删除 tag「${item.name || item.value}」？此操作不可撤销。` }))) {
    return
  }
  const categoryId = item.categoryId || selectedCategoryId.value
  if (!categoryId) {
    errorMsg.value = '无法确定词条所属分类'
    return
  }
  try {
    await api.vocabularyDeletePrompt({
      categoryId,
      value: item.value,
    })
    await loadPrompts(true)
  } catch (e) {
    errorMsg.value = e.message || '删除失败'
  }
}

async function removeCategory(node) {
  if (!node?.id) return
  const name = node?.name || node?.id || '该分类'
  let countHint = ''
  try {
    const res = await api.vocabularyCategoryCount(node.id)
    countHint = res.total ? `（含约 ${res.total} 个 tag` : ''
    if (node.children?.length) {
      countHint += countHint ? '，含子分类）' : '（含子分类）'
    } else if (countHint) {
      countHint += '）'
    }
  } catch {
    /* ignore count */
  }

  if (
    !(await confirmDelete({
      title: '删除 tag 组',
      message: `确定删除分类「${name}」${countHint}？\n\n将从标签选择器中隐藏该组及其子分类，已写入提示词的 tag 文本不会自动移除。`,
    }))
  ) {
    return
  }

  try {
    await api.vocabularyDeleteCategory(node.id)
    if (selectedCategoryId.value === node.id) {
      selectedCategoryId.value = ''
    }
    await loadTree()
    prompts.value = []
    total.value = 0
  } catch (e) {
    errorMsg.value = e.message || '删除分类失败'
  }
}

async function setPreference(item, preference) {
  const categoryId = item.categoryId || selectedCategoryId.value
  if (!categoryId) return

  const current = item.preference || null
  let next = preference
  if (current === preference) next = 'neutral'

  const key = itemKey(item)
  preferenceBusyKey.value = key
  errorMsg.value = ''
  try {
    const res = await api.vocabularySetTagPreference({
      categoryId,
      value: item.value,
      preference: next,
    })
    const applied = res.preference ?? null
    prompts.value = sortByPreference(
      prompts.value.map((p) =>
        itemKey(p) === key ? { ...p, preference: applied } : p,
      ),
    )
  } catch (e) {
    errorMsg.value = e.message || '保存偏好失败'
  } finally {
    preferenceBusyKey.value = ''
  }
}

function onSelectCategory(id) {
  selectedCategoryId.value = id
  if (searchQ.value.trim()) {
    searchQ.value = ''
  }
}

function loadMore() {
  if (globalSearchMode.value || prompts.value.length >= total.value) return
  offset.value += limit
  loadPrompts(false)
}

function clearSearch() {
  searchQ.value = ''
}

let searchTimer
watch(searchQ, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadPrompts(true), 300)
})

watch(selectedCategoryId, (id) => {
  if (selectedCategoryId.value && !searchQ.value.trim()) loadPrompts(true)
  if (id) expandPathToCategory(id)
})

watch(tree, () => {
  if (selectedCategoryId.value) expandPathToCategory(selectedCategoryId.value)
})

onMounted(async () => {
  await loadTree()
})
</script>

<template>
  <div class="mx-auto flex max-w-6xl flex-col gap-4">
    <PageAlert />

    <div class="flex flex-wrap items-center justify-between gap-2">
      <div>
        <RouterLink
          to="/settings/prompts"
          class="mb-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft class="h-3.5 w-3.5" />
          返回提示词设置
        </RouterLink>
        <h1 class="text-base font-semibold text-foreground">
          Tag 显示管理
        </h1>
        <p class="text-xs text-muted-foreground">
          设置 tag 喜欢/不喜欢（影响排序：喜欢靠前、不喜欢靠后），可删除单个 tag 或整组分类
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        :disabled="loadingTree"
        @click="loadTree"
      >
        <RefreshCw class="mr-1 h-3.5 w-3.5" />
        刷新
      </Button>
    </div>

    <p
      v-if="errorMsg"
      class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
    >
      {{ errorMsg }}
    </p>

    <VocabularyMergePanel @merged="loadTree" />

    <div
      class="flex min-h-[20rem] max-h-[calc(100dvh-13rem)] flex-col gap-4 overflow-hidden rounded-lg border border-border bg-card/40 p-3 md:flex-row md:min-h-[28rem] md:items-stretch"
    >
      <aside
        class="flex w-full max-h-[42vh] shrink-0 flex-col min-h-0 md:max-h-none md:h-full md:w-56 lg:w-64"
      >
        <p class="mb-2 text-xs font-medium text-muted-foreground">
          分类（hover 可删组）
        </p>
        <Input
          v-model="categoryFilterQ"
          placeholder="筛选分类名称…"
          class="mb-2 h-8 text-xs"
        />
        <div
          v-if="loadingTree"
          class="flex items-center gap-2 text-xs text-muted-foreground"
        >
          <Loader2 class="h-4 w-4 animate-spin" />
          加载中…
        </div>
        <p
          v-else-if="!filteredTree.length"
          class="text-xs text-muted-foreground"
        >
          无匹配分类
        </p>
        <div
          v-else
          class="min-h-0 flex-1 overflow-y-auto pr-1"
        >
          <TagCategoryTree
            :nodes="filteredTree"
            :selected-id="selectedCategoryId"
            :expanded-ids="expandedCategoryIds"
            manageable
            @select="onSelectCategory"
            @delete="removeCategory"
            @toggle-expand="toggleCategoryExpand"
          />
        </div>
      </aside>

      <main class="flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-hidden">
        <div
          class="rounded-md border border-border/60 bg-muted/20 p-3"
        >
          <label class="block text-xs text-muted-foreground mb-1.5">搜索 tag</label>
          <div class="relative">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              v-model="searchQ"
              placeholder="英文 tag 或中文名称（全库匹配，最多 50 条）…"
              class="h-9 pl-9 pr-9 text-sm"
            />
            <button
              v-if="searchQ"
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="清空搜索"
              @click="clearSearch"
            >
              <X class="h-4 w-4" />
            </button>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <h2 class="text-sm font-medium flex-1 truncate">
            {{ listTitle }}
            <span class="text-muted-foreground font-normal">
              （{{ total }} 条）
            </span>
          </h2>
          <span
            v-if="globalSearchMode"
            class="text-[11px] text-muted-foreground"
          >
            全库搜索中，点击左侧分类可退出
          </span>
          <Button
            v-if="selectedCategoryId && !globalSearchMode"
            size="sm"
            variant="outline"
            class="text-destructive hover:text-destructive"
            @click="removeCategory(selectedNode)"
          >
            <Trash2 class="h-3.5 w-3.5 mr-1" />
            删除此组
          </Button>
          <Button
            size="sm"
            :disabled="!selectedCategoryId || globalSearchMode"
            @click="showAdd = true"
          >
            <Plus class="h-3.5 w-3.5 mr-1" />
            添加 Tag
          </Button>
        </div>

        <div
          v-if="showAdd"
          class="rounded-md border border-dashed border-primary/40 bg-primary/5 p-3 space-y-2"
        >
          <Input
            v-model="addValue"
            placeholder="英文 value（写入提示词）"
            class="h-8 text-xs font-mono"
          />
          <Input
            v-model="addName"
            placeholder="中文名称（可选）"
            class="h-8 text-xs"
          />
          <div class="flex gap-2">
            <Button
              size="sm"
              :disabled="addBusy || !addValue.trim()"
              @click="submitAdd"
            >
              确认添加
            </Button>
            <Button
              size="sm"
              variant="ghost"
              @click="showAdd = false"
            >
              取消
            </Button>
          </div>
        </div>

        <div
          v-if="listLoading && !prompts.length"
          class="flex flex-1 items-center justify-center text-xs text-muted-foreground"
        >
          <Loader2 class="mr-2 h-4 w-4 animate-spin" />
          {{ globalSearchMode ? '搜索中…' : '加载词条…' }}
        </div>

        <div
          v-else
          class="flex flex-1 min-h-0 flex-wrap content-start gap-2 overflow-y-auto rounded-md border border-border/50 p-3"
        >
          <article
            v-for="item in prompts"
            :key="itemKey(item)"
            :class="
              cn(
                'inline-flex max-w-full flex-col rounded-lg border px-2.5 py-2 text-xs transition-colors',
                item.preference === 'like'
                  ? 'border-emerald-500/35 bg-emerald-500/5'
                  : item.preference === 'dislike'
                    ? 'border-orange-500/35 bg-orange-500/5 opacity-90'
                    : 'border-border/60 bg-muted/20 hover:bg-muted/35',
              )
            "
          >
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-1">
                <span class="font-medium text-foreground leading-snug">
                  {{ item.name || item.value }}
                </span>
                <span
                  v-if="item.preference === 'like'"
                  class="rounded bg-emerald-500/15 px-1 text-[10px] text-emerald-600"
                >
                  喜欢
                </span>
                <span
                  v-else-if="item.preference === 'dislike'"
                  class="rounded bg-orange-500/15 px-1 text-[10px] text-orange-600"
                >
                  不喜欢
                </span>
              </div>
              <div
                v-if="item.name && item.name !== item.value"
                class="font-mono text-[11px] text-muted-foreground break-all leading-snug mt-0.5"
              >
                {{ item.value }}
              </div>
              <p
                v-if="globalSearchMode && item.categoryPath"
                class="mt-0.5 text-[10px] text-muted-foreground truncate"
                :title="item.categoryPath"
              >
                {{ item.categoryPath }}
              </p>
              <span
                v-if="item.sourceId === 'user'"
                class="mt-0.5 inline-block rounded bg-primary/10 px-1 text-[10px] text-primary"
              >
                用户添加
              </span>
            </div>

            <div class="mt-2 flex shrink-0 items-center gap-0.5">
              <Button
                variant="ghost"
                size="icon"
                class="h-7 w-7"
                :class="item.preference === 'like' ? 'text-emerald-600' : 'text-muted-foreground'"
                :disabled="preferenceBusyKey === itemKey(item)"
                aria-label="喜欢"
                :title="item.preference === 'like' ? '取消喜欢' : '标记为喜欢'"
                @click="setPreference(item, 'like')"
              >
                <Heart
                  class="h-3.5 w-3.5"
                  :class="item.preference === 'like' ? 'fill-current' : ''"
                />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                class="h-7 w-7"
                :class="item.preference === 'dislike' ? 'text-orange-600' : 'text-muted-foreground'"
                :disabled="preferenceBusyKey === itemKey(item)"
                aria-label="不喜欢"
                :title="item.preference === 'dislike' ? '取消不喜欢' : '标记为不喜欢'"
                @click="setPreference(item, 'dislike')"
              >
                <ThumbsDown
                  class="h-3.5 w-3.5"
                  :class="item.preference === 'dislike' ? 'fill-current' : ''"
                />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                class="h-7 w-7 text-destructive"
                aria-label="删除 tag"
                @click="removePrompt(item)"
              >
                <Trash2 class="h-3.5 w-3.5" />
              </Button>
            </div>
          </article>
          <p
            v-if="!prompts.length && !listLoading"
            class="w-full py-8 text-center text-xs text-muted-foreground"
          >
            {{ globalSearchMode ? '未找到匹配词条' : '该分类下暂无词条' }}
          </p>
        </div>

        <Button
          v-if="!globalSearchMode && prompts.length < total"
          variant="outline"
          size="sm"
          class="self-center"
          :disabled="listLoading"
          @click="loadMore"
        >
          加载更多（{{ prompts.length }}/{{ total }}）
        </Button>
      </main>
    </div>
  </div>
</template>
