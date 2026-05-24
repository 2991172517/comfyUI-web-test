<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { openModelImportModal } from '@/composables/useModelImportModal.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Badge from '@/components/ui/Badge.vue'
import ModelPreviewMedia from '@/components/models/ModelPreviewMedia.vue'
import ModelImportPanel from '@/components/models/ModelImportPanel.vue'
import {
  hasCivitaiApiKey,
  loadCivitaiApiKey,
} from '@/composables/useCivitaiApiKey.js'
import { cn } from '@/lib/utils'
import { staggerReveal } from '@/lib/gsap/motion.js'
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Heart,
  Link2,
  Search,
  Star,
  Tag,
  Trash2,
  X,
} from 'lucide-vue-next'

const app = useAppStore()

/** 常用标签快捷筛选（C 站模型 tag） */
const QUICK_TAGS = [
  'anime',
  'character',
  'style',
  'realistic',
  'fantasy',
  'sdxl',
  'pony',
  'illustrious',
  'flux',
  'woman',
  'man',
  'clothing',
]

/** browse | favorites */
const mainTab = ref('browse')
/** sfw=蓝站 | nsfw=红站 | all */
const contentMode = ref('sfw')

const presets = ref([])
const activePresetId = ref('hot-checkpoint')
const civitaiApiKey = ref(loadCivitaiApiKey())
const favoriteIds = ref(new Set())
const favoriteItems = ref([])
const favoritesLoading = ref(false)
const searchQuery = ref('')
const activeTag = ref('')
const tagSearchInput = ref('')
const tagSuggestions = ref([])
const tagSuggestLoading = ref(false)
let tagSuggestTimer = null

const sort = ref('Most Downloaded')
const period = ref('Month')
const types = ref('Checkpoint')
const page = ref(1)
const limit = ref(24)

/** 每页请求用的 cursor：index 0 = 首页（空串） */
const cursorByPage = ref([''])
/** 避免上一页重复请求 */
const pageCache = ref({})

const items = ref([])
const metadata = ref({})
const loading = ref(false)
const selected = ref(null)
const importUrl = ref('')

const canGoPrev = computed(() => page.value > 1)
const canGoNext = computed(() => !!metadata.value?.hasMore && !!metadata.value?.nextCursor)
const hasApiKey = computed(() => hasCivitaiApiKey(civitaiApiKey.value))
const displayItems = computed(() =>
  mainTab.value === 'favorites' ? favoriteItems.value : items.value,
)
const civitaiGridRef = ref(null)

async function revealCivitaiGrid() {
  await nextTick()
  const els = civitaiGridRef.value?.querySelectorAll('[data-stagger-item]')
  if (els?.length) staggerReveal(els)
}

watch(() => displayItems.value.length, revealCivitaiGrid)
watch(mainTab, revealCivitaiGrid)
const contentModeHint = computed(() => {
  if (contentMode.value === 'nsfw') {
    return '红 C 站（NSFW）：官方 API 仍走 civitai.com，通过 nsfw=true 拉取；链接指向 civitai.red'
  }
  if (contentMode.value === 'all') {
    return '全部：不向 API 传 nsfw 筛选（仍以 SFW 为主）'
  }
  return '蓝 C 站（SFW）：nsfw=false'
})

const pageLabel = computed(() => {
  const more = canGoNext.value ? '+' : '（末页）'
  return `第 ${page.value} 页${more}`
})

function filterCacheKey(cursor) {
  return JSON.stringify({
    c: cursor || '',
    types: types.value,
    sort: sort.value,
    period: period.value,
    q: searchQuery.value.trim(),
    tag: activeTag.value,
    limit: limit.value,
    content: contentMode.value,
  })
}

function syncFavoriteIds(list) {
  favoriteIds.value = new Set((list || []).map((x) => x.id))
}

async function loadFavorites() {
  civitaiApiKey.value = loadCivitaiApiKey()
  if (!hasCivitaiApiKey(civitaiApiKey.value)) {
    favoriteItems.value = []
    syncFavoriteIds([])
    return
  }
  favoritesLoading.value = true
  try {
    const res = await api.listCivitaiModelFavorites()
    favoriteItems.value = res.items || []
    syncFavoriteIds(favoriteItems.value)
  } catch {
    favoriteItems.value = []
    syncFavoriteIds([])
  } finally {
    favoritesLoading.value = false
  }
}

function isFavorited(modelId) {
  return favoriteIds.value.has(modelId)
}

