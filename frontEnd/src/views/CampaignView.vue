<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import CampaignTaskFilters from '@/components/campaign/CampaignTaskFilters.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import { statusLabel } from '@/api/client.js'
import {
  countByStatus,
  filterAndSortTasks,
  uniqueWorkflowLabels,
  workflowLabel,
} from '@/lib/campaignTasks.js'
import { cn } from '@/lib/utils'
import {
  Calendar,
  History,
  Layers,
  ListTodo,
  Play,
  Sparkles,
  Trash2,
} from 'lucide-vue-next'

const app = useAppStore()
const batch = useBatchStore()
const router = useRouter()
const tasks = ref([])
const selected = ref(new Set())
const loading = ref(false)
const running = ref(false)
const historyTaskId = ref('')
const historyTaskName = ref('')
const taskBatches = ref([])
const batchesLoading = ref(false)

const filters = ref({
  search: '',
  status: '',
  workflow: '',
  hasPrompts: '',
  sort: 'created_desc',
})

const statusVariant = {
  pending: 'outline',
  running: 'default',
  completed: 'success',
  failed: 'destructive',
}

function statusLabelTask(status) {
  const map = {
    pending: '待执行',
    running: '执行中',
    completed: '已执行',
    failed: '失败',
  }
  return map[status] || status || '待执行'
}

const workflowOptions = computed(() => uniqueWorkflowLabels(tasks.value))
const filteredTasks = computed(() => filterAndSortTasks(tasks.value, filters.value))
const statusCounts = computed(() => countByStatus(tasks.value))

const selectedInView = computed(() =>
  filteredTasks.value.filter((t) => selected.value.has(t.task_id)).length,
)

