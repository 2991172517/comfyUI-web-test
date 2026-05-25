<script setup>
import { onMounted, ref } from 'vue'
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

const app = useAppStore()
const loading = ref(false)
const saving = ref(false)
const defaults = ref({ checkpoints: '', loras: '' })
const resolved = ref({ checkpoints: '', loras: '' })
const checkpoints = ref('')
const loras = ref('')
const maxScanDepth = ref(3)

async function load() {
  loading.value = true
  try {
    const res = await api.getModelPathSettings()
    defaults.value = res.defaults || {}
    resolved.value = res.resolved || {}
    checkpoints.value = res.settings?.checkpoints || ''
    loras.value = res.settings?.loras || ''
    maxScanDepth.value = Number(res.max_scan_subdir_depth) || 3
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const res = await api.saveModelPathSettings({
      checkpoints: checkpoints.value.trim(),
      loras: loras.value.trim(),
    })
    resolved.value = res.resolved || {}
    app.setMessage('模型路径已保存，列表将按新路径扫描')
    emit('saved')
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    saving.value = false
  }
}

function useDefaults() {
  checkpoints.value = ''
  loras.value = ''
}

const emit = defineEmits(['saved'])

onMounted(() => load())
</script>

<template>
  <Card>
    <CardHeader class="pb-2">
      <CardTitle class="text-sm">模型目录路径</CardTitle>
      <CardDescription class="text-xs leading-relaxed">
        留空则使用 ComfyUI 默认
        <code class="text-[10px] bg-muted px-1 rounded">models/checkpoints</code>、
        <code class="text-[10px] bg-muted px-1 rounded">models/loras</code>。
        填一个总库根目录即可；列表会扫描该目录下最多
        <strong>{{ maxScanDepth }} 层子文件夹</strong>内的
        <code class="text-[10px]">.safetensors</code> / <code class="text-[10px]">.ckpt</code>
        （例如 <code class="text-[10px]">loras/角色/xxx.safetensors</code>）。
        更深层的文件不会出现在本控制台列表中，需挪到较浅目录或由 ComfyUI 自身加载。
        生图时 ComfyUI 仍须在 <code class="text-[10px]">extra_model_paths.yaml</code> 中能加载到同名文件。
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-3">
      <div v-if="loading" class="text-xs text-muted-foreground">加载路径配置…</div>
      <template v-else>
        <div class="grid gap-3 sm:grid-cols-2">
          <div class="space-y-1.5">
            <Label class="text-xs">Checkpoint 目录</Label>
            <Input
              v-model="checkpoints"
              class="h-8 text-xs font-mono"
              :placeholder="defaults.checkpoints || '默认 models/checkpoints'"
            />
            <p class="text-[10px] text-muted-foreground truncate" :title="resolved.checkpoints">
              当前扫描：{{ resolved.checkpoints || '—' }}
            </p>
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs">LoRA 目录</Label>
            <Input
              v-model="loras"
              class="h-8 text-xs font-mono"
              :placeholder="defaults.loras || '默认 models/loras'"
            />
            <p class="text-[10px] text-muted-foreground truncate" :title="resolved.loras">
              当前扫描：{{ resolved.loras || '—' }}
            </p>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button size="sm" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存路径' }}
          </Button>
          <Button variant="outline" size="sm" :disabled="saving" @click="useDefaults">
            恢复默认
          </Button>
        </div>
      </template>
    </CardContent>
  </Card>
</template>
