<script setup>
import { computed, ref } from 'vue'
import { ChevronDown, Dices } from 'lucide-vue-next'
import { getRandomGachaOverlay } from '@/composables/useRandomGachaOverlay.js'
import { simulateGachaRowsForBundleGroups } from '@/lib/randomGachaReels.js'
import { useAppStore } from '@/stores/useAppStore.js'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import Switch from '@/components/ui/Switch.vue'
import PromptRandomBundleCard from '@/components/prompt/PromptRandomBundleCard.vue'
import { newRandomBundle } from '@/composables/usePromptConfig.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  group: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
  gachaPreview: { type: Boolean, default: false },
})

const emit = defineEmits(['update:group', 'remove'])

const app = useAppStore()
const bodyOpen = ref(true)
const previewing = ref(false)

function update(patch) {
  emit('update:group', { ...props.group, ...patch })
}

function syncWeights() {
  const n = (props.group.bundles || []).length
  const weights = [...(props.group.weights || [])]
  while (weights.length < n) weights.push(1)
  if (weights.length > n) weights.length = n
  return weights
}

function updateBundleAt(i, bundle) {
  const bundles = [...(props.group.bundles || [])]
  bundles[i] = bundle
  update({ bundles, weights: syncWeights() })
}

function removeBundleAt(i) {
  const bundles = [...(props.group.bundles || [])]
  bundles.splice(i, 1)
  update({ bundles: bundles.length ? bundles : [newRandomBundle()], weights: syncWeights() })
}

function addBundle() {
  const bundles = [...(props.group.bundles || []), newRandomBundle()]
  update({ bundles, weights: syncWeights() })
}

function updateBundleWeight(i, val) {
  const weights = syncWeights()
  const n = Number(val)
  weights[i] = Number.isFinite(n) && n >= 0 ? n : 1
  update({ weights })
}

const bundleCount = computed(
  () => (props.group.bundles || []).filter((b) => String(b.text || '').trim()).length,
)

const canPreview = computed(
  () =>
    props.gachaPreview &&
    props.group.enabled !== false &&
    bundleCount.value > 0,
)

async function simulateGroup() {
  if (!canPreview.value || previewing.value) return
  previewing.value = true
  try {
    const rows = simulateGachaRowsForBundleGroups([props.group])
    if (!rows.length) {
      app.setMessage('该词串组没有可抽取的词条', true)
      return
    }
    await getRandomGachaOverlay().playWithRows(rows, {
      title: '模拟抽词串',
      subtitle: `预览「${props.group.name || '词串组'}」`,
      manualClose: true,
    })
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    previewing.value = false
  }
}
</script>

<template>
  <article
    :class="
      cn(
        'rounded-md border px-3 py-2.5 space-y-2',
        group.enabled ? 'border-violet-400/35 bg-violet-500/5' : 'border-border/80 opacity-85',
      )
    "
  >
    <div class="flex flex-wrap items-center gap-2 min-w-0">
      <Switch
        size="sm"
        class="shrink-0"
        :model-value="group.enabled !== false"
        :disabled="disabled"
        @update:model-value="update({ enabled: $event })"
      />
      <Input
        class="flex-1 min-w-[5rem] h-8 text-sm"
        :model-value="group.name"
        placeholder="词串组名"
        :disabled="disabled"
        @update:model-value="update({ name: $event })"
      />
      <SelectNative
        class="h-8 text-xs w-[4.5rem] shrink-0"
        :model-value="group.target"
        :disabled="disabled"
        @update:model-value="update({ target: $event })"
      >
        <option value="positive">正向</option>
        <option value="negative">负向</option>
      </SelectNative>
      <SelectNative
        class="h-8 text-xs w-[4.5rem] shrink-0"
        :model-value="group.pick_mode || 'random'"
        :disabled="disabled"
        @update:model-value="update({ pick_mode: $event === 'sequential' ? 'sequential' : 'random' })"
      >
        <option value="random">随机</option>
        <option value="sequential">顺序</option>
      </SelectNative>
      <Badge variant="outline" class="text-[10px] shrink-0">
        {{ bundleCount }} 组词条
      </Badge>
      <Button
        v-if="gachaPreview"
        variant="ghost"
        size="sm"
        class="h-8 w-8 shrink-0 p-0"
        :disabled="disabled || previewing || !canPreview"
        title="模拟抽取本词串组"
        @click="simulateGroup"
      >
        <Dices class="h-4 w-4" />
      </Button>
      <IconDeleteButton class="shrink-0" :disabled="disabled" @click="emit('remove')" />
      <Button
        variant="ghost"
        size="sm"
        class="h-8 w-8 shrink-0 p-0"
        @click="bodyOpen = !bodyOpen"
      >
        <ChevronDown :class="cn('h-4 w-4 transition-transform', bodyOpen && 'rotate-180')" />
      </Button>
    </div>

    <template v-if="bodyOpen">
      <p class="text-[10px] text-muted-foreground leading-snug">
        每次生成抽取<strong>一整组</strong>词条（组内逗号分隔 tag 全部加入）。别名用于抽卡动画与列表展示。
      </p>
      <div class="space-y-2">
        <PromptRandomBundleCard
          v-for="(b, i) in group.bundles"
          :key="b.id"
          :bundle="b"
          :index="i"
          :disabled="disabled"
          :show-weight="(group.pick_mode || 'random') !== 'sequential'"
          :weight="(group.weights || [])[i] ?? 1"
          @update:bundle="updateBundleAt(i, $event)"
          @update-weight="updateBundleWeight(i, $event)"
          @remove="removeBundleAt(i)"
        />
      </div>
      <Button variant="ghost" size="sm" class="h-7 text-xs" :disabled="disabled" @click="addBundle">
        + 添加词条组
      </Button>
    </template>
  </article>
</template>
