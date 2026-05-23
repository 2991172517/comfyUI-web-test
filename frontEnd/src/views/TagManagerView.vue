<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowLeft, Loader2, Plus, RefreshCw, Search, Trash2, X } from 'lucide-vue-next'
import PageAlert from '@/components/layout/PageAlert.vue'
import TagCategoryTree from '@/components/prompt/TagCategoryTree.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import { api } from '@/api/client.js'

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
const defaultWeight = ref(1)
const settingsSaving = ref(false)

const showAdd = ref(false)
const addValue = ref('')
const addName = ref('')
const addBusy = ref(false)
const errorMsg = ref('')

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

const listTitle = computed(() => {
  if (globalSearchMode.value && searchQ.value.trim()) {
    return `全局搜索「${searchQ.value.trim()}」`
  }
  return selectedName.value || '请选择分类'
})

function mapSuggestItem(item) {
  return {
    value: item.insertText || item.insert_text || '',
    name: item.label || '',
    categoryId: item.categoryId || item.category_id || '',
    categoryPath: item.category || null,
    sourceId: item.sourceId || item.source_id || '',
  }
}

async function loadTree() {
  loadingTree.value = true
  errorMsg.value = ''
  try {
    const res = await api.vocabularyCategoryTree()
    rootName.value = res.rootCategoryName || '标签库'
    tree.value = res.tree || []
    if (!selectedCategoryId.value && tree.value[0]?.id) {
      selectedCategoryId.value = tree.value[0].id
    }
  } catch (e) {
    errorMsg.value = e.message || '加载分类失败'
  } finally {
    loadingTree.value = false
  }
}

async function loadSettings() {
  try {
    const res = await api.vocabularyGetSettings()
    defaultWeight.value = res.defaultWeight ?? 1
  } catch {
    /* ignore */
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
    const items = (res.items || []).map(mapSuggestItem)
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
    prompts.value = resetOffset ? res.items || [] : [...prompts.value, ...(res.items || [])]
    total.value = res.total ?? 0
  } catch (e) {
    errorMsg.value = e.message || '加载词条失败'
  } finally {
    listLoading.value = false
  }
}

async function saveDefaultWeight() {
  settingsSaving.value = true
  try {
    const res = await api.vocabularyUpdateSettings(Number(defaultWeight.value))
    defaultWeight.value = res.defaultWeight
  } catch (e) {
    errorMsg.value = e.message || '保存默认权重失败'
  } finally {
    settingsSaving.value = false
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
  if (!confirm(`删除词条「${item.name || item.value}」？`)) return
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

watch(selectedCategoryId, () => {
  if (selectedCategoryId.value && !searchQ.value.trim()) loadPrompts(true)
})

onMounted(async () => {
  await Promise.all([loadTree(), loadSettings()])
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
        <p class="text-xs text-muted-foreground">
          分类来自 manifest（{{ rootName }}），用户新增/删除保存在服务端覆盖文件
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        :disabled="loadingTree"
        @click="loadTree"
      >
        <RefreshCw class="mr-1 h-3.5 w-3.5" />
        刷新分类
      </Button>
    </div>

    <div class="relative">
      <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        v-model="searchQ"
        placeholder="搜索英文 tag 或中文名称（全库匹配，最多 50 条）…"
        class="h-10 pl-9 pr-9 text-sm"
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

    <p
      v-if="errorMsg"
      class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
    >
      {{ errorMsg }}
    </p>

    <div
      class="flex flex-col gap-4 rounded-lg border border-border bg-card/40 p-3 md:flex-row md:min-h-[32rem]"
    >
      <aside class="w-full shrink-0 md:w-56 lg:w-64">
        <p class="mb-2 text-xs font-medium text-muted-foreground">分类</p>
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
        <div
          v-else-if="!filteredTree.length"
          class="text-xs text-muted-foreground"
        >
          无匹配分类
        </div>
        <div
          v-else
          class="max-h-[28rem] overflow-y-auto pr-1"
        >
          <TagCategoryTree
            :nodes="filteredTree"
            :selected-id="selectedCategoryId"
            @select="onSelectCategory"
          />
        </div>
      </aside>

      <main class="min-w-0 flex-1 flex flex-col gap-3">
        <div
          class="flex flex-wrap items-end gap-3 rounded-md border border-border/60 bg-muted/20 p-3"
        >
          <label class="text-xs">
            <span class="text-muted-foreground">默认权重（新建 tag 参考）</span>
            <Input
              v-model.number="defaultWeight"
              type="number"
              step="0.05"
              min="0.05"
              max="2"
              class="mt-1 h-8 w-24 text-xs"
            />
          </label>
          <Button
            size="sm"
            variant="secondary"
            :disabled="settingsSaving"
            @click="saveDefaultWeight"
          >
            保存
          </Button>
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

        <ul
          v-else
          class="flex-1 divide-y divide-border/60 overflow-y-auto rounded-md border border-border/50 max-h-[22rem]"
        >
          <li
            v-for="item in prompts"
            :key="`${item.categoryId}-${item.value}`"
            class="flex items-start gap-2 px-3 py-2 text-xs hover:bg-muted/30"
          >
            <div class="min-w-0 flex-1">
              <div class="font-medium text-foreground">
                {{ item.name || item.value }}
              </div>
              <div class="font-mono text-[10px] text-muted-foreground break-all">
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
            <Button
              variant="ghost"
              size="icon"
              class="h-7 w-7 shrink-0 text-destructive"
              aria-label="删除"
              @click="removePrompt(item)"
            >
              <Trash2 class="h-3.5 w-3.5" />
            </Button>
          </li>
          <li
            v-if="!prompts.length && !listLoading"
            class="px-3 py-8 text-center text-xs text-muted-foreground"
          >
            {{ globalSearchMode ? '未找到匹配词条' : '该分类下暂无词条' }}
          </li>
        </ul>

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
