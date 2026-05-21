<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import ModelNodeCard from '@/components/models/ModelNodeCard.vue'
import { cn } from '@/lib/utils'

const app = useAppStore()
const activeTab = ref('checkpoint')
const loading = ref(false)
const search = ref('')
const checkpoints = ref([])
const loras = ref([])
const savingLora = ref(null)
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

async function load() {
  loading.value = true
  try {
    const res = await api.listNodeCatalog()
    checkpoints.value = (res.checkpoints || []).map((c) => ({ name: c.name }))
    loras.value = (res.loras || []).map((l) => ({
      name: l.name,
      strength_model: l.strength_model ?? null,
      strength_clip: l.strength_clip ?? null,
    }))
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

onMounted(() => load().catch((e) => app.setMessage(e.message, true)))
</script>

<template>
  <div class="space-y-4 max-w-6xl mx-auto">
    <PageAlert />

    <Card>
      <CardHeader>
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle class="text-base">节点管理</CardTitle>
            <CardDescription>
              直接读取 ComfyUI 本地模型列表；每张卡片展示参考图与 txt 说明。LoRA 默认权重修改后失焦即自动保存。
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" :disabled="loading" @click="load">刷新</Button>
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
          {{ search ? '无匹配的 Checkpoint' : '本地 checkpoints 目录为空或 ComfyUI 未连接' }}
        </p>
        <p
          v-else-if="activeTab === 'lora' && !filteredLoras.length"
          class="text-sm text-muted-foreground"
        >
          {{ search ? '无匹配的 LoRA' : '本地 loras 目录为空或 ComfyUI 未连接' }}
        </p>

        <div
          v-show="activeTab === 'checkpoint' && filteredCheckpoints.length"
          class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
        >
          <ModelNodeCard
            v-for="c in filteredCheckpoints"
            :key="c.name"
            folder="checkpoints"
            :name="c.name"
            kind="checkpoint"
          />
        </div>

        <div
          v-show="activeTab === 'lora' && filteredLoras.length"
          class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
        >
          <ModelNodeCard
            v-for="l in filteredLoras"
            :key="l.name"
            folder="loras"
            :name="l.name"
            kind="lora"
            :strength-model="l.strength_model"
            :strength-clip="l.strength_clip"
            @update:strength-model="updateLoraStrength(l.name, 'strength_model', $event)"
            @update:strength-clip="updateLoraStrength(l.name, 'strength_clip', $event)"
            @strength-blur="scheduleSaveLora(l.name)"
          />
        </div>

        <p class="text-[11px] text-muted-foreground pt-2 border-t border-border">
          LoRA 权重在输入框失焦后自动保存；抽卡页选择同名文件时会自动填入。
          <span v-if="savingLora" class="text-primary ml-1">保存中…</span>
        </p>
      </CardContent>
    </Card>
  </div>
</template>
