<script setup>
import { computed, ref, watch, useId } from 'vue'
import { X } from 'lucide-vue-next'

defineOptions({ inheritAttrs: true })

const props = defineProps({
  label: { type: String, default: '生成一张' },
  busyLabel: { type: String, default: '生成中…' },
  cancelLabel: { type: String, default: '取消生成' },
  /** idle | launch | cancel */
  mode: { type: String, default: 'idle' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['generate', 'cancel'])

const filterId = useId()
const launchTriggered = ref(false)

const isLaunch = computed(() => props.mode === 'launch' || launchTriggered.value)
const isCancel = computed(() => props.mode === 'cancel')

const idleChars = computed(() => [...props.label])
const busyChars = computed(() => [...props.busyLabel])
const cancelChars = computed(() => [...props.cancelLabel])

function onClick(event) {
  if (props.disabled) return
  if (isCancel.value) {
    emit('cancel', event)
    return
  }
  if (props.mode !== 'idle') return
  launchTriggered.value = true
  emit('generate', event)
}

watch(
  () => props.mode,
  (mode) => {
    if (mode === 'idle') launchTriggered.value = false
    if (mode === 'cancel') launchTriggered.value = false
  },
)
</script>

<template>
  <button
    type="button"
    class="generate-launch-btn"
    :class="{
      'is-launch': isLaunch && !isCancel,
      'is-cancel': isCancel,
      'is-disabled': disabled,
    }"
    :disabled="disabled"
    @click="onClick"
  >
    <span class="generate-launch-btn__outline" aria-hidden="true" />

    <span
      v-show="!isCancel"
      class="generate-launch-btn__state generate-launch-btn__state--idle"
    >
      <span class="generate-launch-btn__icon">
        <svg
          width="1em"
          height="1em"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <g :style="{ filter: `url(#${filterId})` }">
            <path
              d="M14.2199 21.63C13.0399 21.63 11.3699 20.8 10.0499 16.83L9.32988 14.67L7.16988 13.95C3.20988 12.63 2.37988 10.96 2.37988 9.78001C2.37988 8.61001 3.20988 6.93001 7.16988 5.60001L15.6599 2.77001C17.7799 2.06001 19.5499 2.27001 20.6399 3.35001C21.7299 4.43001 21.9399 6.21001 21.2299 8.33001L18.3999 16.82C17.0699 20.8 15.3999 21.63 14.2199 21.63ZM7.63988 7.03001C4.85988 7.96001 3.86988 9.06001 3.86988 9.78001C3.86988 10.5 4.85988 11.6 7.63988 12.52L10.1599 13.36C10.3799 13.43 10.5599 13.61 10.6299 13.83L11.4699 16.35C12.3899 19.13 13.4999 20.12 14.2199 20.12C14.9399 20.12 16.0399 19.13 16.9699 16.35L19.7999 7.86001C20.3099 6.32001 20.2199 5.06001 19.5699 4.41001C18.9199 3.76001 17.6599 3.68001 16.1299 4.19001L7.63988 7.03001Z"
              fill="currentColor"
            />
            <path
              d="M10.11 14.4C9.92005 14.4 9.73005 14.33 9.58005 14.18C9.29005 13.89 9.29005 13.41 9.58005 13.12L13.16 9.53C13.45 9.24 13.93 9.24 14.22 9.53C14.51 9.82 14.51 10.3 14.22 10.59L10.64 14.18C10.5 14.33 10.3 14.4 10.11 14.4Z"
              fill="currentColor"
            />
          </g>
          <defs>
            <filter :id="filterId">
              <feDropShadow dx="0" dy="1" stdDeviation="0.6" flood-opacity="0.5" />
            </filter>
          </defs>
        </svg>
      </span>
      <p>
        <span
          v-for="(char, i) in idleChars"
          :key="`idle-${i}-${char}`"
          :style="{ '--i': i }"
        >{{ char }}</span>
      </p>
    </span>

    <span
      v-show="!isCancel"
      class="generate-launch-btn__state generate-launch-btn__state--busy"
    >
      <span class="generate-launch-btn__icon">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          height="1em"
          width="1em"
          stroke-width="0.5px"
          stroke="black"
          aria-hidden="true"
        >
          <g :style="{ filter: `url(#${filterId}-ok)` }">
            <path
              fill="currentColor"
              d="M12 22.75C6.07 22.75 1.25 17.93 1.25 12C1.25 6.07 6.07 1.25 12 1.25C17.93 1.25 22.75 6.07 22.75 12C22.75 17.93 17.93 22.75 12 22.75ZM12 2.75C6.9 2.75 2.75 6.9 2.75 12C2.75 17.1 6.9 21.25 12 21.25C17.1 21.25 21.25 17.1 21.25 12C21.25 6.9 17.1 2.75 12 2.75Z"
            />
            <path
              fill="currentColor"
              d="M10.5795 15.5801C10.3795 15.5801 10.1895 15.5001 10.0495 15.3601L7.21945 12.5301C6.92945 12.2401 6.92945 11.7601 7.21945 11.4701C7.50945 11.1801 7.98945 11.1801 8.27945 11.4701L10.5795 13.7701L15.7195 8.6301C16.0095 8.3401 16.4895 8.3401 16.7795 8.6301C17.0695 8.9201 17.0695 9.4001 16.7795 9.6901L11.1095 15.3601C10.9695 15.5001 10.7795 15.5801 10.5795 15.5801Z"
            />
          </g>
          <defs>
            <filter :id="`${filterId}-ok`">
              <feDropShadow dx="0" dy="1" stdDeviation="0.6" flood-opacity="0.5" />
            </filter>
          </defs>
        </svg>
      </span>
      <p>
        <span
          v-for="(char, i) in busyChars"
          :key="`busy-${i}-${char}`"
          :style="{ '--i': i + 5 }"
        >{{ char }}</span>
      </p>
    </span>

    <span
      v-if="isCancel"
      :key="cancelLabel"
      class="generate-launch-btn__state generate-launch-btn__state--cancel"
    >
      <span class="generate-launch-btn__icon generate-launch-btn__icon--cancel">
        <X class="h-[1.1em] w-[1.1em]" aria-hidden="true" />
      </span>
      <p>
        <span
          v-for="(char, i) in cancelChars"
          :key="`cancel-${i}-${char}`"
          :style="{ '--i': i }"
        >{{ char }}</span>
      </p>
    </span>
  </button>
</template>

<style scoped>
.generate-launch-btn {
  --gl-accent: hsl(217 91% 60%);
  --gl-neutral-1: #f7f8f7;
  --gl-neutral-2: #e7e7e7;
  --gl-radius: 14px;

  cursor: pointer;
  border-radius: var(--gl-radius);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.3);
  border: none;
  box-shadow:
    0 0.5px 0.5px 1px rgba(255, 255, 255, 0.2),
    0 10px 20px rgba(0, 0, 0, 0.2),
    0 4px 5px 0 rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.3s ease;
  min-width: 11rem;
  padding: 0 1.25rem;
  height: 3rem;
  font-family: inherit;
  font-size: 1rem;
  font-weight: 600;
  color: #1a1a1a;
}

