<script setup>
import Button from '@/components/ui/Button.vue'
import FavoriteStar from '@/components/FavoriteStar.vue'

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
</script>

<template>
  <article
    :class="[
      'flex min-h-0 flex-col overflow-hidden rounded-lg border bg-background transition-colors',
      selected ? 'border-violet-500 ring-2 ring-violet-500/40' : 'border-border',
    ]"
  >
    <template v-if="cell && imageUrl(cell)">
      <button
        type="button"
        class="relative flex aspect-[3/4] w-full items-center justify-center bg-muted/20 p-2 hover:bg-muted/35"
        :class="selectMode ? 'cursor-pointer' : 'cursor-zoom-in'"
        @click="selectMode ? emit('toggle-select') : emit('preview')"
      >
        <img
          :src="imageUrl(cell)"
          class="max-h-full max-w-full object-contain"
          loading="lazy"
          :alt="cell.label"
        />
        <label
          v-if="selectMode"
          class="absolute left-1 top-1 z-10 flex h-6 w-6 cursor-pointer items-center justify-center rounded-md border border-border bg-background/95 shadow-sm"
          @click.stop
        >
          <input
            type="checkbox"
            class="h-3.5 w-3.5 accent-violet-600"
            :checked="selected"
            @change="emit('toggle-select')"
          />
        </label>
        <FavoriteStar
          v-if="favoritePayload && !selectMode"
          :payload="favoritePayload"
          size="small"
          class="absolute right-1 top-1 z-10"
          @click.stop
        />
      </button>
      <div class="space-y-1 border-t border-border/60 p-2 text-[10px]">
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
        <div class="flex flex-wrap gap-1">
          <Button
            variant="outline"
            size="sm"
            class="h-7 flex-1 min-w-[3rem] text-[10px]"
            @click.stop="emit('save')"
          >
            保存
          </Button>
          <Button
            variant="outline"
            size="sm"
            class="h-7 flex-1 min-w-[3rem] text-[10px]"
            @click.stop="emit('detail')"
          >
            详情
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
      class="flex aspect-[3/4] items-center justify-center text-xs text-muted-foreground"
    >
      无图
    </div>
  </article>
</template>
