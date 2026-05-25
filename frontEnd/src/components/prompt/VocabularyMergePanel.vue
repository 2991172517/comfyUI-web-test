<script setup>
import { ref } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import { FileUp, Loader2 } from 'lucide-vue-next'

const app = useAppStore()
const fileInput = ref(null)
const merging = ref(false)
const previewOnly = ref(false)
const lastStats = ref(null)
const schemaOpen = ref(false)
const schema = ref(null)

async function loadSchema() {
  if (schema.value) {
    schemaOpen.value = !schemaOpen.value
    return
  }
  try {
    schema.value = await api.vocabularyMergeSchema()
    schemaOpen.value = true
  } catch (e) {
    app.setMessage(e.message, true)
  }
}

function pickFile() {
  fileInput.value?.click()
}

async function onFileChange(ev) {
  const file = ev.target.files?.[0]
  ev.target.value = ''
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.json')) {
    app.setMessage('请选择 .json 文件', true)
    return
  }
  merging.value = true
  lastStats.value = null
  try {
    const res = await api.vocabularyMergeManifest(file, {
      dryRun: previewOnly.value,
    })
    lastStats.value = res.stats || null
    const s = res.stats || {}
    const msg = previewOnly.value
      ? `预览：将新增分类 ${s.added_categories ?? 0}、词条 ${s.added_prompts ?? 0}；重复跳过词条 ${s.skipped_prompts_duplicate ?? 0}`
      : `已并入：新增分类 ${s.added_categories ?? 0}、词条 ${s.added_prompts ?? 0}；跳过重复 ${s.skipped_prompts_duplicate ?? 0}。索引已重建，无需重启后端。`
    app.setMessage(msg, false)
    if (!previewOnly.value) {
      emit('merged')
    }
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    merging.value = false
  }
}

const emit = defineEmits(['merged'])
</script>

<template>
  <Card>
    <CardHeader class="pb-2">
      <CardTitle class="text-sm">并入词库 JSON</CardTitle>
      <CardDescription class="text-xs space-y-1">
        <span>
          上传 manifest v2 格式 JSON，合并进
          <code class="text-[10px] bg-muted px-1 rounded">prompt/jsonData/manifest.json</code>
          并自动重建检索库。
        </span>
        <span class="block text-muted-foreground">
          去重：分类按 id；词条按「分类 + value（不区分大小写）」。
        </span>
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-3">
      <div class="flex flex-wrap items-center gap-2">
        <label class="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <input v-model="previewOnly" type="checkbox" class="rounded" />
          仅预览（不写盘）
        </label>
        <Button variant="outline" size="sm" class="text-xs" @click="loadSchema">
          {{ schemaOpen ? '收起格式说明' : '查看 JSON 格式' }}
        </Button>
      </div>

      <div
        v-if="schemaOpen && schema"
        class="rounded-md border border-border bg-muted/30 p-3 text-[11px] space-y-2 max-h-64 overflow-y-auto font-mono"
      >
        <p class="font-sans text-muted-foreground">{{ schema.description }}</p>
        <p class="font-sans">
          <strong>categories[]</strong>：id, name, parentId, order<br />
          <strong>prompts[]</strong>：value（必填）, categoryId（必填）, name（可选）
        </p>
        <pre class="whitespace-pre-wrap break-all text-[10px]">{{
          JSON.stringify(schema.example, null, 2)
        }}</pre>
      </div>

      <input
        ref="fileInput"
        type="file"
        accept=".json,application/json"
        class="hidden"
        @change="onFileChange"
      />
      <Button
        variant="default"
        size="sm"
        class="gap-1.5"
        :disabled="merging"
        @click="pickFile"
      >
        <Loader2 v-if="merging" class="h-4 w-4 animate-spin" />
        <FileUp v-else class="h-4 w-4" />
        {{ merging ? '处理中…' : previewOnly ? '上传并预览' : '上传并并入' }}
      </Button>

      <p v-if="lastStats" class="text-[11px] text-muted-foreground leading-relaxed">
        合并前：分类 {{ lastStats.base_categories }} / 词条 {{ lastStats.base_prompts }} →
        本次文件：分类 {{ lastStats.incoming_categories }} / 词条
        {{ lastStats.incoming_prompts }} →
        结果：分类 {{ lastStats.merged_categories }} / 词条 {{ lastStats.merged_prompts }}
        （新增词条 {{ lastStats.added_prompts }}，跳过重复 {{ lastStats.skipped_prompts_duplicate }}）
      </p>
    </CardContent>
  </Card>
</template>