.generate-launch-btn:hover:not(.is-disabled) {
  transform: scale(1.02);
  box-shadow:
    0 0 1px 2px rgba(255, 255, 255, 0.3),
    0 15px 30px rgba(0, 0, 0, 0.3),
    0 10px 3px -3px rgba(0, 0, 0, 0.04);
}

.generate-launch-btn:active:not(.is-disabled) {
  transform: scale(1);
}

.generate-launch-btn:focus-visible:not(.is-disabled) {
  outline: none;
}

.generate-launch-btn.is-disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.generate-launch-btn.is-cancel::after {
  background:
    linear-gradient(var(--gl-neutral-1), var(--gl-neutral-2)) padding-box,
    linear-gradient(to bottom, rgba(59, 130, 246, 0.15), rgba(37, 99, 235, 0.35)) border-box;
}

.generate-launch-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--gl-radius);
  border: 2.5px solid transparent;
  background:
    linear-gradient(var(--gl-neutral-1), var(--gl-neutral-2)) padding-box,
    linear-gradient(to bottom, rgba(0, 0, 0, 0.1), rgba(0, 0, 0, 0.45)) border-box;
  z-index: 0;
  transition: all 0.4s ease;
}

.generate-launch-btn:hover:not(.is-disabled)::after {
  transform: scale(1.05, 1.1);
  box-shadow: inset 0 -1px 3px 0 rgba(255, 255, 255, 1);
}

.generate-launch-btn::before {
  content: '';
  inset: 7px 6px 6px;
  position: absolute;
  background: linear-gradient(to top, var(--gl-neutral-1), var(--gl-neutral-2));
  border-radius: 30px;
  filter: blur(0.5px);
  z-index: 2;
}

.generate-launch-btn__outline {
  position: absolute;
  border-radius: inherit;
  overflow: hidden;
  z-index: 1;
  opacity: 0;
  transition: opacity 0.4s ease;
  inset: -2px -3.5px;
}

.generate-launch-btn__outline::before {
  content: '';
  position: absolute;
  inset: -100%;
  background: conic-gradient(from 180deg, transparent 60%, hsl(217 91% 75%) 80%, transparent 100%);
  animation: gl-spin 2s linear infinite;
  animation-play-state: paused;
}

.generate-launch-btn:hover:not(.is-disabled) .generate-launch-btn__outline {
  opacity: 1;
}

.generate-launch-btn:hover:not(.is-disabled) .generate-launch-btn__outline::before {
  animation-play-state: running;
}

