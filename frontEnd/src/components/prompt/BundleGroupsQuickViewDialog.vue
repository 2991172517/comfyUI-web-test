<script setup>
import { computed, ref, toRef, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { useModalMotion } from '@/composables/useModalMotion.js'
import {
  globalConfigToPromptLayers,
  normalizePromptConfig,
} from '@/composables/usePromptConfig.js'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open'])

const app = useAppStore()
const backdropRef = ref(null)
const panelRef = ref(null)
const loading = ref(false)
const globalGroups = ref([])

useModalMotion(toRef(() => props.open), backdropRef, panelRef)

const sessionGroups = computed(
  () => normalizePromptConfig(app.sessionPrompts).random_bundle_groups || [],
)

const totalBundles = computed(() => {
  let n = 0
  for (const g of [...globalGroups.value, ...sessionGroups.value]) {
    n += (g.bundles || []).filter((b) => String(b.text || '').trim()).length
  }
  return n
})

async function loadGlobal() {
  loading.value = true
  try {
    const res = await api.getGlobalPromptConfig()
    const cfg = globalConfigToPromptLayers(res.config)
    globalGroups.value = cfg.random_bundle_groups || []
  } catch (e) {
    app.setMessage(e.message, true)
    globalGroups.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) loadGlobal()
  },
)

function close() {
  emit('update:open', false)
}

function onBackdrop(e) {
  if (e.target === e.currentTarget) close()
}

function previewText(text, max = 120) {
  const s = String(text || '').trim()
  if (s.length <= max) return s
  return `${s.slice(0, max)}…`
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="backdropRef"
      class="fixed inset-0 z-[95] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      @click="onBackdrop"
    >
      <div
        ref="panelRef"
        class="flex max-h-[min(88vh,640px)] w-full max-w-lg flex-col rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="bundle-quick-title"
        @click.stop
      >
        <header class="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 id="bundle-quick-title" class="text-base font-semibold">随机词串组</h2>
            <p class="mt-0.5 text-xs text-muted-foreground">
              全局 + 当次，共 {{ totalBundles }} 条词条组
              <span v-if="loading"> · 加载中…</span>
            </p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 p-0" @click="close">
            <X class="h-4 w-4" />
          </Button>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto px-4 py-3 space-y-4">
          <section>
            <h3 class="mb-2 text-xs font-medium text-muted-foreground">全局词串组</h3>
            <p v-if="!loading && !globalGroups.length" class="text-xs text-muted-foreground">
              未配置全局词串组
            </p>
            <div v-else class="space-y-2">
              <article
                v-for="g in globalGroups"
                :key="g.id"
                :class="
                  cn(
                    'rounded-md border px-2.5 py-2 text-xs',
                    g.enabled !== false
                      ? 'border-violet-400/30 bg-violet-500/5'
                      : 'border-border/60 opacity-70',
                  )
                "
              >
                <div class="flex flex-wrap items-center gap-1.5 mb-1.5">
                  <span class="font-medium">{{ g.name || '未命名' }}</span>
                  <Badge variant="outline" class="text-[10px]">
                    {{ g.target === 'negative' ? '负向' : '正向' }}
                  </Badge>
                  <Badge
                    :variant="g.enabled !== false ? 'secondary' : 'outline'"
                    class="text-[10px]"
                  >
                    {{ g.enabled !== false ? '已启用' : '已关闭' }}
                  </Badge>
                </div>
                <ul class="space-y-1">
                  <li
                    v-for="b in g.bundles"
                    :key="b.id"
                    class="rounded bg-muted/30 px-2 py-1 font-mono text-[11px] leading-snug"
                  >
                    <span class="text-foreground font-sans font-medium">{{ b.alias }}</span>
                    <span class="text-muted-foreground"> · </span>
                    <span class="text-muted-foreground">{{
                      previewText(b.text) || '（空）'
                    }}</span>
                  </li>
                </ul>
              </article>
            </div>
          </section>

          <section>
            <h3 class="mb-2 text-xs font-medium text-muted-foreground">当次词串组</h3>
            <p v-if="!sessionGroups.length" class="text-xs text-muted-foreground">
              当次未添加词串组
            </p>
            <div v-else class="space-y-2">
              <article
                v-for="g in sessionGroups"
                :key="g.id"
                :class="
                  cn(
                    'rounded-md border px-2.5 py-2 text-xs',
                    g.enabled !== false
                      ? 'border-primary/30 bg-primary/5'
                      : 'border-border/60 opacity-70',
                  )
                "
              >
                <div class="flex flex-wrap items-center gap-1.5 mb-1.5">
                  <span class="font-medium">{{ g.name || '未命名' }}</span>
                  <Badge variant="outline" class="text-[10px]">当次</Badge>
                  <Badge
                    :variant="g.enabled !== false ? 'secondary' : 'outline'"
                    class="text-[10px]"
                  >
                    {{ g.enabled !== false ? '已启用' : '已关闭' }}
                  </Badge>
                </div>
                <ul class="space-y-1">
                  <li
                    v-for="b in g.bundles"
                    :key="b.id"
                    class="rounded bg-muted/30 px-2 py-1 font-mono text-[11px] leading-snug"
                  >
                    <span class="text-foreground font-sans font-medium">{{ b.alias }}</span>
                    <span class="text-muted-foreground"> · </span>
                    <span class="text-muted-foreground">{{
                      previewText(b.text) || '（空）'
                    }}</span>
                  </li>
                </ul>
              </article>
            </div>
          </section>
        </div>

        <footer class="flex shrink-0 justify-end border-t border-border px-4 py-3">
          <Button size="sm" @click="close">关闭</Button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
