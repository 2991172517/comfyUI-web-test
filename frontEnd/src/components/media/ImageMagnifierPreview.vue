<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { cn } from '@/lib/utils'
import { prefersReducedMotion } from '@/lib/gsap/motion.js'
import { useMagnifierSettings, MAGNIFIER_SHOW_DELAY_MS } from '@/composables/useMagnifierSettings.js'
import { lockMagnifierCursor } from '@/lib/magnifierCursor.js'
import {
  getDisplayedImageViewportRect,
  magnifierImageTransform,
  magnifierLensViewportPosition,
} from '@/lib/imageMagnifier.js'

const props = defineProps({
  src: { type: String, required: true },
  alt: { type: String, default: '' },
  /** 填满父级（absolute inset-0） */
  fill: { type: Boolean, default: false },
  imgClass: { type: String, default: 'object-contain' },
  rootClass: { type: String, default: '' },
  /** 未传时使用全局配置 */
  zoom: { type: Number, default: undefined },
  lensSize: { type: Number, default: undefined },
  borderWidth: { type: Number, default: undefined },
  disabled: { type: Boolean, default: false },
  /** 设置页：滚轮直接改全局放大倍数（同步滑块），无需等镜头出现 */
  wheelSyncGlobalZoom: { type: Boolean, default: false },
})

const emit = defineEmits(['click'])

const {
  lensSize: globalLensSize,
  borderWidth: globalBorderWidth,
  zoom: globalZoom,
  limits,
} = useMagnifierSettings()

const effectiveLensSize = computed(() => props.lensSize ?? globalLensSize.value)
const effectiveBorderWidth = computed(() => props.borderWidth ?? globalBorderWidth.value)
const effectiveZoom = computed(() => props.zoom ?? globalZoom.value)

/** 放大镜激活期间滚轮临时调节的倍数，离开后重置 */
const sessionZoom = ref(null)
const currentZoom = computed(() => sessionZoom.value ?? effectiveZoom.value)

const rootRef = ref(null)
const imgRef = ref(null)
const lensRef = ref(null)
const active = ref(false)
const lensEntered = ref(false)
const magnifierArmed = ref(false)

let showDelayTimer = null
let pendingPointerEvent = null

function clearShowDelay() {
  if (showDelayTimer != null) {
    clearTimeout(showDelayTimer)
    showDelayTimer = null
  }
  magnifierArmed.value = false
  pendingPointerEvent = null
}

function scheduleMagnifier(event) {
  pendingPointerEvent = event
  if (magnifierArmed.value) {
    updateMagnifier(event)
    return
  }
  if (showDelayTimer != null) return
  showDelayTimer = setTimeout(() => {
    showDelayTimer = null
    magnifierArmed.value = true
    if (pendingPointerEvent) updateMagnifier(pendingPointerEvent)
  }, MAGNIFIER_SHOW_DELAY_MS)
}

const canMagnify = computed(
  () =>
    !props.disabled &&
    !prefersReducedMotion() &&
    typeof window !== 'undefined' &&
    window.matchMedia('(hover: hover) and (pointer: fine)').matches,
)

const lens = ref({
  left: 0,
  top: 0,
  bgW: 0,
  bgH: 0,
  tx: 0,
  ty: 0,
})

function resetMagnifier() {
  active.value = false
  lensEntered.value = false
  sessionZoom.value = null
}

let releaseMagnifierCursor = null

function syncMagnifierCursor() {
  releaseMagnifierCursor?.()
  releaseMagnifierCursor = active.value && lensEntered.value ? lockMagnifierCursor() : null
}

watch(active, (isActive) => {
  if (!isActive) lensEntered.value = false
  syncMagnifierCursor()
})

function onLensAfterEnter() {
  lensEntered.value = true
  syncMagnifierCursor()
}

function onLensAfterLeave() {
  lensEntered.value = false
  syncMagnifierCursor()
}

function updateMagnifier(event) {
  const img = imgRef.value
  if (!canMagnify.value || !magnifierArmed.value || !img || !img.complete || !img.naturalWidth) return

  const displayed = getDisplayedImageViewportRect(img)
  if (!displayed) return

  const ix = event.clientX - displayed.left
  const iy = event.clientY - displayed.top

  if (ix < 0 || iy < 0 || ix > displayed.width || iy > displayed.height) {
    active.value = false
    return
  }

  active.value = true

  const size = effectiveLensSize.value
  const pos = magnifierLensViewportPosition(event.clientX, event.clientY, size)
  const bounds = { dispW: displayed.width, dispH: displayed.height }
  const tf = magnifierImageTransform(ix, iy, bounds, currentZoom.value, size)

  lens.value = {
    left: pos.left,
    top: pos.top,
    bgW: tf.bgW,
    bgH: tf.bgH,
    tx: tf.tx,
    ty: tf.ty,
  }
}

