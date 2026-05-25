<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronDown, ChevronUp, ListOrdered, X } from 'lucide-vue-next'
import { useGenerateQueueStore } from '@/stores/useGenerateQueueStore.js'
import Button from '@/components/ui/Button.vue'
import Progress from '@/components/ui/Progress.vue'
import { cn } from '@/lib/utils'

const STORAGE_KEY = 'custom_project_queue_dock_expanded'

function readExpanded() {
  try {
    return localStorage.getItem(STORAGE_KEY) !== '0'
  } catch {
    return true
  }
}

const queue = useGenerateQueueStore()
const expanded = ref(readExpanded())

watch(expanded, (v) => {
  try {
    localStorage.setItem(STORAGE_KEY, v ? '1' : '0')
  } catch {
    /* ignore */
  }
})

const hasQueue = computed(() => queue.items.length > 0)

const running = computed(() => queue.runningItem())

const pendingCount = computed(() => queue.pendingItems().length)

const collapsedSummary = computed(() => {
  if (running.value) {
    return `${running.value.label} · ${queue.progressLabel(running.value)}`
  }
  if (pendingCount.value > 0) {
    return `${pendingCount.value} 项排队等待`
  }
  const done = queue.items.filter((i) => i.status === 'completed').length
  const failed = queue.items.filter((i) => i.status === 'failed').length
  if (failed) return `${failed} 项失败 · ${done} 项完成`
  return `${queue.items.length} 项已结束`
})

const runningProgress = computed(() => {
  if (!running.value) return 0
  const it = running.value
  if (it.type === 'batch' && it.batchTotal > 0) {
    return it.progress ?? Math.round((100 * (it.batchCompleted ?? 0)) / it.batchTotal)
  }
  return it.progress ?? 0
})

function toggleExpanded() {
  expanded.value = !expanded.value
}

const statusText = (item) => {
  if (item.status === 'pending') return '排队中'
  if (item.status === 'running') return '执行中'
  if (item.status === 'completed') return '已完成'
  if (item.status === 'failed') return '失败'
  if (item.status === 'cancelled') return '已取消'
  return item.status
}

const statusClass = (item) => {
  if (item.status === 'running') return 'text-primary'
  if (item.status === 'pending') return 'text-amber-600 dark:text-amber-400'
  if (item.status === 'failed') return 'text-destructive'
  if (item.status === 'completed') return 'text-emerald-600 dark:text-emerald-400'
  return 'text-muted-foreground'
}
</script>

<template>
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0 translate-y-2"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100 translate-y-0"
    leave-to-class="opacity-0 translate-y-2"
  >
    <div
      v-if="hasQueue"
      class="fixed bottom-4 left-4 z-[70] w-[min(100vw-2rem,22rem)] pointer-events-auto"
      role="region"
      aria-label="生成队列"
    >
      <div
        class="overflow-hidden rounded-lg border border-border bg-card/95 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-card/88"
      >
        <div
          class="flex items-center gap-2 border-b border-border/60 px-3 py-2"
          :class="expanded ? '' : 'border-b-0'"
        >
          <button
            type="button"
            class="flex min-w-0 flex-1 items-center gap-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
            :aria-expanded="expanded"
            @click="toggleExpanded"
          >
            <ListOrdered class="h-4 w-4 shrink-0 text-primary" />
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium leading-tight">生成队列</p>
              <p
                v-if="!expanded"
                class="truncate text-[11px] text-muted-foreground leading-snug"
              >
                {{ collapsedSummary }}
              </p>
              <p v-else class="text-[11px] text-muted-foreground leading-snug">
                <span v-if="running">执行中</span>
                <span v-if="running && pendingCount"> · </span>
                <span v-if="pendingCount">{{ pendingCount }} 项等待</span>
                <span v-if="!running && !pendingCount">{{ queue.items.length }} 项</span>
              </p>
            </div>
            <ChevronUp
              v-if="expanded"
              class="h-4 w-4 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
            <ChevronDown
              v-else
              class="h-4 w-4 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
          </button>
          <Button
            v-if="expanded"
            variant="ghost"
            size="sm"
            class="h-7 shrink-0 px-2 text-xs"
            @click.stop="queue.clearFinished()"
          >
            清除已完成
          </Button>
        </div>

        <Progress
          v-if="!expanded && running"
          class="h-1 rounded-none"
          :value="runningProgress"
        />

        <div
          v-show="expanded"
          class="max-h-[min(50vh,16rem)] overflow-y-auto p-3 pt-2"
        >
          <ul class="space-y-2">
            <li
              v-for="item in queue.items"
              :key="item.id"
              :class="
                cn(
                  'rounded-md border border-border/80 px-2.5 py-2',
                  item.status === 'running' && 'border-primary/40 bg-primary/5',
                )
              "
            >
              <div class="flex items-start gap-2">
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-medium">{{ item.label }}</p>
                  <p :class="cn('text-xs', statusClass(item))">
                    {{ statusText(item) }}
                    <span
                      v-if="item.status === 'running' || item.status === 'completed'"
                    >
                      · {{ queue.progressLabel(item) }}
                    </span>
                  </p>
                  <p v-if="item.error" class="mt-0.5 text-xs text-destructive">
                    {{ item.error }}
                  </p>
                </div>
                <div class="flex shrink-0 flex-col gap-0.5">
                  <template v-if="item.status === 'pending'">
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-7 w-7"
                      title="上移"
                      @click="queue.movePending(item.id, -1)"
                    >
                      <ChevronUp class="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-7 w-7"
                      title="下移"
                      @click="queue.movePending(item.id, 1)"
                    >
                      <ChevronDown class="h-4 w-4" />
                    </Button>
                  </template>
                  <Button
                    v-if="item.status === 'pending' || item.status === 'running'"
                    variant="ghost"
                    size="icon"
                    class="h-7 w-7 text-destructive hover:text-destructive"
                    title="取消"
                    @click="queue.cancelItem(item.id)"
                  >
                    <X class="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <Progress
                v-if="item.status === 'running'"
                class="mt-2 h-1.5"
                :value="
                  item.type === 'batch' && item.batchTotal
                    ? item.progress
                    : item.progress
                "
              />
            </li>
          </ul>
        </div>
      </div>
    </div>
  </Transition>
</template>