function formatTime(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

async function refresh() {
  loading.value = true
  try {
    const res = await api.listBatchTasks()
    tasks.value = res.tasks || []
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    loading.value = false
  }
}

function toggle(id, ev) {
  ev?.stopPropagation?.()
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

function toggleAllFiltered() {
  const ids = filteredTasks.value.map((t) => t.task_id)
  const allSelected = ids.length > 0 && ids.every((id) => selected.value.has(id))
  if (allSelected) {
    const next = new Set(selected.value)
    for (const id of ids) next.delete(id)
    selected.value = next
  } else {
    const next = new Set(selected.value)
    for (const id of ids) next.add(id)
    selected.value = next
  }
}

function filterByStatus(status) {
  filters.value.status = filters.value.status === status ? '' : status
}

async function runSelected() {
  const ids = [...selected.value]
  if (!ids.length) {
    app.setMessage('请至少勾选一个任务', true)
    return
  }
  running.value = true
  try {
    await api.runBatchTasks(ids)
    app.setMessage(`已开始串行执行 ${ids.length} 个批量任务，完成后状态会变为「已执行」`)
    selected.value = new Set()
    setTimeout(() => refresh(), 2000)
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    running.value = false
  }
}

function clearSelectionIfIncludes(ids) {
  const next = new Set(selected.value)
  for (const id of ids) next.delete(id)
  selected.value = next
  if (ids.some((id) => historyTaskId.value === id)) {
    historyTaskId.value = ''
    historyTaskName.value = ''
    taskBatches.value = []
  }
}

async function removeTask(id, ev) {
  ev?.stopPropagation?.()
  ev?.preventDefault?.()
  if (!confirm('删除该任务？')) return
  try {
    await api.deleteBatchTask(id)
    clearSelectionIfIncludes([id])
    await refresh()
    app.setMessage('已删除')
  } catch (e) {
    app.setMessage(e.message, true)
  }
}

async function removeSelected() {
  const ids = [...selected.value]
  if (!ids.length) {
    app.setMessage('请先勾选要删除的任务', true)
    return
  }
  if (!confirm(`确定删除选中的 ${ids.length} 个任务？（仅删除计划配置，不删除已生成的批量图片）`)) {
    return
  }
  let ok = 0
  const failed = []
  for (const id of ids) {
    try {
      await api.deleteBatchTask(id)
      ok += 1
    } catch (e) {
      failed.push({ id, message: e.message })
    }
  }
  clearSelectionIfIncludes(ids)
  await refresh()
  if (failed.length) {
    app.setMessage(`已删除 ${ok} 个，${failed.length} 个失败：${failed[0].message}`, true)
  } else {
    app.setMessage(`已删除 ${ok} 个任务`)
  }
}

async function openTaskHistory(task, ev) {
  ev?.stopPropagation?.()
  ev?.preventDefault?.()
  historyTaskId.value = task.task_id
  historyTaskName.value = task.name || task.task_id
  batchesLoading.value = true
  try {
    const res = await api.getBatchTaskBatches(task.task_id, 40)
    taskBatches.value = res.batches || []
  } catch (e) {
    app.setMessage(e.message, true)
    taskBatches.value = []
  } finally {
    batchesLoading.value = false
  }
}

function closeHistory() {
  historyTaskId.value = ''
  historyTaskName.value = ''
  taskBatches.value = []
}

function viewBatchInHistory(batchId, ev) {
  ev?.stopPropagation?.()
  batch.historyTaskId.value = historyTaskId.value
  router.push({
    path: '/history',
    query: { id: batchId, type: 'batch', task_id: historyTaskId.value },
  })
}

function goAllHistory() {
  router.push({ path: '/history' })
}

onMounted(() => refresh())
</script>

<template>
  <div class="space-y-5 w-full max-w-6xl mx-auto">
    <PageAlert />

    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p class="text-sm text-muted-foreground max-w-2xl leading-relaxed">
          在
          <RouterLink to="/generate?mode=sweep" class="text-primary underline font-medium">
            生成 · LoRA 扫参
          </RouterLink>
          配置后「保存为任务」，在此勾选并串行执行；完成后可查看该任务的历史批次。
        </p>
      </div>
      <Button variant="outline" size="sm" :disabled="loading" @click="refresh">
        {{ loading ? '刷新中…' : '刷新列表' }}
      </Button>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <button
        type="button"
        class="rounded-lg border border-border bg-card px-3 py-2.5 text-left hover:bg-muted/30 transition-colors"
        @click="filterByStatus('')"
      >
        <p class="text-[10px] text-muted-foreground flex items-center gap-1">
          <ListTodo class="h-3 w-3" /> 全部
        </p>
        <p class="text-xl font-semibold tabular-nums">{{ tasks.length }}</p>
      </button>
      <button
        type="button"
        :class="
          cn(
            'rounded-lg border px-3 py-2.5 text-left transition-colors',
            filters.status === 'pending'
              ? 'border-primary/50 bg-primary/10'
              : 'border-border bg-card hover:bg-muted/30',
          )
        "
        @click="filterByStatus('pending')"
      >
        <p class="text-[10px] text-muted-foreground">待执行</p>
        <p class="text-xl font-semibold tabular-nums">{{ statusCounts.pending }}</p>
      </button>
      <button
        type="button"
        :class="
          cn(
            'rounded-lg border px-3 py-2.5 text-left transition-colors',
            filters.status === 'completed'
              ? 'border-emerald-500/40 bg-emerald-500/10'
              : 'border-border bg-card hover:bg-muted/30',
          )
        "
        @click="filterByStatus('completed')"
      >
        <p class="text-[10px] text-muted-foreground">已执行</p>
        <p class="text-xl font-semibold tabular-nums text-emerald-700 dark:text-emerald-400">
          {{ statusCounts.completed }}
        </p>
      </button>
      <button
        type="button"
        :class="
          cn(
            'rounded-lg border px-3 py-2.5 text-left transition-colors',
            filters.status === 'failed'
              ? 'border-destructive/40 bg-destructive/10'
              : 'border-border bg-card hover:bg-muted/30',
          )
        "
        @click="filterByStatus('failed')"
      >
        <p class="text-[10px] text-muted-foreground">失败</p>
        <p class="text-xl font-semibold tabular-nums text-destructive">{{ statusCounts.failed }}</p>
      </button>
    </div>

    <CampaignTaskFilters
      v-model:filters="filters"
      :workflow-options="workflowOptions"
      :loading="loading"
      :result-count="filteredTasks.length"
      :total-count="tasks.length"
    />

    <div
      class="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/20 px-3 py-2.5"
    >
      <Button variant="outline" size="sm" :disabled="!filteredTasks.length" @click="toggleAllFiltered">
        {{
          filteredTasks.length &&
          filteredTasks.every((t) => selected.has(t.task_id))
            ? '取消当前页全选'
            : `全选当前筛选（${filteredTasks.length}）`
        }}
      </Button>
      <Button size="sm" :disabled="running || !selected.size" class="gap-1.5" @click="runSelected">
        <Play class="h-3.5 w-3.5" />
        {{ running ? '启动中…' : `执行选中（${selected.size}）` }}
      </Button>
      <Button
        variant="destructive"
        size="sm"
        class="gap-1.5"
        :disabled="!selected.size || loading"
        @click="removeSelected"
      >
        <Trash2 class="h-3.5 w-3.5" />
        删除选中
      </Button>
      <Button variant="secondary" size="sm" class="gap-1.5" type="button" @click="goAllHistory">
        <History class="h-3.5 w-3.5" />
        全部批量历史
      </Button>
      <span
        v-if="selected.size"
        class="text-[11px] text-muted-foreground ml-auto"
      >
        已选 {{ selected.size }}（当前筛选内 {{ selectedInView }}）
      </span>
    </div>

    <div class="grid gap-5 xl:grid-cols-[1fr,min(360px,34%)] xl:items-start">
      <div class="space-y-3 min-w-0">
        <div
          v-if="filteredTasks.length"
          class="grid gap-3 sm:grid-cols-2"
        >
          <article
            v-for="t in filteredTasks"
            :key="t.task_id"
            :class="
              cn(
                'group relative flex flex-col rounded-xl border bg-card overflow-hidden transition-all',
                selected.has(t.task_id)
                  ? 'border-primary shadow-sm ring-1 ring-primary/25'
                  : 'border-border hover:border-primary/30 hover:shadow-sm',
                historyTaskId === t.task_id && 'ring-2 ring-primary/35',
              )
            "
          >
            <div class="flex items-start gap-3 p-4 pb-2">
              <input
                type="checkbox"
                class="mt-1 rounded border-input shrink-0"
                :checked="selected.has(t.task_id)"
                @click.stop
                @change="toggle(t.task_id, $event)"
              />
              <div class="flex-1 min-w-0 space-y-1.5">
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="font-semibold text-sm leading-snug truncate" :title="t.name">
                    {{ t.name || '未命名任务' }}
                  </h3>
                  <Badge :variant="statusVariant[t.status] || 'outline'" class="text-[10px] shrink-0">
                    {{ statusLabelTask(t.status) }}
                  </Badge>
                </div>
                <p class="text-xs text-muted-foreground flex items-center gap-1 truncate">
                  <Layers class="h-3 w-3 shrink-0 opacity-70" />
                  {{ workflowLabel(t) }}
                </p>
                <div class="flex flex-wrap gap-1.5">
                  <Badge variant="secondary" class="text-[10px] font-normal">
                    {{ t.planned_total }} 张
                  </Badge>
                  <Badge
                    v-if="t.has_batch_prompts"
                    variant="outline"
                    class="text-[10px] font-normal gap-0.5"
                  >
                    <Sparkles class="h-2.5 w-2.5" />
                    含提示词
                  </Badge>
                  <Badge variant="outline" class="text-[10px] font-mono font-normal opacity-80">
                    {{ t.task_id }}
                  </Badge>
                </div>
                <p class="text-[10px] text-muted-foreground flex items-center gap-1">
                  <Calendar class="h-3 w-3 shrink-0" />
                  <template v-if="t.executed_at">执行 {{ formatTime(t.executed_at) }}</template>
                  <template v-else-if="t.created_at">创建 {{ formatTime(t.created_at) }}</template>
                </p>
              </div>
            </div>

            <div
              class="mt-auto flex border-t border-border/80 divide-x divide-border/80"
            >
              <button
                v-if="t.status === 'completed' || (t.batch_ids && t.batch_ids.length)"
                type="button"
                class="flex-1 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
                @click.stop="openTaskHistory(t, $event)"
              >
                查看历史
              </button>
              <button
                type="button"
                class="flex-1 py-2 text-xs text-destructive hover:bg-destructive/10 transition-colors"
                @click.stop="removeTask(t.task_id, $event)"
              >
                删除
              </button>
            </div>
          </article>
        </div>

        <Card v-else-if="tasks.length">
          <CardContent class="py-10 text-center text-sm text-muted-foreground">
            没有符合筛选条件的任务，请调整筛选或
            <button
              type="button"
              class="text-primary underline"
              @click="
                Object.assign(filters, {
                  search: '',
                  status: '',
                  workflow: '',
                  hasPrompts: '',
                  sort: 'created_desc',
                })
              "
            >
              重置筛选
            </button>
          </CardContent>
        </Card>

        <Card v-else>
          <CardContent class="py-12 text-center space-y-2">
            <ListTodo class="h-10 w-10 mx-auto text-muted-foreground/40" />
            <p class="text-sm text-muted-foreground">暂无任务</p>
            <p class="text-xs text-muted-foreground">
              在
              <RouterLink to="/generate?mode=sweep" class="text-primary underline">生成页</RouterLink>
              保存扫参任务，或运行
              <code class="text-[10px]">scripts/seed_lora_batch_tasks.py</code>
            </p>
          </CardContent>
        </Card>
      </div>

      <Card v-if="historyTaskId" class="xl:sticky xl:top-20">
        <CardHeader class="pb-2">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <CardTitle class="text-base truncate">{{ historyTaskName }}</CardTitle>
              <CardDescription class="font-mono text-[10px] truncate">
                {{ historyTaskId }}
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" class="h-7 shrink-0" @click="closeHistory">关闭</Button>
          </div>
        </CardHeader>
        <CardContent class="space-y-2 max-h-[min(70vh,520px)] overflow-y-auto">
          <p v-if="batchesLoading" class="text-sm text-muted-foreground py-4 text-center">加载中…</p>
          <template v-else-if="taskBatches.length">
            <button
              v-for="b in taskBatches"
              :key="b.batch_id"
              type="button"
              class="flex w-full items-center gap-3 rounded-lg border border-border px-3 py-2 text-left hover:bg-accent/50 transition-colors"
              @click="viewBatchInHistory(b.batch_id, $event)"
            >
              <div class="h-14 w-14 shrink-0 rounded-md bg-muted overflow-hidden border border-border/60">
                <img
                  v-if="b.thumbnail_url"
                  :src="b.thumbnail_url"
                  class="h-full w-full object-cover"
                  alt=""
                  loading="lazy"
                />
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-mono text-[11px] truncate">{{ b.batch_id }}</p>
                <p class="text-[10px] text-muted-foreground mt-0.5">
                  {{ statusLabel(b.status) }} · {{ b.completed }}/{{ b.total }}
                </p>
              </div>
            </button>
          </template>
          <p v-else class="text-sm text-muted-foreground py-6 text-center">该任务尚无批量记录</p>
        </CardContent>
      </Card>

      <Card v-else class="hidden xl:block border-dashed bg-muted/10">
        <CardContent class="py-16 text-center text-sm text-muted-foreground">
          点击任务的「查看历史」在此显示批次列表
        </CardContent>
      </Card>
    </div>
  </div>
</template>
