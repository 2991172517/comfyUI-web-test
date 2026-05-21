<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { useDebouncedSave } from '@/composables/useDebouncedSave.js'
import Switch from '@/components/ui/Switch.vue'
import PromptRandomGroupList from '@/components/prompt/PromptRandomGroupList.vue'
import {
  applyGlobalRandomGroupsMaster,
  globalConfigToPromptLayers,
  formatGlobalRandomSummary,
  globalRandomGroupsActive,
} from '@/composables/usePromptConfig.js'
import { notifyGlobalPromptSaved } from '@/composables/useGlobalPromptQuick.js'

const app = useAppStore()
const randomGroups = ref([])
const loading = ref(false)
const masterSaving = ref(false)
let cachedBase = null
let randomGroupSnapshot = null

const randomSummary = computed(() =>
  formatGlobalRandomSummary({ random_groups: randomGroups.value }),
)

const masterEnabled = computed(() =>
  globalRandomGroupsActive({ random_groups: randomGroups.value }),
)

async function load() {
  loading.value = true
  markReady(false)
  try {
    const res = await api.getGlobalPromptConfig()
    cachedBase = globalConfigToPromptLayers(res.config)
    randomGroups.value = cachedBase.random_groups || []
    randomGroupSnapshot = null
  } finally {
    loading.value = false
    await nextTick()
    markReady(true)
  }
}

async function persist() {
  if (!cachedBase) return
  await api.saveGlobalPromptConfig({
    enabled: cachedBase.enabled,
    positive: cachedBase.positive,
    negative: cachedBase.negative,
    merge: cachedBase.merge,
    random_groups: randomGroups.value,
  })
  notifyGlobalPromptSaved()
}

const { saving, markReady, schedule, flush } = useDebouncedSave(persist, { delay: 450 })

watch(
  randomGroups,
  () => schedule(),
  { deep: true },
)

async function setMasterEnabled(enabled) {
  if (loading.value || masterSaving.value) return
  masterSaving.value = true
  markReady(false)
  try {
    const wrapper = { random_groups: randomGroups.value }
    if (!enabled) {
      randomGroupSnapshot = applyGlobalRandomGroupsMaster(wrapper, false)
    } else {
      randomGroupSnapshot = applyGlobalRandomGroupsMaster(
        wrapper,
        true,
        randomGroupSnapshot,
      )
      randomGroupSnapshot = null
    }
    randomGroups.value = [...randomGroups.value]
    await flush()
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    masterSaving.value = false
    markReady(true)
  }
}

onMounted(() => load().catch((e) => app.setMessage(e.message, true)))

defineExpose({ load })
</script>

<template>
  <div class="space-y-3">
    <div
      class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border/70 bg-muted/15 px-3 py-2.5"
    >
      <div class="space-y-0.5">
        <p class="text-sm font-medium text-foreground">全局随机组总开关</p>
        <p class="text-[11px] text-muted-foreground">
          一键启用或停用所有含条目的随机组（保留各组单独开关状态）。
          <span v-if="randomSummary.text !== '无随机组'">
            当前 {{ randomSummary.text }}
          </span>
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <Switch
          :model-value="masterEnabled"
          :disabled="loading || masterSaving || saving || randomSummary.text === '无随机组'"
          aria-label="全局随机组总开关"
          @update:model-value="setMasterEnabled"
        />
        <span class="text-xs text-muted-foreground w-6">
          {{ masterSaving || saving ? '…' : masterEnabled ? '开' : '关' }}
        </span>
      </div>
    </div>

    <p class="text-xs text-muted-foreground leading-relaxed">
      随机组在合并时始终参与（与「启用全局提示词」无关）；正/负全文块需开启全局开关。修改后自动保存。
      <span v-if="saving && !masterSaving" class="text-primary">保存中…</span>
    </p>
    <p v-if="loading" class="text-sm text-muted-foreground">加载中…</p>
    <PromptRandomGroupList
      v-else
      :groups="randomGroups"
      @update:groups="randomGroups = $event"
    />
  </div>
</template>
