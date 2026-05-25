<script setup>
import { computed, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { useModalMotion } from '@/composables/useModalMotion.js'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import {
  DEFAULT_WORKFLOW_CATEGORY,
  WORKFLOW_CATEGORIES,
  normalizeCategory,
} from '@/lib/workflowCategories.js'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'

const props = defineProps({
  workflows: { type: Array, default: () => [] },
})

const open = defineModel('open', { type: Boolean, default: false })

const emit = defineEmits(['created'])

const app = useAppStore()
const name = ref('')
const category = ref(DEFAULT_WORKFLOW_CATEGORY)
const copyFrom = ref('')
const busy = ref(false)

const copyOptions = computed(() =>
  (props.workflows || []).filter((w) => w.is_variant && w.format === 'api'),
)

watch(open, (v) => {
  if (v) {
    name.value = ''
    category.value = DEFAULT_WORKFLOW_CATEGORY
    copyFrom.value = ''
  }
})

const backdropRef = ref(null)
const panelRef = ref(null)
useModalMotion(open, backdropRef, panelRef)

function close() {
  open.value = false
}

function onBackdrop(e) {
  if (e.target === e.currentTarget) close()
}

async function submit() {
  busy.value = true
  try {
    const res = await api.createWorkflowVariant({
      display_name: name.value.trim() || undefined,
      category: normalizeCategory(category.value),
      copy_from_workflow_id: copyFrom.value || undefined,
    })
    name.value = ''
    emit('created', res)
    close()
    app.setMessage(
      copyFrom.value
        ? '已从所选工作流复制，可在右侧编辑'
        : '已创建空白工作流，可在右侧编辑 Checkpoint / LoRA',
    )
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="backdropRef"
      class="fixed inset-0 z-[90] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      @click="onBackdrop"
    >
      <div
        ref="panelRef"
        class="w-full max-w-md rounded-xl border border-border bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        @click.stop
      >
        <header class="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 class="text-base font-semibold">新建工作流</h2>
            <p class="mt-0.5 text-[11px] text-muted-foreground">
              选择分类；可选从现有工作流复制，否则创建最小文生图模板
            </p>
          </div>
          <Button variant="ghost" size="sm" class="h-8 w-8 shrink-0 p-0" aria-label="关闭" @click="close">
            <X class="h-4 w-4" />
          </Button>
        </header>
        <div class="space-y-4 p-4">
          <div class="space-y-1">
            <Label for="create-category">分类</Label>
            <SelectNative id="create-category" v-model="category" class="w-full">
              <option v-for="c in WORKFLOW_CATEGORIES" :key="c.id" :value="c.id">
                {{ c.label }}
              </option>
            </SelectNative>
          </div>
          <div class="space-y-1">
            <Label for="create-vname">显示名（可选）</Label>
            <Input id="create-vname" v-model="name" placeholder="例如：修女 Style 测试" @keyup.enter="submit" />
          </div>
          <div class="space-y-1">
            <Label for="create-copy">复制自（可选）</Label>
            <SelectNative id="create-copy" v-model="copyFrom" class="w-full">
              <option value="">不复制 · 使用最小模板</option>
              <option v-for="w in copyOptions" :key="w.id" :value="w.id">
                {{ w.display_name || w.id }}
              </option>
            </SelectNative>
          </div>
          <div class="flex justify-end gap-2">
            <Button variant="ghost" size="sm" @click="close">取消</Button>
            <Button size="sm" :disabled="busy" @click="submit">{{ busy ? '创建中…' : '创建' }}</Button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
