import {
  Sparkles,
  Paintbrush,
  ZoomIn,
  History,
  Star,
  GitBranch,
  ListTodo,
  Boxes,
  KeyRound,
  Tags,
} from 'lucide-vue-next'
import { allowsBatch, isAdmin } from '@/composables/useAuth.js'

/** @typedef {{ to: string, label: string, icon: import('vue').Component, match?: (path: string) => boolean }} NavItem */

/** 顶栏主菜单（高频、尽量一屏放下） */
export function buildPrimaryNavItems() {
  void allowsBatch()
  /** @type {NavItem[]} */
  const items = [
    { to: '/generate', label: '生成', icon: Sparkles },
  ]
  if (allowsBatch()) {
    items.push(
      { to: '/workflows', label: '工作流配置', icon: GitBranch },
      { to: '/campaign', label: '任务计划', icon: ListTodo },
    )
  }
  items.push(
    { to: '/history', label: '历史', icon: History },
    { to: '/favorites', label: '收藏', icon: Star },
  )
  return items
}

/** 顶栏「更多」下拉（工具、模型、管理） */
export function buildMoreNavItems() {
  void isAdmin()
  /** @type {NavItem[]} */
  const items = [
    { to: '/inpaint', label: '局部重绘', icon: Paintbrush },
    { to: '/upscale', label: '高清放大', icon: ZoomIn },
    { to: '/models', label: '模型管理', icon: Boxes },
  ]
  if (isAdmin()) {
    items.push({ to: '/admin/invites', label: '邀请码管理', icon: KeyRound })
  }
  return items
}

/** 用户菜单内的设置项（不占顶栏宽度） */
export function buildSettingsNavItems() {
  return [{ to: '/settings/tags', label: 'Tag 显示管理', icon: Tags }]
}

/** 某路由是否落在「更多」或设置菜单中（用于高亮「更多」按钮） */
export function isMoreNavActive(path) {
  const more = buildMoreNavItems().some((i) => path === i.to || path.startsWith(`${i.to}/`))
  const settings = buildSettingsNavItems().some(
    (i) => path === i.to || path.startsWith(`${i.to}/`),
  )
  return more || settings
}
