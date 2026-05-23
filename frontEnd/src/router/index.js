import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import { allowsBatch, isAdmin, isLoggedIn } from '@/composables/useAuth.js'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/generate' },
      {
        path: 'generate',
        name: 'generate',
        component: () => import('@/views/GenerateView.vue'),
        meta: {
          title: '生成',
          description: '共用工作流与提示词配置',
        },
      },
      {
        path: 'batch',
        redirect: (to) => ({
          path: '/generate',
          query: { ...to.query, mode: 'sweep' },
        }),
      },
      {
        path: 'history',
        name: 'history',
        component: () => import('@/views/HistoryView.vue'),
        meta: {
          title: '历史记录',
          description: '单抽与批量按时间浏览，支持筛选与全宽网格',
          wide: true,
          fullBleed: true,
        },
      },
      {
        path: 'favorites',
        name: 'favorites',
        component: () => import('@/views/FavoritesView.vue'),
        meta: {
          title: '收藏',
          description: '单图收藏网格浏览，筛选与参数详情',
          wide: true,
          fullBleed: true,
        },
      },
      {
        path: 'models/import',
        name: 'model-import',
        component: () => import('@/views/ModelImportView.vue'),
        meta: { title: '模型导入', description: 'Civitai / Shakker 解析与下载' },
      },
      {
        path: 'models/civitai',
        name: 'civitai-browse',
        component: () => import('@/views/CivitaiBrowseView.vue'),
        meta: {
          title: 'C 站模型库',
          description: '浏览热门与搜索 Checkpoint / LoRA，一键导入下载',
          wide: true,
        },
      },
      {
        path: 'workflows',
        name: 'workflows',
        component: () => import('@/views/WorkflowsView.vue'),
        meta: {
          title: '工作流配置',
          description: 'Checkpoint、LoRA 链增删改与 Style',
          wide: true,
        },
      },
      {
        path: 'settings/prompts',
        name: 'prompt-settings',
        component: () => import('@/views/PromptSettingsView.vue'),
        meta: { title: '提示词', description: '全局提示词、预设库' },
      },
      {
        path: 'settings/tags',
        name: 'tag-manage',
        component: () => import('@/views/TagManagerView.vue'),
        meta: { title: 'Tag 词库管理', description: '分类浏览、筛选搜索、增删词条与默认权重' },
      },
      {
        path: 'models',
        name: 'model-manage',
        component: () => import('@/views/NodeCatalogView.vue'),
        meta: { title: '模型管理', description: '本地 Checkpoint / LoRA：说明编辑与删除' },
      },
      {
        path: 'settings/nodes',
        redirect: '/models',
      },
      {
        path: 'campaign',
        name: 'campaign',
        component: () => import('@/views/CampaignView.vue'),
        meta: {
          title: '任务计划',
          description: '串行执行多个批量任务',
          wide: true,
        },
      },
      {
        path: 'admin/invites',
        name: 'invite-manage',
        component: () => import('@/views/InviteManageView.vue'),
        meta: { title: '邀请码管理', description: '邀请码增删改与有效期', requiresAdmin: true },
      },
    ],
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.public) {
    if (to.name === 'login' && isLoggedIn()) {
      const redirect =
        typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/')
          ? to.query.redirect
          : '/generate'
      return redirect
    }
    return true
  }
  if (!isLoggedIn()) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }
  if (to.matched.some((r) => r.meta.requiresAdmin) && !isAdmin()) {
    return { path: '/generate' }
  }
  if (!allowsBatch() && (to.path === '/campaign' || to.name === 'campaign')) {
    return { path: '/generate' }
  }
  if (
    !allowsBatch() &&
    (to.path === '/workflows' ||
      to.name === 'workflows' ||
      to.path.startsWith('/settings/'))
  ) {
    return { path: '/generate' }
  }
  if (!allowsBatch() && to.name === 'generate' && to.query.mode === 'sweep') {
    const query = { ...to.query }
    delete query.mode
    return { path: '/generate', query }
  }
  return true
})
