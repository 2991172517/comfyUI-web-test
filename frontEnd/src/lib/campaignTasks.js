/** 任务计划列表：筛选与排序（前端） */

export function workflowLabel(task) {
  return task?.workflow_display_name || task?.workflow_id || '—'
}

export function filterAndSortTasks(tasks, filters) {
  let list = [...(tasks || [])]
  const q = String(filters?.search || '')
    .trim()
    .toLowerCase()
  if (q) {
    list = list.filter((t) => {
      const wf = workflowLabel(t).toLowerCase()
      return (
        String(t.name || '')
          .toLowerCase()
          .includes(q) ||
        String(t.task_id || '')
          .toLowerCase()
          .includes(q) ||
        wf.includes(q) ||
        String(t.workflow_id || '')
          .toLowerCase()
          .includes(q)
      )
    })
  }
  if (filters?.status) {
    list = list.filter((t) => (t.status || 'pending') === filters.status)
  }
  if (filters?.workflow) {
    list = list.filter((t) => workflowLabel(t) === filters.workflow)
  }
  if (filters?.hasPrompts === 'yes') {
    list = list.filter((t) => t.has_batch_prompts)
  } else if (filters?.hasPrompts === 'no') {
    list = list.filter((t) => !t.has_batch_prompts)
  }

  const sort = filters?.sort || 'created_desc'
  const ts = (iso) => {
    if (!iso) return 0
    const n = Date.parse(iso)
    return Number.isNaN(n) ? 0 : n
  }
  list.sort((a, b) => {
    if (sort === 'name_asc') {
      return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN')
    }
    if (sort === 'planned_desc') {
      return (b.planned_total || 0) - (a.planned_total || 0)
    }
    if (sort === 'created_asc') {
      return ts(a.created_at) - ts(b.created_at)
    }
    return ts(b.created_at) - ts(a.created_at)
  })
  return list
}

export function uniqueWorkflowLabels(tasks) {
  const set = new Set()
  for (const t of tasks || []) {
    const w = workflowLabel(t)
    if (w && w !== '—') set.add(w)
  }
  return [...set].sort((a, b) => a.localeCompare(b, 'zh-CN'))
}

export function countByStatus(tasks) {
  const counts = { pending: 0, running: 0, completed: 0, failed: 0 }
  for (const t of tasks || []) {
    const s = t.status || 'pending'
    if (s in counts) counts[s] += 1
    else counts.pending += 1
  }
  return counts
}
