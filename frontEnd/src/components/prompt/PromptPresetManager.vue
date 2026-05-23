<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { PROMPT_AUTO_SAVE_DEBOUNCE_MS, useDebouncedSave } from '@/composables/useDebouncedSave.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Switch from '@/components/ui/Switch.vue'
import PromptTextarea from '@/components/prompt/PromptTextarea.vue'
import Badge from '@/components/ui/Badge.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import PromptConfigEditor from '@/components/prompt/PromptConfigEditor.vue'
import {
  clonePromptConfig,
  emptyBatchPromptConfig,
  normalizePromptConfig,
  serializePromptConfig,
} from '@/composables/usePromptConfig.js'
import { cn } from '@/lib/utils'
import { isAdmin } from '@/composables/useAuth.js'

defineProps({
  embedded: { type: Boolean, default: false },
})

const app = useAppStore()
const presets = ref([])
const selectedId = ref('')
const draft = ref(emptyBatchPromptConfig())
const draftName = ref('')
const draftDesc = ref('')
const suppressSave = ref(true)

const isNew = ref(true)

async function refresh() {
  const res = await api.listPromptPresets()
  presets.value = res.presets || []
}

async function persistPreset() {
  if (!draftName.value.trim()) return
  const body = {
    name: draftName.value.trim(),
    description: draftDesc.value.trim(),
    ...serializePromptConfig(draft.value),
  }
  if (isNew.value) {
    const res = await api.createPromptPreset(body)
    await refresh()
    suppressSave.value = true
    isNew.value = false
    selectedId.value = res.preset.id
    draftName.value = res.preset.name
    draftDesc.value = res.preset.description || ''
    draft.value = clonePromptConfig(normalizePromptConfig(res.preset))
    await nextTick()
    suppressSave.value = false
  } else {
    await api.updatePromptPreset(selectedId.value, body)
    await refresh()
  }
}

const { saving, pending, markReady, schedule, flush } = useDebouncedSave(persistPreset, {
  delay: PROMPT_AUTO_SAVE_DEBOUNCE_MS,
})

async function selectPreset(p) {
  suppressSave.value = true
  markReady(false)
  if (!p) {
    isNew.value = true
    selectedId.value = ''
    draftName.value = ''
    draftDesc.value = ''
    draft.value = emptyBatchPromptConfig()
  } else {
    isNew.value = false
    selectedId.value = p.id
    draftName.value = p.name
    draftDesc.value = p.description || ''
    draft.value = clonePromptConfig(normalizePromptConfig(p))
  }
  await nextTick()
  suppressSave.value = false
  markReady(true)
}

async function startNew() {
  await selectPreset(null)
  draftName.value = '新预设'
}

async function removePresetById(p) {
  if (!p?.id) return
  if (!confirm(`删除预设「${p.name}」？`)) return
  suppressSave.value = true
  markReady(false)
  try {
    await api.deletePromptPreset(p.id)
    await refresh()
    if (selectedId.value === p.id) {
      if (presets.value.length) await selectPreset(presets.value[0])
      else await startNew()
    }
    app.setMessage('预设已删除')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    suppressSave.value = false
    markReady(true)
  }
}

function rowSelected(p) {
  return !isNew.value && selectedId.value === p.id
}

watch(
  [draft, draftName, draftDesc],
  () => {
    if (suppressSave.value) return
    schedule()
  },
  { deep: true },
)

onMounted(async () => {
  try {
    await refresh()
    if (presets.value.length) await selectPreset(presets.value[0])
    else await startNew()
  } catch (e) {
    app.setMessage(e.message, true)
  }
})

defineExpose({ flush })
</script>

