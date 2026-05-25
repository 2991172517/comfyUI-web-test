<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Download } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { modelImportModalOpen, openModelImportModal } from '@/composables/useModelImportModal.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import ModelNodeCard from '@/components/models/ModelNodeCard.vue'
import ModelManifestToolbar from '@/components/models/ModelManifestToolbar.vue'
import ModelPathSettings from '@/components/models/ModelPathSettings.vue'
import { cn } from '@/lib/utils'

const app = useAppStore()
const router = useRouter()
const activeTab = ref('checkpoint')
const loading = ref(false)
const search = ref('')
const checkpoints = ref([])
const loras = ref([])
const savingLora = ref(null)
const deletingName = ref(null)
const saveTimers = new Map()

const tabs = [
  { id: 'checkpoint', label: 'Checkpoint' },
  { id: 'lora', label: 'LoRA' },
]

const filteredCheckpoints = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return checkpoints.value
  return checkpoints.value.filter((c) => c.name.toLowerCase().includes(q))
})

const filteredLoras = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return loras.value
  return loras.value.filter((l) => l.name.toLowerCase().includes(q))
})

async function reloadCatalog() {
  await load()
  await app.loadModelLists().catch(() => {})
}

async function load() {
  loading.value = true
  try {
    const res = await api.listNodeCatalog()
    checkpoints.value = (res.checkpoints || []).map((c) => ({
      name: c.name,
      recommended_loras: c.recommended_loras || [],
      not_recommended_loras: c.not_recommended_loras || [],
    }))
    loras.value = (res.loras || []).map((l) => ({
      name: l.name,
      strength_model: l.strength_model ?? null,
      strength_clip: l.strength_clip ?? null,
    }))
    await app.loadModelLists().catch(() => {})
  } finally {
    loading.value = false
  }
}

function updateLoraStrength(name, field, value) {
  const row = loras.value.find((l) => l.name === name)
  if (row) row[field] = value
}

function scheduleSaveLora(name) {
  const prev = saveTimers.get(name)
  if (prev) clearTimeout(prev)
  saveTimers.set(
    name,
    setTimeout(() => {
      saveTimers.delete(name)
      saveLora(name)
    }, 350),
  )
}

async function saveLora(name) {
  const row = loras.value.find((l) => l.name === name)
  if (!row) return
  savingLora.value = name
  try {
    await api.saveNodeCatalog({
      loras: [
        {
          name: row.name,
          strength_model: row.strength_model,
          strength_clip: row.strength_clip,
        },
      ],
    })
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    if (savingLora.value === name) savingLora.value = null
  }
}

async function deleteModel(folder, name) {
  deletingName.value = name
  try {
    await api.deleteModel(folder, name, true)
    if (folder === 'checkpoints') {
      checkpoints.value = checkpoints.value.filter((c) => c.name !== name)
    } else {
      loras.value = loras.value.filter((l) => l.name !== name)
    }
    await app.loadModelLists().catch(() => {})
    app.setMessage(`已删除：${name}`)
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    deletingName.value = null
  }
}

watch(modelImportModalOpen, (open, wasOpen) => {
  if (wasOpen && !open) load().catch(() => {})
})

onMounted(() => load().catch((e) => app.setMessage(e.message, true)))
</script>

