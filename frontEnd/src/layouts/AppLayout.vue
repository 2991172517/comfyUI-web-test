<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import AnimatedRouterView from '@/components/layout/AnimatedRouterView.vue'
import { Activity, Layers } from 'lucide-vue-next'
import AppNav from '@/components/layout/AppNav.vue'
import { api } from '@/api/client.js'
import { getAccessToken, setAuthSession } from '@/composables/useAuth.js'
import { createAppStore } from '@/stores/useAppStore.js'
import { createBatchStore } from '@/stores/useBatchStore.js'
import { createGenerateQueueWithApp } from '@/stores/useGenerateQueueStore.js'
import GenerateQueueDock from '@/components/layout/GenerateQueueDock.vue'
import { createHistoryStore } from '@/stores/useHistoryStore.js'
import { createFavoritesPageStore } from '@/stores/useFavoritesPageStore.js'
import Badge from '@/components/ui/Badge.vue'
import QuickNavFab from '@/components/layout/QuickNavFab.vue'
import UserMenu from '@/components/layout/UserMenu.vue'
import GlobalPromptSettingsModal from '@/components/prompt/GlobalPromptSettingsModal.vue'
import ModelImportModal from '@/components/models/ModelImportModal.vue'
import ConfirmDialogHost from '@/components/ui/ConfirmDialogHost.vue'
import RandomGachaHost from '@/components/effects/RandomGachaHost.vue'
import AppToastHost from '@/components/layout/AppToastHost.vue'
import FireflyEcosystemBackground from '@/components/background/FireflyEcosystemBackground.vue'
import { provideConfirmDialog } from '@/composables/useConfirmDialog.js'
import { provideRandomGachaOverlay } from '@/composables/useRandomGachaOverlay.js'
import { cn } from '@/lib/utils'

provideConfirmDialog()
provideRandomGachaOverlay()
const app = createAppStore()
const batch = createBatchStore(app)
createGenerateQueueWithApp(app, batch)
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
  <div class="relative min-h-screen">
    <FireflyEcosystemBackground variant="ambient" :intensity="0.6" :show-controls="false" />

    <div class="relative z-10 flex min-h-screen flex-col bg-background/86 backdrop-blur-[1px]">
    <header
      class="sticky top-0 z-50 border-b border-border bg-card/92 backdrop-blur supports-[backdrop-filter]:bg-card/78"
    >
      <div class="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6">
        <RouterLink to="/generate" class="flex shrink-0 items-center gap-2">
          <Layers class="h-5 w-5 text-primary" />
          <span class="hidden text-sm font-semibold sm:inline">ComfyUI 控制台</span>
        </RouterLink>

        <AppNav />

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
      <AnimatedRouterView />
    </main>

    <QuickNavFab />
    <GlobalPromptSettingsModal />
    <ModelImportModal />
    <ConfirmDialogHost />
    <RandomGachaHost />
    <AppToastHost />
    <GenerateQueueDock />
    </div>
  </div>
</template>