<template>
  <component :is="embedded ? 'div' : Card" :class="embedded ? 'space-y-3' : undefined">
    <CardHeader v-if="!embedded" class="pb-2">
      <CardTitle class="text-base">提示词预设</CardTitle>
      <CardDescription>
        左侧选择预设，右侧编辑细节；修改后自动保存。抽卡/批量页通过「导入预设」载入。
      </CardDescription>
    </CardHeader>
    <p v-else class="text-xs text-muted-foreground">
      点击左侧预设编辑；修改后自动保存（约 {{ PROMPT_AUTO_SAVE_DEBOUNCE_MS / 1000 }} 秒防抖）。
      <span v-if="pending && !saving" class="text-muted-foreground">待保存…</span>
      <span v-else-if="saving" class="text-primary">保存中…</span>
    </p>

    <component :is="embedded ? 'div' : CardContent">
      <div class="grid gap-4 lg:grid-cols-[minmax(200px,240px)_1fr] min-h-[min(420px,65vh)]">
        <!-- 左侧列表 -->
        <aside
          class="flex flex-col rounded-lg border border-border bg-muted/10 overflow-hidden"
        >
          <div class="p-2 border-b border-border shrink-0">
            <Button class="w-full h-10 text-sm font-medium" @click="startNew">
              + 新增预设
            </Button>
          </div>

          <div class="flex-1 overflow-y-auto p-2 space-y-1 min-h-0">
            <div
              v-if="isNew"
              :class="
                cn(
                  'rounded-md border px-2 py-2 text-sm border-primary bg-primary/10',
                )
              "
            >
              <div class="font-medium truncate text-primary">新预设</div>
              <div class="text-[10px] text-muted-foreground mt-0.5">填写右侧后自动创建</div>
            </div>

            <div
              v-for="p in presets"
              :key="p.id"
              :class="
                cn(
                  'flex items-center gap-1 rounded-md border transition-colors',
                  rowSelected(p)
                    ? 'border-primary bg-primary/10'
                    : 'border-transparent hover:border-border hover:bg-accent/50',
                )
              "
            >
              <button
                type="button"
                class="flex-1 min-w-0 text-left px-2 py-2 text-sm"
                @click="selectPreset(p)"
              >
                <div class="font-medium truncate">{{ p.name }}</div>
                <div class="text-[10px] text-muted-foreground mt-0.5">
                  {{ p.random_group_count }} 随机组
                </div>
              </button>
              <IconDeleteButton
                v-if="isAdmin()"
                size="sm"
                class="mr-1"
                title="删除预设"
                @click="removePresetById(p)"
              />
            </div>

            <p
              v-if="!presets.length && !isNew"
              class="text-xs text-muted-foreground text-center py-6 px-2"
            >
              暂无预设
            </p>
          </div>
        </aside>

        <!-- 右侧细节 -->
        <section class="min-w-0 space-y-3 overflow-y-auto max-h-[min(65vh,560px)] pr-1">
          <div class="flex flex-wrap items-center gap-2 border-b border-border/60 pb-2">
            <h3 class="text-sm font-semibold truncate flex-1">
              {{ isNew ? '新建预设' : draftName || '预设详情' }}
            </h3>
            <Badge v-if="isNew" variant="outline" class="text-[10px] shrink-0">未保存</Badge>
            <Badge v-else-if="saving" variant="secondary" class="text-[10px] shrink-0">保存中…</Badge>
          </div>

          <div class="flex flex-wrap items-end gap-2">
            <div class="flex-1 min-w-[140px] space-y-1">
              <Label class="text-xs">名称</Label>
              <Input v-model="draftName" class="h-8 text-sm" placeholder="例：修女丝袜" />
            </div>
            <div class="flex-[2] min-w-[200px] space-y-1">
              <Label class="text-xs">说明</Label>
              <Input v-model="draftDesc" class="h-8 text-sm" placeholder="可选" />
            </div>
          </div>

          <div class="grid gap-2 lg:grid-cols-2">
            <div class="space-y-1">
              <Label class="text-xs">正向全文</Label>
              <PromptTextarea v-model="draft.positive" :rows="5" class="text-xs font-mono" placeholder="可选" />
            </div>
            <div class="space-y-1">
              <Label class="text-xs">负向全文</Label>
              <PromptTextarea v-model="draft.negative" :rows="5" class="text-xs font-mono" />
            </div>
          </div>

          <div class="flex flex-wrap gap-3 text-[11px]">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <Switch v-model="draft.merge.global_before_workflow" size="sm" />
              全局全文在工作流底稿前
            </label>
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <Switch v-model="draft.merge.random_before_workflow" size="sm" />
              随机词在工作流底稿前
            </label>
          </div>

          <PromptConfigEditor
            :fixed="draft.fixed"
            :random-groups="draft.random_groups"
            :show-fixed="true"
            :show-random="true"
            compact
            @update:fixed="draft.fixed = $event"
            @update:random-groups="draft.random_groups = $event"
          />
        </section>
      </div>
    </component>
  </component>
</template>
