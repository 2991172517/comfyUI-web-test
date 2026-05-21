<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import WorkflowEssentialsEditor from '@/components/workflow/WorkflowEssentialsEditor.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Badge from '@/components/ui/Badge.vue'
import { cn } from '@/lib/utils'

const router = useRouter()
const app = useAppStore()
const variants = ref([])
const selectedId = ref('')
const newId = ref('')
const newName = ref('')
const busy = ref(false)

async function refresh() {
  const v = await api.listWorkflowVariants()
  variants.value = v.variants || []
  await app.loadWorkflowList()
  if (!selectedId.value && variants.value.length) {
    selectedId.value = variants.value[0].id
  }
}

async function createVariant() {
  if (!newId.value.trim()) {
    app.setMessage('请填写子工作流 ID', true)
    return
  }
  busy.value = true
  try {
    const res = await api.createWorkflowVariant({
      variant_id: newId.value.trim(),
      display_name: newName.value.trim() || undefined,
    })
    newId.value = ''
    newName.value = ''
    await refresh()
    selectedId.value = res.id
    app.setMessage('子工作流已创建，请在右侧配置 Checkpoint / LoRA')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    busy.value = false
  }
}

function selectVariant(id) {
  selectedId.value = id
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

    <p class="text-sm text-muted-foreground max-w-3xl">
      此处<strong class="text-foreground">不是</strong> ComfyUI 画布，只管理会变的几项：Checkpoint、LoRA
      链（增删改）、Style 开关。提示词、采样、尺寸等仍在「抽卡」页调整。
    </p>

    <div class="grid gap-6 lg:grid-cols-[minmax(240px,280px)_1fr]">
      <aside class="space-y-4">
        <Card>
          <CardHeader class="pb-2">
            <CardTitle class="text-base">子工作流</CardTitle>
            <CardDescription>从母版复制，独立保存 JSON。</CardDescription>
          </CardHeader>
          <CardContent class="space-y-2">
            <button
              v-for="v in variants"
              :key="v.id"
              type="button"
              :class="
                cn(
                  'w-full rounded-md border px-3 py-2 text-left text-sm transition-colors',
                  selectedId === v.id
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:bg-accent',
                )
              "
              @click="selectVariant(v.id)"
            >
              <div class="font-medium">{{ v.display_name }}</div>
              <div class="text-xs text-muted-foreground truncate">{{ v.id }}</div>
            </button>
            <p v-if="!variants.length" class="text-xs text-muted-foreground">暂无，下方创建。</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader class="pb-2">
            <CardTitle class="text-base">新建</CardTitle>
          </CardHeader>
          <CardContent class="space-y-3">
            <div class="space-y-1">
              <Label for="vid">ID</Label>
              <Input id="vid" v-model="newId" placeholder="nun_style_test" />
            </div>
            <div class="space-y-1">
              <Label for="vname">显示名</Label>
              <Input id="vname" v-model="newName" placeholder="修女 Style 测试" />
            </div>
            <Button class="w-full" size="sm" :disabled="busy" @click="createVariant">
              从母版复制
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="pt-4 space-y-2 text-xs text-muted-foreground">
            <div class="flex items-center gap-2">
              <Badge variant="outline">母版</Badge>
              <span>First_api（只读）</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              class="w-full"
              @click="router.push({ path: '/generate', query: { workflow: 'First_api' } })"
            >
              用母版试跑 →
            </Button>
          </CardContent>
        </Card>
      </aside>

      <main class="min-w-0">
        <Card v-if="!selectedId">
          <CardContent class="py-12 text-center text-sm text-muted-foreground">
            请选择或创建一个子工作流，在右侧编辑 Checkpoint 与 LoRA 链。
          </CardContent>
        </Card>
        <WorkflowEssentialsEditor v-else :workflow-id="selectedId" />
      </main>
    </div>
  </div>
</template>