<template>
  <div class="space-y-4 max-w-6xl mx-auto">
    <PageAlert />

    <ModelPathSettings @saved="reloadCatalog" />

    <Card>
      <CardHeader>
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle class="text-base">模型管理</CardTitle>
            <CardDescription>
              浏览本地 Checkpoint / LoRA；可为每个 Checkpoint 配置推荐/不推荐 LoRA（生成页选 LoRA 时灰字提示，仍可选）。
            </CardDescription>
          </div>
          <div class="flex flex-wrap items-end gap-3 shrink-0">
            <ModelManifestToolbar @done="load" />
            <div class="flex flex-wrap items-center gap-2">
              <Button variant="outline" size="sm" @click="router.push('/models/civitai')">
                C 站浏览
              </Button>
              <Button variant="default" size="sm" class="gap-1.5" @click="openModelImportModal">
                <Download class="h-4 w-4" />
                粘贴链接
              </Button>
              <Button variant="outline" size="sm" :disabled="loading" @click="load">刷新</Button>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent class="space-y-4">
        <div class="flex flex-wrap items-center gap-3">
          <div
            class="inline-flex rounded-lg border border-border p-0.5 text-sm"
            role="tablist"
          >
            <button
              v-for="t in tabs"
              :key="t.id"
              type="button"
              role="tab"
              :aria-selected="activeTab === t.id"
              :class="
                cn(
                  'rounded-md px-4 py-1.5 transition-colors',
                  activeTab === t.id
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground',
                )
              "
              @click="activeTab = t.id"
            >
              {{ t.label }}
              <span class="ml-1 opacity-70 text-[11px]">
                ({{
                  t.id === 'checkpoint' ? checkpoints.length : loras.length
                }})
              </span>
            </button>
          </div>
          <Input
            v-model="search"
            class="max-w-xs h-8 text-sm ml-auto"
            placeholder="搜索模型文件名…"
          />
        </div>

        <p v-if="loading" class="text-sm text-muted-foreground">加载本地模型列表…</p>

        <p
          v-else-if="activeTab === 'checkpoint' && !filteredCheckpoints.length"
          class="text-sm text-muted-foreground"
        >
          {{ search ? '无匹配的 Checkpoint' : '本地 checkpoints 目录为空' }}
        </p>
        <p
          v-else-if="activeTab === 'lora' && !filteredLoras.length"
          class="text-sm text-muted-foreground"
        >
          {{ search ? '无匹配的 LoRA' : '本地 loras 目录为空' }}
        </p>

        <div
          v-if="activeTab === 'checkpoint' && filteredCheckpoints.length"
          class="grid gap-4 items-stretch sm:grid-cols-2 xl:grid-cols-3"
        >
          <ModelNodeCard
            v-for="c in filteredCheckpoints"
            :key="c.name"
            folder="checkpoints"
            :name="c.name"
            kind="checkpoint"
            manage
            :all-loras="loras.map((l) => l.name)"
            :lora-catalog="app.modelLists.loraCatalog"
            :recommended-loras="c.recommended_loras"
            :not-recommended-loras="c.not_recommended_loras"
            :deleting="deletingName === c.name"
            @update:recommended-loras="
              (v) => {
                c.recommended_loras = v
              }
            "
            @update:not-recommended-loras="
              (v) => {
                c.not_recommended_loras = v
              }
            "
            @delete="deleteModel('checkpoints', $event)"
          />
        </div>

        <div
          v-if="activeTab === 'lora' && filteredLoras.length"
          class="grid gap-4 items-stretch sm:grid-cols-2 xl:grid-cols-3"
        >
          <ModelNodeCard
            v-for="l in filteredLoras"
            :key="l.name"
            folder="loras"
            :name="l.name"
            kind="lora"
            manage
            :strength-model="l.strength_model"
            :strength-clip="l.strength_clip"
            :deleting="deletingName === l.name"
            @update:strength-model="updateLoraStrength(l.name, 'strength_model', $event)"
            @update:strength-clip="updateLoraStrength(l.name, 'strength_clip', $event)"
            @strength-blur="scheduleSaveLora(l.name)"
            @delete="deleteModel('loras', $event)"
          />
        </div>

        <p class="text-[11px] text-muted-foreground pt-2 border-t border-border">
          删除会移除 .safetensors/.ckpt 及同名资源文件夹（含说明与预览图）。点击卡片说明框即可编辑说明。
          「导出清单」生成
          <code class="text-[10px] bg-muted px-1 rounded">config/models_manifest.json</code>；
          「一键下载全部」按清单拉取缺失模型，本地已有则跳过（需 C 站 API Key）。
          <span v-if="savingLora" class="text-primary ml-1">LoRA 权重保存中…</span>
        </p>
      </CardContent>
    </Card>
  </div>
</template>
