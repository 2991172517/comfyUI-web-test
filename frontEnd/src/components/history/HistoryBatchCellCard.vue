<script setup>
import { computed } from 'vue'
import { Check } from 'lucide-vue-next'
import {
  historyBatchCellImageHeight,
  historyCardImgClass,
  historyCardIsNatural,
  historyCardThumbBoxStyle,
} from '@/composables/useHistoryCardLayout.js'
import Button from '@/components/ui/Button.vue'
import FavoriteStar from '@/components/FavoriteStar.vue'
import ImageMagnifierPreview from '@/components/media/ImageMagnifierPreview.vue'

defineProps({
  cell: { type: Object, default: null },
  ia: { type: Number, default: 0 },
  ib: { type: Number, default: 0 },
  showAxis: { type: Boolean, default: true },
  matrixCols: { type: Number, default: 0 },
  favoritePayload: { type: Object, default: null },
  selectMode: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['preview', 'detail', 'regenerate', 'save', 'toggle-select'])

function imageUrl(cell) {
  return cell?.images?.[0]?.url
}

const imageBoxStyle = computed(() => {
  const h = historyBatchCellImageHeight.value
  if (h == null) return { minHeight: '6rem' }
  return { height: `${h}px` }
})
</script>

<template>
  <article
    :class="[
      'flex min-h-0 w-full max-w-full flex-col overflow-hidden rounded-lg border bg-background transition-colors',
      selected ? 'border-violet-500 ring-2 ring-violet-500/40' : 'border-border',
    ]"
  >
    <template v-if="cell && imageUrl(cell)">
      <button
        type="button"
        class="relative flex w-full cursor-zoom-in items-center justify-center bg-muted/20 p-0 hover:bg-muted/35 overflow-hidden"
        :class="selectMode ? 'cursor-pointer' : ''"
        :style="[imageBoxStyle, historyCardIsNatural ? {} : historyCardThumbBoxStyle]"
        @click="selectMode ? emit('toggle-select') : emit('preview')"
      >
        <ImageMagnifierPreview
          :fill="!historyCardIsNatural"
          :src="imageUrl(cell)"
          :alt="cell.label"
          :img-class="historyCardImgClass"
          :root-class="historyCardIsNatural ? 'relative w-full' : ''"
          :disabled="selectMode"
        />
        <button
          v-if="selectMode"
          type="button"
          class="absolute right-1 top-1 z-10 flex h-7 w-7 items-center justify-center rounded-full border-2 shadow-md transition-colors"
          :class="
            selected
              ? 'border-violet-500 bg-violet-600 text-white'
              : 'border-white/90 bg-background/90 text-transparent hover:border-violet-400'
          "
          :aria-label="selected ? '取消选择' : '选择'"
          @click.stop="emit('toggle-select')"
        >
          <Check class="h-4 w-4" :class="selected ? 'opacity-100' : 'opacity-0'" />
        </button>
        <FavoriteStar
          v-if="favoritePayload && !selectMode"
          :payload="favoritePayload"
          size="small"
          class="absolute right-1 top-1 z-10"
          @click.stop
        />
      </button>
      <div
        class="cursor-pointer space-y-1 border-t border-border/60 p-2 text-[10px] transition-colors hover:bg-accent/40"
        @click="emit('detail')"
      >
        <p v-if="showAxis" class="font-medium">
          A{{ ia }}×B{{ ib }}
          <span class="font-normal text-muted-foreground">
            · {{ cell.loras?.A?.strength_model }} / {{ cell.loras?.B?.strength_model }}
          </span>
        </p>
        <p v-else class="font-medium text-muted-foreground">
          #{{ cell.index ?? (matrixCols ? ia * matrixCols + ib : ia * 99 + ib) }}
          <span v-if="ia != null && ib != null"> · A{{ ia }}×B{{ ib }}</span>
        </p>
        <div class="flex flex-wrap gap-1" @click.stop>
          <Button
            variant="outline"
            size="sm"
            class="h-7 flex-1 min-w-[3rem] text-[10px]"
            @click.stop="emit('save')"
          >
            保存
          </Button>
          <Button
            variant="secondary"
            size="sm"
            class="h-7 flex-1 min-w-[3rem] text-[10px]"
            @click.stop="emit('regenerate')"
          >
            生成
          </Button>
        </div>
      </div>
    </template>
    <div
      v-else
      class="flex w-full items-center justify-center text-xs text-muted-foreground"
      :style="imageBoxStyle"
    >
      无图
    </div>
  </article>
</template>
