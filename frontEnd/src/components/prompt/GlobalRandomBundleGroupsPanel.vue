<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Dices } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import { getRandomGachaOverlay } from '@/composables/useRandomGachaOverlay.js'
import { simulateGachaRowsForBundleGroups } from '@/lib/randomGachaReels.js'
import { PROMPT_AUTO_SAVE_DEBOUNCE_MS, useDebouncedSave } from '@/composables/useDebouncedSave.js'
import Switch from '@/components/ui/Switch.vue'
import Button from '@/components/ui/Button.vue'
import PromptRandomBundleGroupList from '@/components/prompt/PromptRandomBundleGroupList.vue'
import {
  applyGlobalRandomBundleGroupsMaster,
  formatGlobalRandomBundleSummary,
  globalConfigToPromptLayers,
  globalRandomBundleGroupsActive,
  serializeGlobalPromptConfig,
} from '@/composables/usePromptConfig.js'
import { notifyGlobalPromptSaved } from '@/composables/useGlobalPromptQuick.js'

const app = useAppStore()
const bundleGroups = ref([])
const cachedGachaEnabled = ref(true)
const loading = ref(false)
const masterSaving = ref(false)
let cachedBase = null
let bundleSnapshot = null

const bundleSummary = computed(() =>
  formatGlobalRandomBundleSummary({ random_bundle_groups: bundleGroups.value }),
)

const masterEnabled = computed(() =>
  globalRandomBundleGroupsActive({ random_bundle_groups: bundleGroups.value }),
)

async function load() {
  loading.value = true
  markReady(false)
  try {
    const res = await api.getGlobalPromptConfig()
    cachedBase = globalConfigToPromptLayers(res.config)
    bundleGroups.value = cachedBase.random_bundle_groups || []
    cachedGachaEnabled.value = res.config?.gacha_animation_enabled !== false
    bundleSnapshot = null
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
      { ...cachedBase, random_bundle_groups: bundleGroups.value },
      { gacha_animation_enabled: cachedGachaEnabled.value },
    ),
  )
  notifyGlobalPromptSaved()
}

const { saving, pending, markReady, schedule, flush } = useDebouncedSave(persist, {
  delay: PROMPT_AUTO_SAVE_DEBOUNCE_MS,
})

watch(bundleGroups, () => schedule(), { deep: true })

async function setMasterEnabled(enabled) {
  if (loading.value || masterSaving.value) return
  masterSaving.value = true
  markReady(false)
  try {
    const wrapper = { random_bundle_groups: bundleGroups.value }
    if (!enabled) {
      bundleSnapshot = applyGlobalRandomBundleGroupsMaster(wrapper, false)
    } else {
      applyGlobalRandomBundleGroupsMaster(wrapper, true, bundleSnapshot)
      bundleSnapshot = null
    }
    bundleGroups.value = [...bundleGroups.value]
    await flush()
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    masterSaving.value = false
    markReady(true)
  }
}

onMounted(() => load().catch((e) => app.setMessage(e.message, true)))

const simulating = ref(false)

async function simulateAll() {
  if (simulating.value || loading.value) return
  const enabled = bundleGroups.value.filter(
    (g) =>
      g?.enabled !== false &&
      (g.bundles || []).some((b) => String(b.text || '').trim()),
  )
  if (!enabled.length) {
    app.setMessage('没有可抽取的词串组', true)
    return
  }
  simulating.value = true
  try {
    const rows = simulateGachaRowsForBundleGroups(enabled)
    await getRandomGachaOverlay().playWithRows(rows, {
      title: '模拟抽词串',
      subtitle: `预览 ${rows.length} 个词串组`,
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
  <div class="space-y-4">
    <div
      class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-violet-400/25 bg-violet-500/5 px-3 py-2.5"
    >
      <div class="space-y-0.5">
        <p class="text-sm font-medium text-foreground">全局词串组总开关</p>
        <p class="text-[11px] text-muted-foreground">
          每次生成从组内抽取一整条词条串。
          <span v-if="bundleSummary.text !== '无词串组'">当前 {{ bundleSummary.text }}</span>
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <Button
          variant="outline"
          size="sm"
          class="h-8 gap-1.5"
          :disabled="loading || simulating || bundleSummary.text === '无词串组'"
          @click="simulateAll"
        >
          <Dices class="h-4 w-4" />
          模拟
        </Button>
        <Switch
          :model-value="masterEnabled"
          :disabled="loading || masterSaving || saving || bundleSummary.text === '无词串组'"
          @update:model-value="setMasterEnabled"
        />
      </div>
    </div>

    <p class="text-xs text-muted-foreground">
      修改后自动保存。
      <span v-if="pending && !saving">待保存…</span>
      <span v-else-if="saving">保存中…</span>
    </p>
    <p v-if="loading" class="text-sm text-muted-foreground">加载中…</p>
    <PromptRandomBundleGroupList
      v-else
      gacha-preview
      :groups="bundleGroups"
      @update:groups="bundleGroups = $event"
    />
  </div>
</template>
