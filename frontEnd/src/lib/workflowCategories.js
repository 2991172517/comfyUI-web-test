/** 工作流一级分类（与后端 workflow_categories.py 一致） */
export const WORKFLOW_CATEGORIES = [
  { id: 'generate', label: '文生图' },
  { id: 'inpaint', label: '局部重绘' },
  { id: 'upscale', label: '高清放大' },
  { id: 'other', label: '其他' },
]

export const DEFAULT_WORKFLOW_CATEGORY = 'generate'

const BY_ID = Object.fromEntries(WORKFLOW_CATEGORIES.map((c) => [c.id, c]))

export function categoryLabel(id) {
  return BY_ID[id]?.label || id || '未分类'
}

export function normalizeCategory(value) {
  const raw = String(value || '').trim().toLowerCase()
  return BY_ID[raw] ? raw : DEFAULT_WORKFLOW_CATEGORY
}

/** 从工作流 id 推断分类（与后端 infer_category_from_workflow_id 一致） */
export function inferCategoryFromWorkflowId(workflowId) {
  const id = String(workflowId || '')
  const low = id.toLowerCase()
  if (low.includes('inpaint') || id.includes('重绘')) return 'inpaint'
  if (low.includes('upscale') || id.includes('放大') || id.includes('高清')) return 'upscale'
  return DEFAULT_WORKFLOW_CATEGORY
}

export function isPngRestoreWorkflowId(workflowId) {
  return /^variants\/png_[a-f0-9]+$/i.test(String(workflowId || ''))
}
