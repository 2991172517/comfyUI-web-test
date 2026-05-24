<script setup>
import { computed, ref } from 'vue'
import { ChevronDown, Dices } from 'lucide-vue-next'
import { getRandomGachaOverlay } from '@/composables/useRandomGachaOverlay.js'
import { simulateGachaRowsForGroups } from '@/lib/randomGachaReels.js'
import { useAppStore } from '@/stores/useAppStore.js'
import Input from '@/components/ui/Input.vue'
import PoolPickWeightPanel from '@/components/prompt/PoolPickWeightPanel.vue'
import PromptTextarea from '@/components/prompt/PromptTextarea.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import Switch from '@/components/ui/Switch.vue'
import {
  countCandidates,
  groupModeBadge,
  groupModeDescription,
  randomGroupMode,
  splitPromptTokens,
} from '@/lib/promptTokens.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  group: { type: Object, required: true },
  index: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
  gachaPreview: { type: Boolean, default: false },
})

const emit = defineEmits(['update:group', 'remove'])

const app = useAppStore()
const previewing = ref(false)

const bodyOpen = ref(true)

const mode = computed(() => randomGroupMode(props.group))
const badgeText = computed(() => groupModeBadge(props.group))
const modeHint = computed(() => groupModeDescription(props.group))
const isRandom = computed(() => (props.group.pick_mode || 'random') !== 'sequential')
const isPool = computed(() => mode.value === 'pool')

const poolLine = computed(() => String((props.group.prompts || [])[0] || ''))
const poolTokens = computed(() => splitPromptTokens(poolLine.value))

const poolPickWeights = computed(() => {
  const raw = props.group.weights || []
  return poolTokens.value.map((_, i) => raw[i] ?? 1)
})

const showPoolPickWeights = computed(() => isPool.value && isRandom.value)

function update(patch) {
  emit('update:group', { ...props.group, ...patch })
}

function syncWeights(prompts) {
  const weights = [...(props.group.weights || [])]
  while (weights.length < prompts.length) weights.push(1)
  if (weights.length > prompts.length) weights.length = prompts.length
  return weights
}

function updatePrompt(i, val) {
  const prompts = [...(props.group.prompts || [])]
  prompts[i] = val
  let weights = syncWeights(prompts)
  if (i === 0 && (prompts.filter((p) => String(p).trim()).length <= 1)) {
    const k = splitPromptTokens(val).length || 1
    weights = []
    for (let j = 0; j < k; j++) weights.push((props.group.weights || [])[j] ?? 1)
  }
  update({ prompts, weights })
}

function updateWeight(i, val) {
  const weights = syncWeights(props.group.prompts || [])
  const n = Number(val)
  weights[i] = Number.isFinite(n) && n >= 0 ? n : 1
  update({ weights })
}

function updatePoolTokenWeight(i, val) {
  const k = poolTokens.value.length
  if (!k) return
  const weights = []
  const raw = props.group.weights || []
  for (let j = 0; j < k; j++) weights.push(raw[j] ?? 1)
  const n = Number(val)
  weights[i] = Number.isFinite(n) && n >= 0 ? n : 1
  update({ weights })
}

function bumpSchemeWeight(i, delta) {
  const current = (props.group.weights || [])[i] ?? 1
  updateWeight(i, current + delta)
}

function addCandidate() {
  const prompts = [...(props.group.prompts || []), '']
  update({ prompts, weights: syncWeights(prompts) })
}

function removePrompt(i) {
  const prompts = [...(props.group.prompts || [])]
  prompts.splice(i, 1)
  const next = prompts.length ? prompts : ['']
  update({ prompts: next, weights: syncWeights(next) })
}

function switchToPoolMode() {
  const lines = (props.group.prompts || []).map((p) => String(p).trim()).filter(Boolean)
  if (lines.length <= 1) return
  const merged = [lines.join(', ')]
  update({ prompts: merged, weights: syncWeights(merged) })
}

function onPickModeChange(val) {
  const pick_mode = val === 'sequential' ? 'sequential' : 'random'
  update({ pick_mode })
}

const canGachaPreview = computed(
  () =>
    props.gachaPreview &&
    props.group.enabled !== false &&
    (props.group.prompts || []).some((p) => String(p).trim()),
)

