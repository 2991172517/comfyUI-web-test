import { api } from '@/api/client.js'

/** 随机词模式：六类各抽一词 */
export const VOCAB_RANDOM_CATEGORY_NAMES = Object.freeze([
  '服饰',
  '表情',
  '动作',
  '环境',
  '物品',
  '镜头',
])

let cachedTree = null

export function clearVocabularyCategoryTreeCache() {
  cachedTree = null
}

async function loadCategoryTree() {
  if (cachedTree) return cachedTree
  const res = await api.vocabularyCategoryTree()
  cachedTree = res.tree || []
  return cachedTree
}

function flattenCategories(nodes, out = []) {
  for (const node of nodes || []) {
    out.push({ id: node.id, name: node.name })
    flattenCategories(node.children, out)
  }
  return out
}

export function resolveCategoryIdsByName(tree, names = VOCAB_RANDOM_CATEGORY_NAMES) {
  const byName = new Map(flattenCategories(tree).map((n) => [n.name, n.id]))
  return names.map((name) => ({ name, id: byName.get(name) || '' }))
}

async function pickOneFromCategory(categoryId) {
  const countRes = await api.vocabularyCategoryCount(categoryId)
  const total = Number(countRes?.total ?? 0)
  if (!total) return null

  const offset = Math.floor(Math.random() * total)
  const res = await api.vocabularyListPrompts(categoryId, { offset, limit: 1 })
  const item = res.items?.[0]
  const value = String(item?.value || '').trim()
  return value || null
}

/**
 * @returns {Promise<Array<{ name: string, id: string, value: string }>>}
 */
export async function pickRandomSixFromLibrary() {
  const tree = await loadCategoryTree()
  const categories = resolveCategoryIdsByName(tree)
  const picks = []

  await Promise.all(
    categories.map(async ({ name, id }) => {
      if (!id) return
      try {
        const value = await pickOneFromCategory(id)
        if (value) picks.push({ name, id, value })
      } catch {
        /* 单类失败不影响其余类 */
      }
    }),
  )

  return picks.sort(
    (a, b) =>
      VOCAB_RANDOM_CATEGORY_NAMES.indexOf(a.name) - VOCAB_RANDOM_CATEGORY_NAMES.indexOf(b.name),
  )
}

export function getWorkflowPositiveText(app) {
  const enc = app.promptEncode?.positive
  if (!enc?.node_id) return ''
  const node = app.state.nodes.find((n) => n.id === enc.node_id)
  const field = node?.fields?.find((f) => f.key === 'text')
  return field ? String(app.fieldValue(enc.node_id, field) || '') : ''
}

export function setWorkflowPositiveText(app, val) {
  const enc = app.promptEncode?.positive
  if (!enc?.node_id) return
  app.updateField(enc.node_id, 'text', val)
}
