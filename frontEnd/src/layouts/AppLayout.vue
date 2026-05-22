<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, RouterLink, RouterView } from 'vue-router'
import {
  Sparkles,
  History,
  Star,
  Activity,
  Layers,
  GitBranch,
  ListTodo,
  Boxes,
  KeyRound,
  Globe,
} from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { allowsBatch, authRole, getAccessToken, isAdmin, setAuthSession } from '@/composables/useAuth.js'
import { createAppStore } from '@/stores/useAppStore.js'
import { createBatchStore } from '@/stores/useBatchStore.js'
import { createHistoryStore } from '@/stores/useHistoryStore.js'
import { createFavoritesPageStore } from '@/stores/useFavoritesPageStore.js'
import Badge from '@/components/ui/Badge.vue'
import QuickNavFab from '@/components/layout/QuickNavFab.vue'
import UserMenu from '@/components/layout/UserMenu.vue'
import GlobalPromptSettingsModal from '@/components/prompt/GlobalPromptSettingsModal.vue'
import ModelImportModal from '@/components/models/ModelImportModal.vue'
import { cn } from '@/lib/utils'

const app = createAppStore()
const batch = createBatchStore(app)
const history = createHistoryStore()
createFavoritesPageStore()
const route = useRoute()

onMounted(async () => {
  const token = getAccessToken()
  if (token) {
    try {
      const me = await api.authMe()
      if (me.ok) {
        setAuthSession({
          token,
          role: me.role,
          username: me.username,
          invite_code: me.invite_code,
          allow_batch: me.allow_batch,
          single_quota: me.single_quota,
          single_remaining: me.single_remaining,
        })
      }
    } catch {
      /* 401 由 client 处理 */
    }
  }
  await app.init()
  await batch.refreshHistory()
  await history.loadFilterOptions()
})

const nav = computed(() => {
  void authRole.value
  const items = [
    { to: '/generate', label: '生成', icon: Sparkles },
    ...(allowsBatch()
      ? [
          { to: '/workflows', label: '工作流配置', icon: GitBranch },
          { to: '/campaign', label: '任务计划', icon: ListTodo },
        ]
      : []),
    { to: '/history', label: '历史记录', icon: History },
    { to: '/favorites', label: '收藏', icon: Star },
    { to: '/models', label: '模型管理', icon: Boxes },
    { to: '/models/civitai', label: 'C 站模型库', icon: Globe },
  ]
  if (isAdmin()) {
    items.push({ to: '/admin/invites', label: '邀请码管理', icon: KeyRound })
  }
  return items
})

const pageTitle = computed(() => route.meta?.title || '控制台')
/** 生成页在内容区自带模式说明，避免顶栏副标题随模式切换伸缩 */
const pageDesc = computed(() =>
  route.name === 'generate' ? '' : route.meta?.description || '',
)
/** 生成页单张/批量共用布局，不因 ?mode=sweep 变宽 */
const isWidePage = computed(
  () => !!route.meta?.wide || route.name === 'history' || route.name === 'civitai-browse',
)
const isFullBleed = computed(() => !!route.meta?.fullBleed)
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background">
    <header
      class="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80"
    >
      <div class="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6">
        <RouterLink to="/generate" class="flex shrink-0 items-center gap-2">
          <Layers class="h-5 w-5 text-primary" />
          <span class="hidden text-sm font-semibold sm:inline">ComfyUI 控制台</span>
        </RouterLink>

        <nav class="flex flex-1 items-center gap-1 overflow-x-auto">
          <RouterLink
            v-for="item in nav"
            :key="item.to"
            :to="item.to"
            :class="
              cn(
                'flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm transition-colors',
                'text-muted-foreground hover:bg-accent hover:text-foreground',
              )
            "
            active-class="!bg-primary/15 !text-primary font-medium"
          >
            <component :is="item.icon" class="h-4 w-4 shrink-0" />
            {{ item.label }}
          </RouterLink>
        </nav>

        <div class="flex shrink-0 items-center gap-2">
          <Badge :variant="app.healthOk ? 'success' : 'destructive'" class="gap-1">
            <Activity class="h-3 w-3" />
            <span class="hidden sm:inline">{{ app.healthOk ? 'ComfyUI 在线' : '离线' }}</span>
            <span class="sm:hidden">{{ app.healthOk ? 'OK' : '—' }}</span>
          </Badge>
          <UserMenu />
        </div>
      </div>
    </header>

    <main
      :class="
        cn(
          'mx-auto w-full flex-1 pb-8',
          isFullBleed ? 'max-w-none px-2 sm:px-4' : 'px-4 sm:px-6',
          isFullBleed || isWidePage ? 'max-w-[min(100%,1920px)]' : 'max-w-7xl',
        )
      "
    >
      <div
        :class="
          cn(
            'border-b border-border pb-4',
            pageDesc ? 'mb-6' : 'mb-4',
          )
        "
      >
        <h1 class="text-2xl font-semibold tracking-tight">{{ pageTitle }}</h1>
        <p v-if="pageDesc" class="mt-1 text-sm text-muted-foreground max-w-3xl">{{ pageDesc }}</p>
      </div>
      <RouterView />
    </main>

    <QuickNavFab />
    <GlobalPromptSettingsModal />
    <ModelImportModal />
  </div>
</template>