async function toggleFavorite(item, ev) {
  ev?.stopPropagation?.()
  civitaiApiKey.value = loadCivitaiApiKey()
  if (!hasCivitaiApiKey(civitaiApiKey.value)) {
    app.setMessage('请先在右侧导入面板保存 Civitai API Key，再收藏模型', true)
    return
  }
  const id = item.id
  try {
    if (isFavorited(id)) {
      await api.removeCivitaiModelFavorite(id)
      favoriteIds.value.delete(id)
      favoriteIds.value = new Set(favoriteIds.value)
      favoriteItems.value = favoriteItems.value.filter((x) => x.id !== id)
      app.setMessage('已取消收藏')
    } else {
      const res = await api.addCivitaiModelFavorite(item)
      favoriteIds.value.add(id)
      favoriteIds.value = new Set(favoriteIds.value)
      if (res.item) {
        favoriteItems.value = [
          res.item,
          ...favoriteItems.value.filter((x) => x.id !== id),
        ]
      }
      app.setMessage('已加入收藏')
    }
  } catch (e) {
    app.setMessage(e.message, true)
  }
}

async function removeFavoriteItem(item, ev) {
  ev?.stopPropagation?.()
  await toggleFavorite(item, ev)
}

function switchMainTab(tab) {
  mainTab.value = tab
  if (tab === 'favorites') {
    loadFavorites()
  }
}

function onContentModeChange() {
  if (mainTab.value !== 'browse') return
  resetPagination()
  load()
}

function resetPagination() {
  page.value = 1
  cursorByPage.value = ['']
  pageCache.value = {}
}

function applyPreset(p) {
  activePresetId.value = p.id
  types.value = p.types || 'Checkpoint'
  sort.value = p.sort || 'Most Downloaded'
  period.value = p.period || 'Month'
  searchQuery.value = p.query || ''
  activeTag.value = p.tag || ''
  tagSearchInput.value = activeTag.value
  resetPagination()
  load()
}

function selectTag(name) {
  const t = (name || '').trim()
  activeTag.value = t
  tagSearchInput.value = t
  tagSuggestions.value = []
  activePresetId.value = ''
  resetPagination()
  load()
}

function clearTag() {
  activeTag.value = ''
  tagSearchInput.value = ''
  tagSuggestions.value = []
  resetPagination()
  load()
}

async function fetchTagSuggestions(q) {
  const text = (q || '').trim()
  if (text.length < 2) {
    tagSuggestions.value = []
    return
  }
  tagSuggestLoading.value = true
  try {
    const res = await api.searchCivitaiTags({ query: text, limit: 20 })
    tagSuggestions.value = res.tags || []
  } catch {
    tagSuggestions.value = []
  } finally {
    tagSuggestLoading.value = false
  }
}

function onTagInput() {
  if (tagSuggestTimer) clearTimeout(tagSuggestTimer)
  tagSuggestTimer = setTimeout(() => {
    fetchTagSuggestions(tagSearchInput.value)
  }, 320)
}

function applyTagFromInput() {
  selectTag(tagSearchInput.value)
}

function selectCard(item) {
  selected.value = item
  importUrl.value = item.pageUrl || ''
}

function openInModal() {
  if (!importUrl.value) return
  openModelImportModal(importUrl.value)
}

async function load() {
  const cursor = cursorByPage.value[page.value - 1] ?? ''
  const cacheKey = filterCacheKey(cursor)
  const cached = pageCache.value[cacheKey]
  if (cached) {
    items.value = cached.items
    metadata.value = cached.metadata
    if (selected.value) {
      const still = items.value.find((x) => x.id === selected.value.id)
      if (still) selected.value = still
      else selected.value = null
    }
    return
  }

  loading.value = true
  try {
    const res = await api.browseCivitaiModels({
      types: types.value,
      sort: sort.value,
      period: period.value,
      query: searchQuery.value.trim() || undefined,
      tag: activeTag.value || undefined,
      cursor: cursor || undefined,
      page: page.value,
      limit: limit.value,
      content: contentMode.value,
    })
    items.value = res.items || []
    metadata.value = res.metadata || {}
    pageCache.value[cacheKey] = {
      items: items.value,
      metadata: metadata.value,
    }
    if (selected.value) {
      const still = items.value.find((x) => x.id === selected.value.id)
      if (still) selected.value = still
      else selected.value = null
    }
  } catch (e) {
    app.setMessage(e.message, true)
    items.value = []
  } finally {
    loading.value = false
  }
}

function onSearch() {
  activePresetId.value = ''
  resetPagination()
  load()
}

function prevPage() {
  if (page.value <= 1) return
  page.value -= 1
  load()
}

