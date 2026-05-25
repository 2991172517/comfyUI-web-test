<script setup>
import { onMounted, ref } from 'vue'
import { Plus, Upload } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import WorkflowTreeSidebar from '@/components/workflow/WorkflowTreeSidebar.vue'
import WorkflowConfigPanel from '@/components/workflow/WorkflowConfigPanel.vue'
import WorkflowImportDialog from '@/components/workflow/WorkflowImportDialog.vue'
import WorkflowCreateDialog from '@/components/workflow/WorkflowCreateDialog.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'

const app = useAppStore()

const workflows = ref([])
const selectedId = ref('')
const showImport = ref(false)
const showCreate = ref(false)

async function refresh() {
  const res = await api.listWorkflows()
  workflows.value = (res.workflows || []).filter(
    (w) => w.format === 'api' && !String(w.id || '').includes('.meta'),
  )
  await app.loadWorkflowList()

  if (selectedId.value && !workflows.value.some((w) => w.id === selectedId.value)) {
    selectedId.value = ''
  }
  if (!selectedId.value && workflows.value.length) {
    const pick =
      workflows.value.find((w) => w.category === 'generate') || workflows.value[0]
    selectedId.value = pick?.id || ''
  }
}

function selectWorkflow(id) {
  selectedId.value = id
}

function onImported(res) {
  refresh().then(() => {
    if (res?.id) selectedId.value = res.id
  })
}

function onCreated(res) {
  refresh().then(() => {
    if (res?.id) selectedId.value = res.id
  })
}

function onDeleted() {
  selectedId.value = ''
  refresh()
}

onMounted(async () => {
  try {
    await app.loadModelLists()
    await refresh()
  } catch (e) {
    app.setMessage(e.message, true)
  }
})
</script>

<template>
  <div class="space-y-4">
    <PageAlert />

    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="max-w-2xl space-y-1">
        <h2 class="text-lg font-semibold">工作流配置</h2>
        <p class="text-sm text-muted-foreground">
          左侧按分类浏览工作流；右侧按 Checkpoint / LoRA / 其他 查看与编辑，布局与抽卡页一致。
        </p>
      </div>
      <div class="flex shrink-0 flex-wrap gap-2">
        <Button variant="outline" size="sm" class="gap-1.5" @click="showImport = true">
          <Upload class="h-4 w-4" />
          导入工作流
        </Button>
        <Button size="sm" class="gap-1.5" @click="showCreate = true">
          <Plus class="h-4 w-4" />
          新建工作流
        </Button>
      </div>
    </div>

    <div class="grid gap-6 lg:grid-cols-[minmax(260px,300px)_1fr]">
      <aside>
        <Card class="h-full">
          <CardHeader class="pb-2">
            <CardTitle class="text-base">工作流树</CardTitle>
            <p class="text-xs text-muted-foreground">
              {{ workflows.length }} 个工作流
            </p>
          </CardHeader>
          <CardContent class="max-h-[calc(100vh-14rem)] overflow-y-auto pr-1">
            <WorkflowTreeSidebar
              :workflows="workflows"
              :selected-id="selectedId"
              @select="selectWorkflow"
            />
          </CardContent>
        </Card>
      </aside>

      <main class="min-w-0">
        <WorkflowConfigPanel
          :workflow-id="selectedId"
          @deleted="onDeleted"
          @saved="refresh"
        />
      </main>
    </div>

    <WorkflowImportDialog v-model:open="showImport" @imported="onImported" />
    <WorkflowCreateDialog v-model:open="showCreate" :workflows="workflows" @created="onCreated" />
  </div>
</template>
