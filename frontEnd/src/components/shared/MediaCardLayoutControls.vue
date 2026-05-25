<script setup>
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import {
  historyCardLayout,
  historyCardIsNatural,
  setHistoryCardWidth,
  applyHistoryCardWidthPreset,
  HISTORY_CARD_WIDTH_MIN,
  HISTORY_CARD_WIDTH_MAX,
  HISTORY_CARD_WIDTH_PRESETS,
  HISTORY_IMAGE_LAYOUT_OPTIONS,
  HISTORY_ASPECT_OPTIONS,
} from '@/composables/useHistoryCardLayout.js'

defineProps({
  compact: { type: Boolean, default: false },
})
</script>

<template>
  <div
    :class="
      compact
        ? 'flex flex-wrap items-end gap-x-4 gap-y-2'
        : 'flex flex-wrap items-end gap-3 rounded-lg border border-border bg-muted/40 px-3 py-2'
    "
  >
    <div class="space-y-1 min-w-[10rem]">
      <Label class="text-xs flex items-center justify-between gap-2">
        <span>卡片宽度</span>
        <span class="font-mono text-muted-foreground tabular-nums">{{ historyCardLayout.cardWidth }}px</span>
      </Label>
      <input
        v-model.number="historyCardLayout.cardWidth"
        type="range"
        class="h-2 w-full min-w-[10rem] max-w-[12rem] accent-primary"
        :min="HISTORY_CARD_WIDTH_MIN"
        :max="HISTORY_CARD_WIDTH_MAX"
        @input="setHistoryCardWidth($event.target.value)"
      />
      <div class="flex flex-wrap gap-1">
        <Button
          v-for="p in HISTORY_CARD_WIDTH_PRESETS"
          :key="p.value"
          variant="outline"
          size="sm"
          class="h-6 px-2 text-[10px]"
          :class="historyCardLayout.cardWidth === p.value ? 'border-primary bg-primary/10' : ''"
          @click="applyHistoryCardWidthPreset(p.value)"
        >
          {{ p.label }}
        </Button>
      </div>
    </div>

    <div class="space-y-1">
      <Label class="text-xs">图片适配</Label>
      <SelectNative v-model="historyCardLayout.imageLayout" class="min-w-[7.5rem]">
        <option
          v-for="opt in HISTORY_IMAGE_LAYOUT_OPTIONS"
          :key="opt.id"
          :value="opt.id"
        >
          {{ opt.label }}
        </option>
      </SelectNative>
    </div>

    <div v-if="!historyCardIsNatural" class="space-y-1">
      <Label class="text-xs">画框比例</Label>
      <SelectNative v-model="historyCardLayout.aspectRatio" class="min-w-[6.5rem]">
        <option
          v-for="opt in HISTORY_ASPECT_OPTIONS"
          :key="opt.id"
          :value="opt.id"
        >
          {{ opt.label }}
        </option>
      </SelectNative>
    </div>
  </div>
</template>
