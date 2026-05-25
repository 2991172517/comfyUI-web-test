<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ChevronRight, Check, Loader2 } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import { pipelineNodeStatus } from '@/composables/usePipelineNodeStatus.js'
import Badge from '@/components/ui/Badge.vue'
import Label from '@/components/ui/Label.vue'

const props = defineProps({
  /** @type {{ node_id: string, title: string, class_type: string, is_preview?: boolean, is_save?: boolean }[]} */
  nodes: { type: Array, default: () => [] },
  /** config：可勾选预览；progress：仅展示进度 */
  mode: { type: String, default: 'config' },
  disabled: { type: Boolean, default: false },
  enabledPreviewIds: { type: Array, default: () => [] },
  currentNodeId: { type: [String, Number], default: null },
  completedNodeIds: { type: Array, default: () => [] },
  jobStatus: { type: String, default: 'idle' },
  /** 节点 ID → 该节点输出图（用于预览节点下方点击查看） */
  imagesByNode: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['toggle-preview', 'view-node-images'])

const enabledSet = computed(() => new Set((props.enabledPreviewIds || []).map(String)))

function isPreviewEnabled(nodeId) {
  return enabledSet.value.has(String(nodeId))
}

const trackNodeIds = computed(() =>
  (props.nodes || []).map((n) => String(n.node_id)),
)

function statusOf(node) {
  if (props.mode !== 'progress') return null
  return pipelineNodeStatus(
    node.node_id,
    props.currentNodeId,
    props.completedNodeIds,
    props.jobStatus,
    trackNodeIds.value,
  )
}

function cardClass(node) {
  const st = statusOf(node)
  if (props.mode !== 'progress') {
    return cn(
      'min-w-[140px] max-w-[200px] shrink-0 rounded-lg border-2 px-3 py-2.5 transition-colors',
      node.is_preview
        ? isPreviewEnabled(node.node_id)
          ? 'border-primary/35 bg-primary/5'
          : 'border-border/40 bg-muted/10 opacity-70'
        : 'border-border bg-card',
    )
  }
  return cn(
    'min-w-[120px] max-w-[180px] shrink-0 rounded-lg border-2 px-2.5 py-2 transition-all duration-300',
    st === 'active' &&
      'border-primary bg-primary/10 shadow-md ring-2 ring-primary/35 scale-[1.02]',
    st === 'done' && 'border-emerald-600/55 bg-emerald-500/8',
    st === 'pending' && 'border-border/45 bg-muted/15 opacity-55',
  )
}

function badgeFor(node) {
  if (node.is_save) return { text: '终图', variant: 'success' }
  if (node.is_preview) return { text: '预览', variant: 'secondary' }
  return null
}

function onTogglePreview(node) {
  if (props.disabled || props.mode !== 'config' || !node.is_preview) return
  emit('toggle-preview', node.node_id)
}

function imagesForNode(nodeId) {
  const list = props.imagesByNode?.[String(nodeId)]
  return Array.isArray(list) ? list : []
}

function viewNodeImages(node) {
  const imgs = imagesForNode(node.node_id)
  if (!imgs.length) return
  emit('view-node-images', { nodeId: node.node_id, images: imgs })
}

const scrollRef = ref(null)

/** 进度条自动滚动目标：优先当前节点，否则最后一个已完成节点 */
const scrollTargetId = computed(() => {
  if (props.mode !== 'progress') return null
  if (props.currentNodeId != null && String(props.currentNodeId) !== '') {
    return String(props.currentNodeId)
  }
  const done = props.completedNodeIds || []
  if (done.length) return String(done[done.length - 1])
  return null
})

async function scrollToProgressTarget(behavior = 'smooth') {
  const container = scrollRef.value
  const id = scrollTargetId.value
  if (!container || !id) return

  await nextTick()
  const el = [...container.querySelectorAll('[data-pipeline-node]')].find(
    (n) => n.getAttribute('data-pipeline-node') === id,
  )
  if (!el || !(el instanceof HTMLElement)) return

  const targetLeft = el.offsetLeft + el.offsetWidth / 2 - container.clientWidth / 2
  const maxScroll = Math.max(0, container.scrollWidth - container.clientWidth)
  container.scrollTo({
    left: Math.min(maxScroll, Math.max(0, targetLeft)),
    behavior,
  })
}

watch(
  scrollTargetId,
  (id) => {
    if (!id || props.mode !== 'progress') return
    if (!['pending', 'in_progress', 'finalizing', 'completed'].includes(props.jobStatus)) return
    scrollToProgressTarget('smooth')
  },
)

watch(
  () => props.nodes?.length,
  () => {
    if (props.mode === 'progress' && scrollTargetId.value) {
      scrollToProgressTarget('auto')
    }
  },
)
</script>

<template>
  <div class="space-y-3">
    <div
      v-if="!nodes.length"
      class="rounded-md border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground"
    >
      暂无流水线节点
    </div>

    <div
      v-else
      ref="scrollRef"
      class="overflow-x-auto pb-2 -mx-1 px-1 scroll-smooth"
      :class="mode === 'progress' ? 'snap-x snap-mandatory' : ''"
    >
      <div class="flex min-w-min items-stretch gap-0">
        <template
          v-for="(node, index) in nodes"
          :key="node.node_id"
        >
          <div
            class="flex shrink-0 flex-col items-center gap-1"
            :class="mode === 'progress' ? 'snap-center' : ''"
            :data-pipeline-node="String(node.node_id)"
          >
            <div
              :class="cardClass(node)"
              :title="`#${node.node_id} ${node.class_type}`"
            >
              <div class="flex items-start gap-2">
                <div
                  v-if="mode === 'config' && node.is_preview"
                  class="pt-0.5"
                >
                  <input
                    :id="`pf-${node.node_id}`"
                    type="checkbox"
                    class="h-3.5 w-3.5 rounded border-border"
                    :checked="isPreviewEnabled(node.node_id)"
                    :disabled="disabled"
                    @change="onTogglePreview(node)"
                  />
                </div>
                <div
                  v-else-if="mode === 'progress'"
                  class="flex h-5 w-5 shrink-0 items-center justify-center"
                >
                  <Loader2
                    v-if="statusOf(node) === 'active'"
                    class="h-4 w-4 animate-spin text-primary"
                  />
                  <Check
                    v-else-if="statusOf(node) === 'done'"
                    class="h-4 w-4 text-emerald-600"
                  />
                  <span
                    v-else
                    class="h-2 w-2 rounded-full bg-muted-foreground/35"
                  />
                </div>

                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-1">
                    <span class="text-[10px] font-medium tabular-nums text-muted-foreground">
                      {{ index + 1 }}
                    </span>
                    <Badge
                      v-if="badgeFor(node)"
                      :variant="badgeFor(node).variant"
                      class="text-[9px] px-1 py-0 leading-none"
                    >
                      {{ badgeFor(node).text }}
                    </Badge>
                  </div>
                  <Label
                    :for="mode === 'config' && node.is_preview ? `pf-${node.node_id}` : undefined"
                    class="mt-0.5 block text-xs font-medium leading-snug text-foreground line-clamp-2"
                    :class="mode === 'config' && node.is_preview && !disabled ? 'cursor-pointer' : ''"
                  >
                    {{ node.title }}
                  </Label>
                  <p class="mt-0.5 text-[10px] text-muted-foreground truncate">
                    #{{ node.node_id }}
                  </p>
                </div>
              </div>
            </div>

            <button
              v-if="mode === 'progress' && node.is_preview && imagesForNode(node.node_id).length"
              type="button"
              class="text-[10px] text-primary hover:underline whitespace-nowrap px-1"
              @click="viewNodeImages(node)"
            >
              点击查看
              <span v-if="imagesForNode(node.node_id).length > 1">
                （{{ imagesForNode(node.node_id).length }} 张）
              </span>
            </button>
          </div>

          <div
            v-if="index < nodes.length - 1"
            class="flex shrink-0 items-center self-center px-1 pt-3 text-muted-foreground/50"
            aria-hidden="true"
          >
            <ChevronRight class="h-5 w-5" />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
