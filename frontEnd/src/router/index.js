import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'

const routes = [
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', redirect: '/generate' },
      {
        path: 'generate',
        name: 'generate',
        component: () => import('@/views/GenerateView.vue'),
        meta: {
          title: '生成',
          description: '单张生成或 LoRA 扫参批量，共用工作流与提示词配置',
          wideWhenSweep: true,
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
        path: 'settings/nodes',
        name: 'node-catalog',
        component: () => import('@/views/NodeCatalogView.vue'),
        meta: { title: '节点默认', description: 'Checkpoint / LoRA 槽位默认配置' },
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
    ],
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