function nextPage() {
  if (!canGoNext.value) return
  const nextCur = metadata.value.nextCursor
  page.value += 1
  if (cursorByPage.value.length < page.value) {
    cursorByPage.value.push(nextCur)
  } else {
    cursorByPage.value[page.value - 1] = nextCur
  }
  load()
}

function formatDownloads(n) {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

onMounted(async () => {
  civitaiApiKey.value = loadCivitaiApiKey()
  try {
    const res = await api.getCivitaiBrowsePresets()
    presets.value = res.presets || []
    if (presets.value.length) applyPreset(presets.value[0])
    else load()
  } catch (e) {
    app.setMessage(e.message, true)
    await load()
  }
  if (hasCivitaiApiKey(civitaiApiKey.value)) {
    loadFavorites().catch(() => {})
  }
})

watch([sort, period, types], () => {
  if (mainTab.value !== 'browse') return
  activePresetId.value = ''
  resetPagination()
  load()
})

watch(contentMode, onContentModeChange)
</script>

<template>
  <div class="flex w-full min-h-0 flex-col gap-4 lg:flex-row lg:items-start">
    <div class="min-w-0 flex-1 space-y-4">
      <PageAlert />

      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base">C 站模型库</CardTitle>
          <CardDescription>
            浏览/搜索 Checkpoint、LoRA（cursor 分页）；蓝/红 C 站通过官方 API 的 nsfw 参数区分（非换域名）。
            收藏按本机保存的 Civitai API Key 分目录。也可
            <Button variant="ghost" size="sm" class="h-auto px-1 text-xs text-primary" @click="openModelImportModal()">
              粘贴链接导入
            </Button>
          </CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="flex flex-wrap items-center gap-2 border-b border-border pb-3">
            <Button
              :variant="mainTab === 'browse' ? 'default' : 'outline'"
              size="sm"
              @click="switchMainTab('browse')"
            >
              浏览
            </Button>
            <Button
              :variant="mainTab === 'favorites' ? 'default' : 'outline'"
              size="sm"
              class="gap-1"
              @click="switchMainTab('favorites')"
            >
              <Star class="h-3.5 w-3.5" />
              我的收藏
              <Badge v-if="favoriteItems.length" variant="secondary" class="text-[10px]">
                {{ favoriteItems.length }}
              </Badge>
            </Button>
            <p v-if="mainTab === 'favorites' && !hasApiKey" class="text-xs text-amber-600 dark:text-amber-400">
              请先在右侧保存 Civitai API Key 后查看收藏
            </p>
          </div>

          <template v-if="mainTab === 'browse'">
          <div class="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-muted/10 p-3">
            <div class="space-y-1">
              <Label class="text-xs">内容范围</Label>
              <SelectNative v-model="contentMode" class="h-9 text-xs min-w-[9rem]">
                <option value="sfw">蓝 C 站（SFW）</option>
                <option value="nsfw">红 C 站（NSFW）</option>
                <option value="all">全部</option>
              </SelectNative>
            </div>
            <p class="text-[10px] text-muted-foreground flex-1 min-w-[200px]">
              {{ contentModeHint }}
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <Button
              v-for="p in presets"
              :key="p.id"
              :variant="activePresetId === p.id ? 'default' : 'outline'"
              size="sm"
              class="text-xs"
              @click="applyPreset(p)"
            >
              {{ p.label }}
            </Button>
          </div>

          <div class="rounded-lg border border-border bg-muted/15 p-3 space-y-3">
            <div class="flex items-center gap-2 text-xs font-medium text-foreground">
              <Tag class="h-3.5 w-3.5 text-primary" />
              标签筛选
              <Badge v-if="activeTag" variant="secondary" class="text-[10px] gap-1">
                {{ activeTag }}
                <button type="button" class="hover:text-destructive" @click.stop="clearTag">
                  <X class="h-3 w-3" />
                </button>
              </Badge>
            </div>
            <div class="flex flex-wrap gap-2">
              <Input
                v-model="tagSearchInput"
                class="flex-1 min-w-[160px] text-sm"
                placeholder="输入标签名搜索，如 anime、character…"
                @input="onTagInput"
                @keyup.enter="applyTagFromInput"
              />
              <Button size="sm" variant="outline" :disabled="loading" @click="applyTagFromInput">
                应用标签
              </Button>
            </div>
            <p v-if="tagSuggestLoading" class="text-[11px] text-muted-foreground">匹配标签中…</p>
            <div v-else-if="tagSuggestions.length" class="flex flex-wrap gap-1.5">
              <button
                v-for="t in tagSuggestions"
                :key="t.name"
                type="button"
                class="rounded-full border border-border bg-background px-2.5 py-0.5 text-[11px] hover:border-primary hover:bg-primary/10 transition-colors"
                @click="selectTag(t.name)"
              >
                {{ t.name }}
              </button>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <span class="text-[10px] text-muted-foreground w-full">常用：</span>
              <button
                v-for="t in QUICK_TAGS"
                :key="t"
                type="button"
                :class="
                  cn(
                    'rounded-full border px-2.5 py-0.5 text-[11px] transition-colors',
                    activeTag === t
                      ? 'border-primary bg-primary/15 text-primary'
                      : 'border-border hover:bg-accent',
                  )
                "
                @click="selectTag(t)"
              >
                {{ t }}
              </button>
            </div>
          </div>

          <div class="flex flex-wrap items-end gap-3">
            <div class="flex-1 min-w-[200px] space-y-1">
              <Label class="text-xs">模型关键词</Label>
              <div class="flex gap-2">
                <Input
                  v-model="searchQuery"
                  class="text-sm"
                  placeholder="模型名、风格描述…"
                  @keyup.enter="onSearch"
                />
                <Button size="sm" class="gap-1 shrink-0" :disabled="loading" @click="onSearch">
                  <Search class="h-4 w-4" />
                  搜索
                </Button>
              </div>
              <p class="text-[10px] text-muted-foreground">
                全文搜索与标签可同时使用；翻页使用 C 站 cursor（非页码）。
              </p>
            </div>
            <div class="space-y-1">
              <Label class="text-xs">类型</Label>
              <SelectNative v-model="types" class="h-9 text-xs min-w-[8rem]">
                <option value="Checkpoint">Checkpoint</option>
                <option value="LORA">LoRA</option>
                <option value="LoCon">LoCon</option>
                <option value="DoRA">DoRA</option>
                <option value="Controlnet">Controlnet</option>
                <option value="VAE">VAE</option>
              </SelectNative>
            </div>
            <div class="space-y-1">
              <Label class="text-xs">排序</Label>
              <SelectNative v-model="sort" class="h-9 text-xs min-w-[9rem]">
                <option value="Most Downloaded">最多下载</option>
                <option value="Highest Rated">最高评分</option>
                <option value="Newest">最新</option>
              </SelectNative>
            </div>
            <div class="space-y-1">
              <Label class="text-xs">周期</Label>
              <SelectNative v-model="period" class="h-9 text-xs min-w-[7rem]">
                <option value="Week">一周</option>
                <option value="Month">一月</option>
                <option value="Year">一年</option>
                <option value="AllTime">全部</option>
              </SelectNative>
            </div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2">
            <p class="text-xs text-muted-foreground">
              {{ loading ? '加载中…' : `本页 ${items.length} 条` }}
              <span v-if="metadata.totalItems"> · 约 {{ metadata.totalItems }} 个匹配</span>
            </p>
            <div class="flex items-center gap-2">
              <Button variant="outline" size="sm" :disabled="loading || !canGoPrev" @click="prevPage">
                <ChevronLeft class="h-4 w-4" />
                上一页
              </Button>
              <span class="text-xs tabular-nums min-w-[5rem] text-center">{{ pageLabel }}</span>
              <Button variant="outline" size="sm" :disabled="loading || !canGoNext" @click="nextPage">
                下一页
                <ChevronRight class="h-4 w-4" />
              </Button>
            </div>
          </div>
          </template>

          <div
            v-else-if="mainTab === 'favorites'"
            class="flex flex-wrap items-center justify-between gap-2"
          >
            <p class="text-xs text-muted-foreground">
              {{ favoritesLoading ? '加载收藏…' : `共 ${favoriteItems.length} 个收藏` }}
            </p>
            <Button
              variant="outline"
              size="sm"
              :disabled="favoritesLoading || !hasApiKey"
              @click="loadFavorites"
            >
              刷新
            </Button>
          </div>

          <p
            v-if="(mainTab === 'browse' && !loading && !displayItems.length) || (mainTab === 'favorites' && !favoritesLoading && !displayItems.length)"
            class="py-16 text-center text-sm text-muted-foreground"
          >
            <template v-if="mainTab === 'favorites'">
              {{ hasApiKey ? '暂无收藏，在浏览页点击心形图标添加。' : '请先保存 API Key。' }}
            </template>
            <template v-else>
              无结果，请换关键词、标签、内容范围或筛选条件。
            </template>
          </p>

          <div
            v-else-if="displayItems.length"
            ref="civitaiGridRef"
            class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
          >
            <article
              v-for="item in displayItems"
              :key="mainTab === 'favorites' ? `fav-${item.id}` : `${page}-${item.id}`"
              data-stagger-item
              :class="
                cn(
                  'cursor-pointer overflow-hidden rounded-xl border-2 bg-card transition-all hover:shadow-md',
                  selected?.id === item.id
                    ? 'border-primary ring-1 ring-primary/30'
                    : 'border-border hover:border-primary/40',
                )
              "
              @click="selectCard(item)"
            >
              <div class="relative aspect-[4/3] bg-muted/40 flex items-center justify-center p-1">
                <ModelPreviewMedia
                  v-if="item.previewMedia || item.thumbnailUrl"
                  :source="item.previewMedia || { url: item.thumbnailUrl, mediaType: 'image' }"
                  class="max-h-full max-w-full"
                  :eager="selected?.id === item.id"
                />
                <span v-else class="text-xs text-muted-foreground">无预览</span>
                <Badge
                  variant="secondary"
                  class="absolute left-2 top-2 text-[10px] bg-background/90"
                >
                  {{ item.type }}
                </Badge>
                <Badge
                  v-if="item.nsfw"
                  variant="destructive"
                  class="absolute left-2 top-8 text-[10px] opacity-90"
                >
                  NSFW
                </Badge>
                <button
                  type="button"
                  class="absolute right-2 top-2 rounded-full border border-border bg-background/90 p-1.5 shadow-sm hover:bg-primary/10 transition-colors"
                  :title="isFavorited(item.id) ? '取消收藏' : '收藏'"
                  @click.stop="toggleFavorite(item, $event)"
                >
                  <Heart
                    :class="cn('h-4 w-4', isFavorited(item.id) ? 'fill-rose-500 text-rose-500' : 'text-muted-foreground')"
                  />
                </button>
                <button
                  v-if="mainTab === 'favorites'"
                  type="button"
                  class="absolute right-2 bottom-2 rounded-md border border-border bg-background/90 p-1 text-destructive hover:bg-destructive/10"
                  title="从收藏移除"
                  @click.stop="removeFavoriteItem(item, $event)"
                >
                  <Trash2 class="h-3.5 w-3.5" />
                </button>
              </div>
              <div class="space-y-1 p-3">
                <p class="text-sm font-medium leading-snug line-clamp-2" :title="item.name">
                  {{ item.name }}
                </p>
                <p class="text-[11px] text-muted-foreground truncate">{{ item.creator }}</p>
                <div v-if="item.tags?.length" class="flex flex-wrap gap-1 max-h-10 overflow-hidden">
                  <Badge
                    v-for="tag in item.tags.slice(0, 4)"
                    :key="tag"
                    variant="outline"
                    class="text-[9px] px-1 py-0 font-normal cursor-pointer hover:bg-primary/10"
                    @click.stop="selectTag(tag)"
                  >
                    {{ tag }}
                  </Badge>
                </div>
                <p class="text-[10px] text-muted-foreground">
                  {{ formatDownloads(item.downloadCount) }} 下载
                  <span v-if="item.baseModel"> · {{ item.baseModel }}</span>
                </p>
              </div>
            </article>
          </div>
        </CardContent>
      </Card>
    </div>

    <aside
      class="w-full shrink-0 lg:sticky lg:top-16 lg:w-[min(100%,420px)] lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto space-y-3"
    >
      <Card v-if="!selected" class="border-dashed">
        <CardContent class="py-12 text-center text-sm text-muted-foreground">
          点击左侧模型卡片，在此解析并下载到本地。
        </CardContent>
      </Card>

      <template v-else>
        <Card>
          <CardHeader class="pb-2">
            <CardTitle class="text-sm line-clamp-2">{{ selected.name }}</CardTitle>
            <CardDescription class="flex flex-wrap gap-1.5">
              <Badge variant="outline">{{ selected.type }}</Badge>
              <Badge variant="secondary">{{ selected.suggestedFolder }}</Badge>
            </CardDescription>
          </CardHeader>
          <CardContent class="flex flex-wrap gap-2 pb-4">
            <Button
              variant="outline"
              size="sm"
              class="gap-1"
              @click="selected.pageUrl && window.open(selected.pageUrl, '_blank')"
            >
              <ExternalLink class="h-3.5 w-3.5" />
              C 站打开
            </Button>
            <Button variant="outline" size="sm" class="gap-1" @click="openInModal">
              <Link2 class="h-3.5 w-3.5" />
              弹窗导入
            </Button>
          </CardContent>
        </Card>

        <ModelImportPanel
          :key="selected.id + '-' + importUrl"
          embedded
          :initial-url="importUrl"
        />
      </template>
    </aside>
  </div>
</template>
