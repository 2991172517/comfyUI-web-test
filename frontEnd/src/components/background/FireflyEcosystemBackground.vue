<script setup>
import { computed, ref } from 'vue'
import { useFireflyEcosystemCanvas } from '@/composables/useFireflyEcosystemCanvas.js'
import { useFireflyEcosystemTheme } from '@/composables/useFireflyEcosystemTheme.js'
import { prefersReducedMotion } from '@/lib/gsap/motion.js'
import { cn } from '@/lib/utils'
import { Shuffle } from 'lucide-vue-next'

const props = defineProps({
  /** login：全强度 + 控制条；ambient：内页低透明度衬底 */
  variant: { type: String, default: 'login' },
  /** 整体不透明度 0–1，ambient 默认较低 */
  intensity: { type: Number, default: null },
  showControls: { type: Boolean, default: null },
  fixed: { type: Boolean, default: true },
})

const canvasRef = ref(null)
const { modeId, paletteLabel, activeTheme, ECOSYSTEM_MODES, setMode, randomizeColors } =
  useFireflyEcosystemTheme()

const isAmbient = computed(() => props.variant === 'ambient')
const layerOpacity = computed(() => {
  if (props.intensity != null) return Math.min(1, Math.max(0, props.intensity))
  return isAmbient.value ? 0.32 : 1
})
const controlsVisible = computed(() => {
  if (props.showControls != null) return props.showControls
  return !isAmbient.value
})

const themeBodyClass = computed(() => activeTheme.value.bodyClass || '')
const themeStyle = computed(() => ({
  '--login-accent': activeTheme.value.accent,
  '--login-accent-rgb': activeTheme.value.accentRgb,
  '--login-text-secondary': activeTheme.value.textSecondary || '#8e8e93',
  opacity: layerOpacity.value,
}))

const reducedMotion = prefersReducedMotion()

const themeForCanvas = computed(() => ({
  ...activeTheme.value,
  /** 内页降低拖尾亮度，避免叠在 UI 上过抢眼 */
  trailAlpha: isAmbient.value ? 0.11 : 0.2,
}))

useFireflyEcosystemCanvas(canvasRef, themeForCanvas)
</script>

<template>
  <div
    :class="
      cn(
        'firefly-ecosystem-bg overflow-hidden bg-[#050505] text-white',
        fixed ? 'fixed inset-0 z-0' : 'absolute inset-0',
        themeBodyClass,
      )
    "
    :style="themeStyle"
    :aria-hidden="isAmbient ? 'true' : undefined"
  >
    <canvas
      v-if="!reducedMotion"
      ref="canvasRef"
      class="pointer-events-none absolute inset-0 z-0 h-full w-full"
    />
    <div
      v-else
      class="pointer-events-none absolute inset-0 z-0 bg-gradient-to-b from-[#050505] via-[#0a1220] to-[#050505]"
    />

    <div class="firefly-glass-overlay pointer-events-none absolute inset-0 z-[1]" />

    <div
      v-if="activeTheme.matrixUi"
      class="firefly-hud-corners pointer-events-none absolute inset-4 z-[2]"
    >
      <div />
    </div>

    <div
      v-if="controlsVisible"
      class="pointer-events-none absolute right-3 top-3 z-20 flex flex-col items-end gap-2 sm:right-4 sm:top-4"
    >
      <div
        class="pointer-events-auto flex items-center gap-1 rounded-lg border border-white/10 bg-black/45 p-1 backdrop-blur-md"
        style="opacity: 1"
      >
        <button
          v-for="m in ECOSYSTEM_MODES"
          :key="m.id"
          type="button"
          :class="
            cn(
              'min-w-[2rem] rounded-md px-2 py-1 text-[11px] font-semibold transition-colors',
              modeId === m.id
                ? 'bg-[color-mix(in_srgb,var(--login-accent)_28%,transparent)] text-[var(--login-accent)] shadow-sm'
                : 'text-white/55 hover:text-white/90',
            )
          "
          :title="m.name"
          @click="setMode(m.id)"
        >
          {{ m.label }}
        </button>
      </div>
      <button
        type="button"
        class="pointer-events-auto flex items-center gap-1.5 rounded-lg border border-white/10 bg-black/45 px-2.5 py-1.5 text-[11px] font-medium text-white/80 backdrop-blur-md transition-colors hover:border-[color-mix(in_srgb,var(--login-accent)_45%,transparent)] hover:text-[var(--login-accent)]"
        style="opacity: 1"
        title="随机切换配色"
        @click="randomizeColors"
      >
        <Shuffle class="h-3.5 w-3.5" />
        <span>随机配色</span>
        <span v-if="paletteLabel" class="text-[10px] opacity-70">· {{ paletteLabel }}</span>
      </button>
    </div>

    <div v-if="$slots.default" class="relative z-10 min-h-full">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.firefly-glass-overlay {
  background: radial-gradient(
    circle at 50% 50%,
    transparent 40%,
    rgba(0, 0, 0, 0.8) 100%
  );
}

.theme-2 .firefly-glass-overlay {
  background:
    radial-gradient(circle at 50% 50%, transparent 40%, rgba(0, 0, 0, 0.8) 100%),
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0, 255, 102, 0.03) 2px,
      rgba(0, 255, 102, 0.03) 4px
    );
}

.firefly-hud-corners::before,
.firefly-hud-corners::after,
.firefly-hud-corners > div::before,
.firefly-hud-corners > div::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  border: 2px solid color-mix(in srgb, var(--login-accent) 55%, transparent);
  opacity: 0.5;
}

.firefly-hud-corners::before {
  top: 0;
  left: 0;
  border-right: none;
  border-bottom: none;
}

.firefly-hud-corners::after {
  top: 0;
  right: 0;
  border-left: none;
  border-bottom: none;
}

.firefly-hud-corners > div::before {
  bottom: 0;
  left: 0;
  border-right: none;
  border-top: none;
}

.firefly-hud-corners > div::after {
  bottom: 0;
  right: 0;
  border-left: none;
  border-top: none;
}
</style>
