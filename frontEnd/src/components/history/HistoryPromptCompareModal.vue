<script setup>
import { computed } from 'vue'
import Button from '@/components/ui/Button.vue'
import { comparePromptItems } from '@/lib/promptCompare.js'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  items: { type: Array, default: () => [] },
})

const emit = defineEmits(['close'])

const result = computed(() => comparePromptItems(props.items))

function sideTitle(side) {
  return side === 'positive' ? '正向' : '负向'
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && items.length >= 2"
      class="fixed inset-0 z-[110] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      @click.self="emit('close')"
    >
      <div
        class="flex max-h-[min(92vh,920px)] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        @click.stop
      >
        <header class="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h2 class="text-base font-semibold">提示词对比</h2>
            <p class="text-xs text-muted-foreground">
              已选 {{ result.count }} 张 ·
              {{ items.map((i) => i.label).join('、') }}
            </p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 p-0" @click="emit('close')">
            <X class="h-4 w-4" />
          </Button>
        </header>

        <div class="min-h-0 flex-1 space-y-6 overflow-y-auto p-4">
          <section
            v-for="side in ['positive', 'negative']"
            :key="side"
            class="space-y-3 rounded-lg border border-border/70 bg-muted/15 p-3"
          >
            <h3 class="text-sm font-medium text-foreground">
              {{ sideTitle(side) }}提示词
              <span
                v-if="result[side]?.allFullSame"
                class="ml-2 text-xs font-normal text-emerald-600"
              >
                全文一致
              </span>
              <span v-else class="ml-2 text-xs font-normal text-amber-600">存在差异</span>
            </h3>

            <template v-if="result[side]">
              <div v-if="result[side].sameSegments.length" class="space-y-1">
                <p class="text-xs font-medium text-emerald-700/90">相同片段（{{ result[side].sameSegments.length }}）</p>
                <p class="rounded-md bg-emerald-500/10 px-2 py-1.5 text-[11px] leading-relaxed text-foreground">
                  {{ result[side].sameSegments.join(', ') }}
                </p>
              </div>
              <p v-else class="text-xs text-muted-foreground">无共同片段</p>

              <div v-if="result[side].differentSegments.length" class="space-y-2">
                <p class="text-xs font-medium text-amber-700/90">
                  不同片段（{{ result[side].differentSegments.length }}）
                </p>
                <ul class="space-y-2">
                  <li
                    v-for="(diff, di) in result[side].differentSegments"
                    :key="di"
                    class="rounded-md border border-amber-500/25 bg-amber-500/5 px-2 py-1.5 text-[11px]"
                  >
                    <p class="leading-relaxed text-foreground">{{ diff.text }}</p>
                    <p class="mt-1 text-muted-foreground">
                      出现于：{{ diff.labels.join('、') }}
                    </p>
                  </li>
                </ul>
              </div>
              <p v-else-if="result[side].allFullSame" class="text-xs text-muted-foreground">
                各张图该方向提示词完全相同
              </p>

              <details class="text-xs">
                <summary class="cursor-pointer text-muted-foreground hover:text-foreground">
                  各张完整提示词
                </summary>
                <ul class="mt-2 space-y-2">
                  <li
                    v-for="row in result[side].perItem"
                    :key="row.key"
                    class="rounded border border-border/60 bg-background/80 p-2"
                  >
                    <p class="mb-1 font-medium text-foreground/90">{{ row.label }}</p>
                    <p class="font-mono text-[11px] leading-relaxed break-words">{{ row.full || '—' }}</p>
                    <p
                      v-if="row.uniqueSegments.length && !result[side].allFullSame"
                      class="mt-1 text-[10px] text-amber-700/80"
                    >
                      独有片段：{{ row.uniqueSegments.join(', ') }}
                    </p>
                  </li>
                </ul>
              </details>
            </template>
          </section>
        </div>

        <footer class="shrink-0 border-t border-border px-4 py-3 text-right">
          <Button variant="outline" size="sm" @click="emit('close')">关闭</Button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
