<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { prefersReducedMotion } from '@/lib/gsap/motion.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  imageUrl: { type: String, required: true },
  /** @type {{ label: string, value: string }[]} */
  rows: { type: Array, default: () => [] },
  hoverDelay: { type: Number, default: 1000 },
  /** aspect-square | 填满父级（父级需 position:relative 且有高度） */
  fill: { type: Boolean, default: false },
  aspectClass: { type: String, default: 'aspect-square' },
  imgClass: { type: String, default: 'object-contain' },
  alt: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['click'])

const flipped = ref(false)
let enterTimer = null

const displayRows = computed(() =>
  (props.rows || []).filter((r) => r?.value != null && String(r.value).trim() !== ''),
)

const canFlip = computed(() => !!props.imageUrl && !props.disabled)

function onPointerEnter() {
  if (!canFlip.value) return
  clearTimeout(enterTimer)
  const delay = prefersReducedMotion() ? 0 : props.hoverDelay
  enterTimer = setTimeout(() => {
    flipped.value = true
  }, delay)
}

function onPointerLeave() {
  clearTimeout(enterTimer)
  flipped.value = false
}

function onClick(ev) {
  if (flipped.value) {
    ev.stopPropagation()
    return
  }
  emit('click', ev)
}

onUnmounted(() => {
  clearTimeout(enterTimer)
})
</script>

<template>
  <div
    class="image-flip-card"
    :class="[
      fill ? 'image-flip-card--fill' : cn('w-full', aspectClass),
      flipped && 'is-flipped',
    ]"
    @pointerenter="onPointerEnter"
    @pointerleave="onPointerLeave"
    @click="onClick"
  >
    <div class="image-flip-card__perspective">
      <div class="image-flip-card__inner">
        <!-- 正面 -->
        <div class="image-flip-card__face image-flip-card__face--front">
          <img
            v-if="imageUrl"
            :src="imageUrl"
            :alt="alt"
            loading="lazy"
            draggable="false"
            :class="
              cn(
                'image-flip-card__front-img',
                imgClass,
                !disabled && 'cursor-zoom-in',
              )
            "
          />
          <div class="image-flip-card__front-overlay">
            <slot name="overlay" />
          </div>
        </div>

        <!-- 背面：模糊图 + 信息 -->
        <div class="image-flip-card__face image-flip-card__face--back">
          <img
            v-if="imageUrl"
            :src="imageUrl"
            alt=""
            aria-hidden="true"
            draggable="false"
            class="image-flip-card__back-blur"
          />
          <div class="image-flip-card__back-vignette" />
          <div class="image-flip-card__back-panel">
            <p class="image-flip-card__back-heading">生成信息</p>
            <dl v-if="displayRows.length" class="image-flip-card__meta">
              <div
                v-for="(row, i) in displayRows"
                :key="i"
                class="image-flip-card__meta-row"
              >
                <dt>{{ row.label }}</dt>
                <dd :title="String(row.value)">{{ row.value }}</dd>
              </div>
            </dl>
            <p v-else class="image-flip-card__empty">暂无参数记录</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-flip-card {
  position: relative;
  transform-style: preserve-3d;
  isolation: isolate;
}

.image-flip-card--fill {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.image-flip-card__perspective {
  position: absolute;
  inset: 0;
  perspective: 1000px;
  -webkit-perspective: 1000px;
}

.image-flip-card__inner {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 3rem;
  transform-style: preserve-3d;
  -webkit-transform-style: preserve-3d;
  transition: transform 0.62s cubic-bezier(0.4, 0.2, 0.2, 1);
  will-change: transform;
}

.image-flip-card.is-flipped .image-flip-card__inner {
  transform: rotateY(180deg);
}

.image-flip-card__face {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  overflow: hidden;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}

.image-flip-card__face--front {
  transform: rotateY(0deg) translateZ(1px);
  z-index: 2;
  background: hsl(0 0% 0% / 0.35);
}

.image-flip-card__face--back {
  transform: rotateY(180deg) translateZ(1px);
  z-index: 1;
  background: #0a0a0c;
}

.image-flip-card__front-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: hsl(0 0% 0% / 0.25);
}

.image-flip-card__front-overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  pointer-events: none;
}

.image-flip-card__front-overlay :deep(*) {
  pointer-events: auto;
}

/* 背面模糊：用真实 img + filter，避免 background + 3D 失效 */
.image-flip-card__back-blur {
  position: absolute;
  inset: -18%;
  width: 136%;
  height: 136%;
  max-width: none;
  object-fit: cover;
  object-position: center;
  /* filter: blur(32px) saturate(1.35) brightness(0.38) contrast(1.08); */
  filter: blur(5px) saturate(1.2) brightness(0.48) contrast(1.05);
  transform: scale(1.05);
  pointer-events: none;
  user-select: none;
}

.image-flip-card__back-vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(
      160deg,
      hsl(0 0% 100% / 0.08) 0%,
      transparent 38%,
      hsl(0 0% 0% / 0.55) 100%
    ),
    radial-gradient(ellipse at 30% 20%, hsl(var(--primary) / 0.22), transparent 55%),
    linear-gradient(to top, hsl(0 0% 0% / 0.88) 0%, hsl(0 0% 0% / 0.35) 50%, transparent 100%);
}

.image-flip-card__back-panel {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 0.55rem 0.65rem 0.6rem;
  color: #f5f5f5;
  text-shadow: 0 1px 3px rgb(0 0 0 / 0.9);
  pointer-events: none;
}

.image-flip-card__back-heading {
  margin: 0 0 0.3rem;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: hsl(var(--primary));
}

.image-flip-card__meta {
  margin: 0;
  max-height: 72%;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: hsl(0 0% 100% / 0.35) transparent;
}

.image-flip-card__meta-row {
  display: grid;
  grid-template-columns: 3rem 1fr;
  gap: 0.15rem 0.4rem;
  margin-bottom: 0.22rem;
  font-size: 0.6rem;
  line-height: 1.35;
}

.image-flip-card__meta-row dt {
  opacity: 0.75;
  font-weight: 600;
}

.image-flip-card__meta-row dd {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  word-break: break-word;
}

.image-flip-card__empty {
  margin: 0;
  font-size: 0.65rem;
  opacity: 0.8;
}

.image-flip-card.is-flipped {
  z-index: 25;
}

@media (prefers-reduced-motion: reduce) {
  .image-flip-card__inner {
    transition-duration: 0.18s;
  }
}
</style>