@keyframes gl-spin {
  to {
    transform: rotate(360deg);
  }
}

.generate-launch-btn__state {
  padding-left: 1.75rem;
  z-index: 3;
  display: flex;
  position: relative;
  align-items: center;
}

.generate-launch-btn__state p {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  white-space: nowrap;
}

.generate-launch-btn__icon {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  margin: auto;
  transform: scale(1.25);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.generate-launch-btn__icon--cancel {
  color: hsl(217 91% 48%);
}

.generate-launch-btn__icon svg {
  overflow: visible;
}

.generate-launch-btn__state p span {
  display: block;
  opacity: 0;
  animation: gl-slide-down 0.8s ease forwards calc(var(--i) * 0.03s);
}

.generate-launch-btn:hover:not(.is-disabled):not(.is-launch) .generate-launch-btn__state--idle p span,
.generate-launch-btn.is-cancel:hover:not(.is-disabled) .generate-launch-btn__state--cancel p span {
  animation: gl-wave 0.5s ease forwards calc(var(--i) * 0.02s);
}

.generate-launch-btn.is-launch .generate-launch-btn__state--idle p span {
  animation: gl-disappear 0.6s ease forwards calc(var(--i) * 0.03s);
}

@keyframes gl-wave {
  30% {
    opacity: 1;
    transform: translateY(4px);
  }
  50% {
    opacity: 1;
    transform: translateY(-3px);
    color: var(--gl-accent);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes gl-slide-down {
  0% {
    opacity: 0;
    transform: translateY(-20px) translateX(5px) rotate(-90deg);
    color: var(--gl-accent);
    filter: blur(5px);
  }
  30% {
    opacity: 1;
    transform: translateY(4px);
    filter: blur(0);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes gl-disappear {
  to {
    opacity: 0;
    transform: translateX(5px) translateY(20px);
    color: var(--gl-accent);
    filter: blur(5px);
  }
}

.generate-launch-btn__state--busy {
  display: none;
}

.generate-launch-btn__state--idle .generate-launch-btn__icon svg {
  animation: gl-land 0.6s ease forwards;
}

.generate-launch-btn:hover:not(.is-disabled):not(.is-launch):not(.is-cancel) .generate-launch-btn__state--idle .generate-launch-btn__icon {
  transform: rotate(45deg) scale(1.25);
}

.generate-launch-btn.is-launch .generate-launch-btn__state--idle {
  position: absolute;
}

.generate-launch-btn.is-launch .generate-launch-btn__state--busy {
  display: flex;
}

.generate-launch-btn.is-launch .generate-launch-btn__state--idle .generate-launch-btn__icon svg {
  animation: gl-take-off 0.8s linear forwards;
}

.generate-launch-btn.is-launch .generate-launch-btn__state--idle .generate-launch-btn__icon {
  transform: rotate(0) scale(1.25);
}

@keyframes gl-take-off {
  0% {
    opacity: 1;
  }
  60% {
    opacity: 1;
    transform: translateX(70px) rotate(45deg) scale(2);
  }
  100% {
    opacity: 0;
    transform: translateX(160px) rotate(45deg) scale(0);
  }
}

@keyframes gl-land {
  0% {
    transform: translateX(-60px) translateY(30px) rotate(-50deg) scale(2);
    opacity: 0;
    filter: blur(3px);
  }
  100% {
    transform: translateX(0) translateY(0) rotate(0);
    opacity: 1;
    filter: blur(0);
  }
}

.generate-launch-btn.is-launch .generate-launch-btn__state--idle .generate-launch-btn__icon::before {
  content: '';
  position: absolute;
  top: 50%;
  height: 2px;
  width: 0;
  left: -5px;
  background: linear-gradient(to right, transparent, rgba(0, 0, 0, 0.5));
  animation: gl-contrail 0.8s linear forwards;
}

@keyframes gl-contrail {
  0% {
    width: 0;
    opacity: 1;
  }
  60% {
    opacity: 0.7;
    width: 80px;
  }
  100% {
    opacity: 0;
    width: 160px;
  }
}

.generate-launch-btn.is-launch .generate-launch-btn__state--busy p span {
  opacity: 0;
  animation: gl-slide-down 0.8s ease forwards calc(var(--i) * 0.08s);
}

.generate-launch-btn.is-launch .generate-launch-btn__state--busy .generate-launch-btn__icon svg {
  opacity: 0;
  animation: gl-appear 1.2s ease forwards 0.8s;
}

@keyframes gl-appear {
  0% {
    opacity: 0;
    transform: scale(4) rotate(-40deg);
    color: var(--gl-accent);
    filter: blur(4px);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
    filter: blur(0);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.generate-launch-btn.is-cancel .generate-launch-btn__state--cancel p span {
  opacity: 1;
  transform: none;
  filter: none;
  animation: gl-slide-down 0.55s ease forwards calc(var(--i) * 0.04s);
}
</style>
