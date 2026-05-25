<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Dices } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { getRandomGachaOverlay } from '@/composables/useRandomGachaOverlay.js'
import { simulateGachaRowsForGroups } from '@/lib/randomGachaReels.js'
import { PROMPT_AUTO_SAVE_DEBOUNCE_MS, useDebouncedSave } from '@/composables/useDebouncedSave.js'
import Switch from '@/components/ui/Switch.vue'
import Button from '@/components/ui/Button.vue'
import PromptRandomGroupList from '@/components/prompt/PromptRandomGroupList.vue'
import {
  applyGlobalRandomGroupsMaster,
  globalConfigToPromptLayers,
  formatGlobalRandomSummary,
  globalRandomGroupsActive,
  serializeGlobalPromptConfig,
} from '@/composables/usePromptConfig.js'
import { notifyGlobalPromptSaved } from '@/composables/useGlobalPromptQuick.js'

const app = useAppStore()
const randomGroups = ref([])
const cachedGachaEnabled = ref(true)
const loading = ref(false)
const masterSaving = ref(false)
const simulating = ref(false)
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
    cachedGachaEnabled.value = res.config?.gacha_animation_enabled !== false
    randomGroupSnapshot = null
  } finally {
    loading.value = false
    await nextTick()
    markReady(true)
  }
}

async function persist() {
  if (!cachedBase) return
  await api.saveGlobalPromptConfig(
    serializeGlobalPromptConfig(
      { ...cachedBase, random_groups: randomGroups.value },
      { gacha_animation_enabled: cachedGachaEnabled.value },
    ),
  )
  notifyGlobalPromptSaved()
}

const { saving, pending, markReady, schedule, flush } = useDebouncedSave(persist, {
  delay: PROMPT_AUTO_SAVE_DEBOUNCE_MS,
})

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

async function simulateAllGroups() {
  if (simulating.value || loading.value) return
  const enabled = randomGroups.value.filter(
    (g) => g?.enabled !== false && (g.prompts || []).some((p) => String(p).trim()),
  )
  if (!enabled.length) {
    app.setMessage('没有可抽取的随机组，请先添加并启用词条', true)
    return
  }
  simulating.value = true
  try {
    const rows = simulateGachaRowsForGroups(enabled)
    await getRandomGachaOverlay().playWithRows(rows, {
      title: '模拟抽词',
      subtitle: `预览 ${rows.length} 个全局随机组（不影响实际生成）`,
      manualClose: true,
    })
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    simulating.value = false
  }
}

defineExpose({ load, flush })
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
        <Button
          variant="outline"
          size="sm"
          class="h-8 gap-1.5 px-2.5"
          :disabled="loading || simulating || randomSummary.text === '无随机组'"
          title="模拟抽取全部已启用随机组"
          @click="simulateAllGroups"
        >
          <Dices class="h-4 w-4" />
          <span class="hidden sm:inline">{{ simulating ? '抽取中…' : '模拟抽词' }}</span>
        </Button>
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
      随机组在合并时始终参与（与「启用全局提示词」无关）；正/负全文块需开启全局开关。修改后自动保存（约
      {{ PROMPT_AUTO_SAVE_DEBOUNCE_MS / 1000 }} 秒防抖）。
      <span v-if="pending && !saving && !masterSaving" class="text-muted-foreground">待保存…</span>
      <span v-else-if="saving && !masterSaving" class="text-primary">保存中…</span>
    </p>
    <p v-if="loading" class="text-sm text-muted-foreground">加载中…</p>
    <PromptRandomGroupList
      v-else
      gacha-preview
      :groups="randomGroups"
      @update:groups="randomGroups = $event"
    />
  </div>
</template>
