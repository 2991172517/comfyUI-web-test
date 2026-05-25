<script setup>
import { ref } from 'vue'
import { Upload, FileJson, ImageIcon } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Alert from '@/components/ui/Alert.vue'
import Badge from '@/components/ui/Badge.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import {
  DEFAULT_WORKFLOW_CATEGORY,
  WORKFLOW_CATEGORIES,
  normalizeCategory,
} from '@/lib/workflowCategories.js'
import { cn } from '@/lib/utils'

const emit = defineEmits(['imported', 'close'])

const app = useAppStore()
const fileInputRef = ref(null)
const file = ref(null)
const displayName = ref('')
const category = ref(DEFAULT_WORKFLOW_CATEGORY)
const analyzing = ref(false)
const importing = ref(false)
const dragDepth = ref(0)
const analysis = ref(null)

const dragging = ref(false)

function isAcceptedFile(f) {
  const name = (f?.name || '').toLowerCase()
  return (
    name.endsWith('.json') ||
    name.endsWith('.png') ||
    f.type === 'application/json' ||
    f.type === 'image/png'
  )
}

function applyFile(f) {
  if (!f || !isAcceptedFile(f)) {
    app.setMessage('请拖入 .json 工作流或含元数据的 .png 图片', true)
    return
  }
  file.value = f
  analysis.value = null
  if (!displayName.value) {
    displayName.value = f.name.replace(/\.(json|png)$/i, '')
  }
  analyzeFile()
}

function pickFile() {
  fileInputRef.value?.click()
}

function onFileChange(e) {
  applyFile(e.target.files?.[0] || null)
  e.target.value = ''
}

function onDragEnter(e) {
  e.preventDefault()
  dragDepth.value += 1
  dragging.value = true
}

function onDragOver(e) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
  dragging.value = true
}

function onDragLeave() {
  dragDepth.value = Math.max(0, dragDepth.value - 1)
  if (dragDepth.value === 0) dragging.value = false
}

function onDrop(e) {
  e.preventDefault()
  dragDepth.value = 0
  dragging.value = false
  applyFile(e.dataTransfer?.files?.[0] || null)
}

async function analyzeFile() {
  if (!file.value) return
  analyzing.value = true
  try {
    analysis.value = await api.analyzeWorkflowImport(file.value)
  } catch (e) {
    app.setMessage(e.message, true)
    analysis.value = null
  } finally {
    analyzing.value = false
  }
}

async function confirmImport() {
  if (!file.value) {
    app.setMessage('请选择或拖入工作流文件', true)
    return
  }
  importing.value = true
  try {
    const res = await api.importWorkflow(file.value, {
      display_name: displayName.value.trim() || undefined,
      category: normalizeCategory(category.value),
    })
    app.setMessage(`已导入：${res.display_name}（${res.variant_id}）`)
    emit('imported', res)
    emit('close')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    importing.value = false
  }
}

defineExpose({ applyFile })
</script>

<template>
  <div
    class="space-y-4"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <input
      ref="fileInputRef"
      type="file"
      accept=".json,.png,application/json,image/png"
      class="hidden"
      @change="onFileChange"
    />

    <div
      role="button"
      tabindex="0"
      :class="
        cn(
          'flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed px-4 py-10 text-sm transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/50 cursor-pointer',
          dragging
            ? 'border-primary bg-primary/15 text-primary scale-[1.01]'
            : 'border-border bg-muted/20 text-muted-foreground hover:border-primary/40 hover:bg-primary/5',
        )
      "
      @click="pickFile"
      @keydown.enter="pickFile"
      @keydown.space.prevent="pickFile"
    >
      <Upload :class="cn('h-9 w-9', dragging ? 'text-primary' : 'text-primary/70')" />
      <span class="font-medium text-foreground">拖放文件到此处</span>
      <span>或点击选择 · JSON 工作流 / 含 ComfyUI 元数据的 PNG</span>
      <span v-if="file" class="mt-1 rounded-md bg-background/80 px-2 py-1 text-xs text-foreground">
        {{ file.name }}
      </span>
    </div>

    <div class="space-y-1">
      <Label for="import-category">分类</Label>
      <SelectNative id="import-category" v-model="category" class="w-full">
        <option v-for="c in WORKFLOW_CATEGORIES" :key="c.id" :value="c.id">
          {{ c.label }}
        </option>
      </SelectNative>
    </div>

    <div class="space-y-1">
      <Label for="import-vname">名称（可选）</Label>
      <Input id="import-vname" v-model="displayName" placeholder="列表里显示的名字，不填则用文件名" />
      <p class="text-[11px] text-muted-foreground">
        无需填写 ID，后台会根据名称或文件名自动生成唯一标识。
      </p>
    </div>

    <Alert v-if="analyzing" variant="default">正在识别节点…</Alert>

    <template v-else-if="analysis">
      <div class="flex flex-wrap items-center gap-2 text-sm">
        <Badge variant="outline">
          <FileJson v-if="analysis.source === 'json'" class="mr-1 h-3 w-3" />
          <ImageIcon v-else class="mr-1 h-3 w-3" />
          {{ analysis.source === 'json' ? 'JSON' : 'PNG 元数据' }}
        </Badge>
        <Badge variant="secondary">{{ analysis.node_count }} 个节点</Badge>
        <Badge variant="secondary">{{ analysis.lora_count }} 个 LoRA</Badge>
        <Badge v-if="analysis.checkpoint?.ckpt_name" variant="outline" class="max-w-full truncate">
          {{ analysis.checkpoint.ckpt_name }}
        </Badge>
      </div>

      <Alert v-if="analysis.warnings?.length" variant="default">
        <ul class="list-disc space-y-0.5 pl-4">
          <li v-for="(w, i) in analysis.warnings" :key="i">{{ w }}</li>
        </ul>
      </Alert>

      <div
        v-if="analysis.unrecognized?.length"
        class="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2.5"
      >
        <p class="mb-2 text-sm font-medium text-amber-200">
          未识别节点（{{ analysis.unrecognized.length }}）
        </p>
        <ul class="max-h-36 space-y-1 overflow-y-auto text-xs text-amber-100/90">
          <li v-for="n in analysis.unrecognized" :key="n.node_id">
            {{ n.title }} · {{ n.class_type }} · #{{ n.node_id }}
          </li>
        </ul>
        <p class="mt-2 text-[11px] text-muted-foreground">
          仍可导入；这些自定义节点需 ComfyUI 已安装对应插件才能正常运行。
        </p>
      </div>

      <p v-else class="text-xs text-muted-foreground">所有节点均已识别，可直接导入。</p>
    </template>

    <div class="flex justify-end gap-2 pt-1">
      <Button variant="ghost" size="sm" @click="emit('close')">取消</Button>
      <Button size="sm" :disabled="!file || analyzing || importing" @click="confirmImport">
        {{ importing ? '导入中…' : '确认导入' }}
      </Button>
    </div>
  </div>
</template>
