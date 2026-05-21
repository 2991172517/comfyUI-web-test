<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Badge from '@/components/ui/Badge.vue'
import Alert from '@/components/ui/Alert.vue'
import ModelVisualPicker from '@/components/models/ModelVisualPicker.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  workflowId: { type: String, required: true },
})

const emit = defineEmits(['saved', 'loaded'])

const router = useRouter()
const app = useAppStore()
const loading = ref(false)
const saving = ref(false)
const essentials = ref(null)
const syncClip = ref(true)

const hasStyleSlot = computed(() =>
  essentials.value?.lora_chain?.some((l) => l.role === 'style'),
)
const readOnly = computed(() => !!essentials.value?.is_master)

async function load() {
  if (!props.workflowId) return
  loading.value = true
  try {
    const res = await api.getWorkflowEssentials(props.workflowId)
    essentials.value = res
    emit('loaded', res)
  } catch (e) {
    app.setMessage(e.message, true)
    essentials.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => props.workflowId,
  () => load(),
  { immediate: true },
)

function roleLabel(role) {
  if (role === 'style') return 'Style'
  if (role === 'character') return '角色'
  return role
}

function patchLora(nodeId, key, val) {
  const item = essentials.value?.lora_chain?.find((l) => l.node_id === nodeId)
  if (!item) return
  item[key] = val
  if (syncClip.value && (key === 'strength_model' || key === 'strength_clip')) {
    item.strength_model = key === 'strength_model' ? val : item.strength_model
    item.strength_clip = item.strength_model
  }
}

async function save() {
  if (!essentials.value || readOnly.value) return
  saving.value = true
  try {
    const res = await api.saveWorkflowEssentials(props.workflowId, {
      display_name: essentials.value.display_name,
      style_enabled: essentials.value.style_enabled,
      checkpoint: essentials.value.checkpoint,
      lora_chain: essentials.value.lora_chain,
    })
    essentials.value = res
    await app.loadWorkflow(props.workflowId)
    app.setMessage('工作流核心配置已保存')
    emit('saved', res)
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    saving.value = false
  }
}

async function addLora(role) {
  if (readOnly.value) return
  try {
    const res = await api.addLoraSlot(props.workflowId, { role, lora_name: 'None' })
    essentials.value = res
    await app.loadWorkflow(props.workflowId)
    app.setMessage(role === 'style' ? '已添加 Style LoRA 槽位' : '已添加角色 LoRA')
  } catch (e) {
    app.setMessage(e.message, true)
  }
}

async function removeLora(nodeId) {
  if (readOnly.value) return
  if (!confirm('从链中移除此 LoRA 节点？')) return
  try {
    const res = await api.removeLoraSlot(props.workflowId, nodeId)
    essentials.value = res
    await app.loadWorkflow(props.workflowId)
    app.setMessage('已移除 LoRA')
  } catch (e) {
    app.setMessage(e.message, true)
  }
}

function goGenerate() {
  router.push({ path: '/generate', query: { workflow: props.workflowId } })
}
</script>

<template>
  <div v-if="loading" class="text-sm text-muted-foreground py-8 text-center">加载配置…</div>

  <Alert v-else-if="readOnly" variant="default" class="mb-4">
    母版只读。请从左侧创建子工作流后再编辑 Checkpoint / LoRA / Style。
  </Alert>

  <div v-else-if="essentials" class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex-1 min-w-[200px] space-y-1">
        <Label>显示名称</Label>
        <Input v-model="essentials.display_name" :disabled="readOnly" />
      </div>
      <div class="flex flex-wrap gap-2 pt-6">
        <Button variant="outline" size="sm" @click="goGenerate">去抽卡试跑</Button>
        <Button size="sm" :disabled="saving || readOnly" @click="save">
          {{ saving ? '保存中…' : '保存核心配置' }}
        </Button>
      </div>
    </div>

    <Card>
      <CardHeader class="pb-2">
        <CardTitle class="text-base">Checkpoint</CardTitle>
        <CardDescription>底模，整条 LoRA 链接在其后。</CardDescription>
      </CardHeader>
      <CardContent>
        <ModelVisualPicker
          folder="checkpoints"
          label="模型文件"
          :model-value="essentials.checkpoint?.ckpt_name || ''"
          :options="app.modelLists.checkpoints"
          :catalog="app.modelLists.checkpointCatalog"
          :loading="app.modelsLoading"
          :disabled="readOnly"
          @update:model-value="essentials.checkpoint.ckpt_name = $event"
        />
      </CardContent>
    </Card>

    <Card>
      <CardHeader class="pb-2">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle class="text-base">LoRA 链</CardTitle>
            <CardDescription>
              从上到下：先角色 LoRA，末尾为 Style（可选）。提示词 / 采样等请在「抽卡」页调整。
            </CardDescription>
          </div>
          <label class="flex items-center gap-2 text-xs text-muted-foreground">
            <input v-model="syncClip" type="checkbox" class="rounded border-input" />
            同步 strength_clip
          </label>
        </div>
      </CardHeader>
      <CardContent class="space-y-3">
        <div
          v-for="(l, idx) in essentials.lora_chain"
          :key="l.node_id"
          :class="
            cn(
              'rounded-lg border p-4 space-y-3',
              l.role === 'style' ? 'border-primary/40 bg-primary/5' : 'border-border',
            )
          "
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <span class="text-xs text-muted-foreground">#{{ idx + 1 }}</span>
              <Badge :variant="l.role === 'style' ? 'default' : 'secondary'">
                {{ roleLabel(l.role) }}
              </Badge>
              <span class="text-xs text-muted-foreground">节点 {{ l.node_id }}</span>
            </div>
            <Button
              v-if="l.can_remove"
              variant="ghost"
              size="sm"
              class="text-destructive hover:text-destructive"
              :disabled="readOnly"
              @click="removeLora(l.node_id)"
            >
              移除
            </Button>
          </div>

          <ModelVisualPicker
            folder="loras"
            label="LoRA 文件"
            :model-value="l.lora_name"
            :options="app.modelLists.loras"
            :catalog="app.modelLists.loraCatalog"
            :loading="app.modelsLoading"
            :disabled="readOnly"
            @update:model-value="l.lora_name = $event"
          />

          <div class="grid gap-3 sm:grid-cols-2">
            <div class="space-y-1">
              <Label>strength_model</Label>
              <Input
                type="number"
                step="0.05"
                min="0"
                max="2"
                :model-value="l.strength_model"
                :disabled="readOnly"
                @update:model-value="patchLora(l.node_id, 'strength_model', Number($event))"
              />
            </div>
            <div class="space-y-1">
              <Label>strength_clip</Label>
              <Input
                type="number"
                step="0.05"
                min="0"
                max="2"
                :model-value="l.strength_clip"
                :disabled="readOnly || syncClip"
                @update:model-value="patchLora(l.node_id, 'strength_clip', Number($event))"
              />
            </div>
          </div>
        </div>

        <p v-if="!essentials.lora_chain?.length" class="text-sm text-muted-foreground">
          链上暂无 LoRA，可直接用 Checkpoint 出图，或下方添加。
        </p>

        <div class="flex flex-wrap gap-2 border-t border-border pt-3">
          <Button variant="outline" size="sm" :disabled="readOnly" @click="addLora('character')">
            + 角色 LoRA
          </Button>
          <Button
            v-if="!hasStyleSlot"
            variant="outline"
            size="sm"
            :disabled="readOnly"
            @click="addLora('style')"
          >
            + Style LoRA
          </Button>
        </div>
      </CardContent>
    </Card>

    <Card v-if="hasStyleSlot">
      <CardHeader class="pb-2">
        <CardTitle class="text-base">Style 开关</CardTitle>
        <CardDescription>
          关闭时运行绕过 Style 节点（与单张/批量一致），不删 JSON 里的节点。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <label class="flex items-center gap-2 text-sm">
          <input
            v-model="essentials.style_enabled"
            type="checkbox"
            class="rounded border-input"
            :disabled="readOnly"
          />
          生成时启用 Style LoRA
        </label>
      </CardContent>
    </Card>
  </div>
</template>
