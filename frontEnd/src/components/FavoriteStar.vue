<script setup>
import { ref } from 'vue'
import { Star } from 'lucide-vue-next'
import { useFavorites } from '@/composables/useFavorites.js'
import { playFavoriteBurst } from '@/lib/gsap/favoriteBurst.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  payload: { type: Object, required: true },
  size: { type: String, default: 'normal' },
})

const emit = defineEmits(['toggled'])

const { isFavorited, toggleFavorite } = useFavorites()
const busy = ref(false)
const btnRef = ref(null)

async function onClick(e) {
  e?.stopPropagation?.()
  if (busy.value) return
  busy.value = true
  try {
    const res = await toggleFavorite(props.payload)
    const nowFav = isFavorited(props.payload)
    if (btnRef.value) {
      playFavoriteBurst(btnRef.value, { favorited: nowFav })
    }
    emit('toggled', res)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <button
    ref="btnRef"
    type="button"
    :title="isFavorited(payload) ? '取消收藏' : '收藏参数'"
    :disabled="busy"
    :class="
      cn(
        'inline-flex items-center justify-center rounded-md border border-border/80 bg-black/50 text-amber-400 backdrop-blur-sm transition-colors hover:bg-black/70 disabled:opacity-50',
        size === 'small' ? 'h-7 w-7' : 'h-8 w-8',
        isFavorited(payload) && 'border-amber-500/50 bg-amber-500/20',
      )
    "
    @click="onClick"
  >
    <Star
      :class="cn('h-4 w-4', isFavorited(payload) ? 'fill-amber-400' : 'fill-transparent')"
    />
  </button>
</template>