async function simulateGroup() {
  if (previewing.value || !canGachaPreview.value) return
  previewing.value = true
  try {
    const rows = simulateGachaRowsForGroups([props.group])
    if (!rows.length) {
      app.setMessage('该组没有可抽取的词条', true)
      return
    }
    await getRandomGachaOverlay().playWithRows(rows, {
      title: '模拟抽词',
      subtitle: `预览「${props.group.name || '随机组'}」（不影响实际生成）`,
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
        group.enabled ? 'border-primary/35 bg-primary/5' : 'border-border/80 opacity-85',
      )
    "
  >
    <div class="flex items-center gap-2 min-w-0">
      <Switch
        size="sm"
        class="shrink-0"
        :model-value="group.enabled !== false"
        :disabled="disabled"
        :aria-label="`${group.name || '随机组'} 启用`"
        @update:model-value="update({ enabled: $event })"
      />
      <Input
        class="flex-1 min-w-[4rem] h-8 text-sm"
        :model-value="group.name"
        placeholder="组名"
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
        title="随机：按权重抽取；顺序：按批量图序号依次取用并循环"
        @update:model-value="onPickModeChange"
      >
        <option value="random">随机</option>
        <option value="sequential">顺序</option>
      </SelectNative>
      <Badge variant="outline" class="text-[10px] shrink-0 hidden sm:inline-flex" :title="modeHint">
        {{ badgeText }}
      </Badge>
      <Button
        v-if="gachaPreview"
        variant="ghost"
        size="sm"
        class="h-8 w-8 shrink-0 p-0 text-primary"
        :disabled="disabled || previewing || !canGachaPreview"
        title="模拟抽取本组"
        @click="simulateGroup"
      >
        <Dices class="h-4 w-4" />
      </Button>
      <Button
        v-if="countCandidates(group) > 1"
        variant="outline"
        size="sm"
        class="h-8 px-2 text-[10px] shrink-0 hidden md:inline-flex"
        :disabled="disabled"
        title="合并为逗号分隔词条池"
        @click="switchToPoolMode"
      >
        合并池
      </Button>
      <IconDeleteButton
        class="shrink-0"
        :disabled="disabled"
        title="删除组"
        @click="emit('remove')"
      />
      <Button
        variant="ghost"
        size="sm"
        class="h-8 w-8 shrink-0 p-0"
        :disabled="disabled"
        :title="bodyOpen ? '收起词条' : '展开词条'"
        @click="bodyOpen = !bodyOpen"
      >
        <ChevronDown :class="cn('h-4 w-4 transition-transform', bodyOpen && 'rotate-180')" />
      </Button>
    </div>

    <template v-if="bodyOpen">
    <p class="text-[10px] text-muted-foreground leading-snug">{{ modeHint }}</p>

    <template v-if="mode === 'pool'">
      <PromptTextarea
        :model-value="(group.prompts || [])[0] || ''"
        :rows="4"
        class="text-xs font-mono"
        :disabled="disabled"
        placeholder="词条池，英文或中文逗号分隔"
        @update:model-value="updatePrompt(0, $event)"
      />
      <PoolPickWeightPanel
        v-if="showPoolPickWeights"
        :tokens="poolTokens"
        :weights="poolPickWeights"
        :disabled="disabled"
        @update-weight="updatePoolTokenWeight"
      />
    </template>

    <template v-else>
      <div class="space-y-1.5">
        <div
          v-if="isRandom"
          class="flex gap-1.5 items-center pr-8 text-[10px] text-muted-foreground"
        >
          <span class="w-8 shrink-0 text-right">#</span>
          <span class="flex-1">候选方案</span>
          <span class="w-[4.5rem] shrink-0 text-center">抽中权重</span>
        </div>
        <div
          v-for="(line, i) in group.prompts"
          :key="i"
          class="flex gap-1.5 items-start"
        >
          <span class="text-[10px] text-muted-foreground pt-2 w-8 shrink-0 text-right">{{ i + 1 }}</span>
          <PromptTextarea
            class="flex-1 min-w-0 text-xs font-mono"
            :model-value="line"
            :rows="4"
            :disabled="disabled"
            placeholder="候选方案，逗号分隔多个 tag"
            @update:model-value="updatePrompt(i, $event)"
          />
          <div
            v-if="isRandom"
            class="flex shrink-0 items-center gap-0.5 pt-1"
          >
            <button
              type="button"
              class="h-7 w-6 rounded text-xs text-muted-foreground hover:bg-muted disabled:opacity-40"
              :disabled="disabled"
              aria-label="降低方案抽中权重"
              @click="bumpSchemeWeight(i, -1)"
            >
              −
            </button>
            <Input
              type="number"
              min="0"
              step="0.1"
              class="h-7 w-12 text-xs text-center"
              :model-value="(group.weights || [])[i] ?? 1"
              :disabled="disabled"
              title="方案抽中权重，越大越容易被抽到"
              @update:model-value="updateWeight(i, $event)"
            />
            <button
              type="button"
              class="h-7 w-6 rounded text-xs text-muted-foreground hover:bg-muted disabled:opacity-40"
              :disabled="disabled"
              aria-label="提高方案抽中权重"
              @click="bumpSchemeWeight(i, 1)"
            >
              +
            </button>
          </div>
          <IconDeleteButton
            size="sm"
            :disabled="disabled || (group.prompts || []).length <= 1"
            title="删除方案"
            @click="removePrompt(i)"
          />
        </div>
        <Button variant="ghost" size="sm" class="h-7 text-xs" :disabled="disabled" @click="addCandidate">
          + 方案
        </Button>
      </div>
    </template>
    </template>
  </article>
</template>