function onEnter(event) {
  if (!canMagnify.value) return
  scheduleMagnifier(event)
}

function onMove(event) {
  if (!canMagnify.value) return
  scheduleMagnifier(event)
}

function onLeave() {
  clearShowDelay()
  resetMagnifier()
}

function clampZoom(value) {
  return Math.min(limits.zoom.max, Math.max(limits.zoom.min, value))
}

function stepZoomFromWheel(event, baseZoom) {
  const step = limits.zoom.wheelStep ?? limits.zoom.step
  const delta = event.deltaY > 0 ? -step : step
  return clampZoom(baseZoom + delta)
}

function onWheel(event) {
  if (!canMagnify.value) return

  if (props.wheelSyncGlobalZoom) {
    event.preventDefault()
    const next = stepZoomFromWheel(event, effectiveZoom.value)
    if (props.zoom === undefined) {
      globalZoom.value = next
    }
    sessionZoom.value = null
    if (active.value || magnifierArmed.value) updateMagnifier(event)
    return
  }

  if (!active.value) return
  event.preventDefault()
  sessionZoom.value = stepZoomFromWheel(event, currentZoom.value)
  updateMagnifier(event)
}

function onClick(event) {
  emit('click', event)
}

onBeforeUnmount(() => {
  clearShowDelay()
  releaseMagnifierCursor?.()
  releaseMagnifierCursor = null
  resetMagnifier()
})
</script>

<template>
  <div
    ref="rootRef"
    :class="
      cn(
        'image-magnifier-root',
        fill ? 'absolute inset-0' : 'relative w-full h-full',
        canMagnify && (active && lensEntered ? 'cursor-none' : 'cursor-zoom-in'),
        rootClass,
      )
    "
    @mouseenter="onEnter"
    @mousemove="onMove"
    @mouseleave="onLeave"
    @wheel="onWheel"
  >
    <img
      ref="imgRef"
      :src="src"
      :alt="alt"
      :class="cn('block h-full w-full select-none pointer-events-none', imgClass)"
      loading="lazy"
      decoding="async"
      draggable="false"
      @load="resetMagnifier"
    />

    <div class="absolute inset-0" @click="onClick" />

    <slot name="overlay" />

    <Teleport to="body">
      <Transition
        name="magnifier-lens"
        @after-enter="onLensAfterEnter"
        @after-leave="onLensAfterLeave"
      >
        <div
          v-if="canMagnify && active"
          ref="lensRef"
          key="magnifier-lens"
          class="image-magnifier-lens pointer-events-none"
          :style="{
            left: `${lens.left}px`,
            top: `${lens.top}px`,
            width: `${effectiveLensSize}px`,
            height: `${effectiveLensSize}px`,
            borderWidth: `${effectiveBorderWidth}px`,
          }"
          aria-hidden="true"
        >
          <img
            :src="src"
            alt=""
            class="image-magnifier-lens__img"
            draggable="false"
            :style="{
              width: `${lens.bgW}px`,
              height: `${lens.bgH}px`,
              transform: `translate3d(${lens.tx}px, ${lens.ty}px, 0)`,
            }"
          />
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.image-magnifier-lens {
  position: fixed;
  z-index: 120;
  border-radius: 50%;
  overflow: hidden;
  border-style: solid;
  border-color: hsl(var(--primary) / 0.75);
  background-color: hsl(var(--background));
  box-shadow:
    0 0 0 2px hsl(var(--background) / 0.85),
    0 12px 32px hsl(0 0% 0% / 0.38);
  transform-origin: center center;
  will-change: transform, opacity;
}

.image-magnifier-lens__img {
  position: absolute;
  left: 0;
  top: 0;
  max-width: none;
  max-height: none;
  pointer-events: none;
  user-select: none;
  will-change: transform;
}
</style>

<style>
.magnifier-lens-enter-active {
  transition:
    opacity 0.3s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.magnifier-lens-leave-active {
  transition:
    opacity 0.18s ease-in,
    transform 0.18s ease-in;
}

.magnifier-lens-enter-from,
.magnifier-lens-leave-to {
  opacity: 0;
  transform: scale(0.82);
}

.magnifier-lens-enter-to,
.magnifier-lens-leave-from {
  opacity: 1;
  transform: scale(1);
}
</style>
