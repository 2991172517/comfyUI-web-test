<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Eraser, Paintbrush, RotateCcw, Undo2, Upload } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import { getAccessToken } from '@/composables/useAuth.js'
import { cn } from '@/lib/utils'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['image-loaded', 'mask-changed'])

const MAX_UNDO = 40
const MAX_STAGE_VH = 0.7
const MAX_STAGE_PX = 720

const fileInput = ref(null)
const wrapRef = ref(null)
const displayRef = ref(null)
const maskRef = ref(null)

const imageBitmap = ref(null)
const imageWidth = ref(0)
const imageHeight = ref(0)
const stageDisplayW = ref(0)
const stageDisplayH = ref(0)
const sourceFile = ref(null)
const sourcePreviewUrl = ref('')
const imageName = ref('')
const brushSize = ref(48)
const erasing = ref(false)
const painting = ref(false)
const hasMask = ref(false)
const canUndo = ref(false)

/** @type {ImageData[]} */
const undoStack = []
let undoIndex = -1
let strokeStarted = false
let resizeObserver = null

const canPaint = computed(() => !!imageBitmap.value && !props.disabled)

const stageBoxStyle = computed(() => {
  if (!stageDisplayW.value || !stageDisplayH.value) return {}
  return {
    width: `${stageDisplayW.value}px`,
    height: `${stageDisplayH.value}px`,
  }
})

const canvasCssStyle = computed(() => {
  if (!stageDisplayW.value || !stageDisplayH.value) return {}
  return {
    width: `${stageDisplayW.value}px`,
    height: `${stageDisplayH.value}px`,
    touchAction: 'none',
  }
})

function revokePreviewUrl() {
  if (sourcePreviewUrl.value) {
    URL.revokeObjectURL(sourcePreviewUrl.value)
    sourcePreviewUrl.value = ''
  }
}

function updateStageLayout() {
  const wrap = wrapRef.value
  if (!wrap || !imageWidth.value || !imageHeight.value) {
    stageDisplayW.value = 0
    stageDisplayH.value = 0
    return
  }
  const maxW = Math.max(1, wrap.clientWidth)
  const maxH = Math.min(window.innerHeight * MAX_STAGE_VH, MAX_STAGE_PX)
  const s = Math.min(maxW / imageWidth.value, maxH / imageHeight.value)
  stageDisplayW.value = Math.max(1, Math.round(imageWidth.value * s))
  stageDisplayH.value = Math.max(1, Math.round(imageHeight.value * s))
}

function snapshotMask() {
  const canvas = maskRef.value
  if (!canvas?.width) return null
  const ctx = canvas.getContext('2d')
  return ctx.getImageData(0, 0, canvas.width, canvas.height)
}

function maskHasPaint(data) {
  if (!data) return false
  const a = data.data
  for (let i = 3; i < a.length; i += 4) {
    if (a[i] > 8) return true
  }
  return false
}

function restoreMask(data) {
  const canvas = maskRef.value
  if (!canvas || !data) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.putImageData(data, 0, 0)
  hasMask.value = maskHasPaint(data)
  emit('mask-changed')
}

function resetUndoStack() {
  undoStack.length = 0
  undoIndex = -1
  const snap = snapshotMask()
  if (snap) {
    undoStack.push(snap)
    undoIndex = 0
  }
  canUndo.value = false
}

function pushUndoState() {
  const snap = snapshotMask()
  if (!snap) return
  const prev = undoStack[undoIndex]
  if (prev?.data?.length === snap.data.length) {
    const same = prev.data.every((v, i) => v === snap.data[i])
    if (same) return
  }
  undoStack.splice(undoIndex + 1)
  undoStack.push(snap)
  while (undoStack.length > MAX_UNDO) {
    undoStack.shift()
    undoIndex -= 1
  }
  undoIndex = undoStack.length - 1
  canUndo.value = undoIndex > 0
}

function undo() {
  if (undoIndex <= 0) return
  undoIndex -= 1
  restoreMask(undoStack[undoIndex])
  canUndo.value = undoIndex > 0
}

function onKeyDown(ev) {
  if (!(ev.ctrlKey || ev.metaKey) || ev.key.toLowerCase() !== 'z') return
  if (!canPaint.value) return
  const tag = ev.target?.tagName?.toLowerCase()
  if (tag === 'input' || tag === 'textarea') return
  ev.preventDefault()
  undo()
}

/** 画布像素坐标：显示区按原图等比缩放，scaleX 应等于 scaleY */
function pointerPos(ev, canvas) {
  const rect = canvas.getBoundingClientRect()
  if (!rect.width || !rect.height) return { x: 0, y: 0 }
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  return {
    x: Math.max(0, Math.min(canvas.width, (ev.clientX - rect.left) * scaleX)),
    y: Math.max(0, Math.min(canvas.height, (ev.clientY - rect.top) * scaleY)),
  }
}

function drawDot(ctx, x, y, size, erase) {
  ctx.save()
  ctx.globalCompositeOperation = erase ? 'destination-out' : 'source-over'
  ctx.fillStyle = erase ? 'rgba(0,0,0,1)' : 'rgba(255,80,80,0.85)'
  ctx.beginPath()
  ctx.arc(x, y, size / 2, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()
}

function drawLine(ctx, x0, y0, x1, y1, size, erase) {
  const dist = Math.hypot(x1 - x0, y1 - y0)
  const steps = Math.max(1, Math.ceil(dist / (size * 0.35)))
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    drawDot(ctx, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, size, erase)
  }
}

let last = null

function onPointerDown(ev) {
  if (!canPaint.value) return
  ev.preventDefault()
  const canvas = maskRef.value
  if (!canvas) return
  painting.value = true
  strokeStarted = true
  canvas.setPointerCapture(ev.pointerId)
  const p = pointerPos(ev, canvas)
  last = p
  const ctx = canvas.getContext('2d')
  drawDot(ctx, p.x, p.y, brushSize.value, erasing.value)
  hasMask.value = true
  emit('mask-changed')
}

function onPointerMove(ev) {
  if (!painting.value || !last) return
  const canvas = maskRef.value
  if (!canvas) return
  const p = pointerPos(ev, canvas)
  const ctx = canvas.getContext('2d')
  drawLine(ctx, last.x, last.y, p.x, p.y, brushSize.value, erasing.value)
  last = p
  hasMask.value = true
  emit('mask-changed')
}

function finishStroke() {
  if (strokeStarted) {
    pushUndoState()
    strokeStarted = false
  }
  painting.value = false
  last = null
}

function onPointerUp(ev) {
  if (!painting.value) return
  const canvas = maskRef.value
  if (canvas?.hasPointerCapture?.(ev.pointerId)) {
    canvas.releasePointerCapture(ev.pointerId)
  }
  finishStroke()
}

function resizeCanvases(w, h) {
  for (const c of [displayRef.value, maskRef.value]) {
    if (!c) continue
    c.width = w
    c.height = h
  }
  const maskCtx = maskRef.value?.getContext('2d')
  if (maskCtx) {
    maskCtx.clearRect(0, 0, w, h)
  }
  hasMask.value = false
  resetUndoStack()
}

function drawImageToDisplay() {
  const img = imageBitmap.value
  const canvas = displayRef.value
  if (!img || !canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
}

function fetchHeadersForImage() {
  const token = getAccessToken()
  return token ? { 'X-Access-Token': token } : {}
}

function resolveFetchUrl(url) {
  const s = String(url || '').trim()
  if (!s) return ''
  if (s.startsWith('http://') || s.startsWith('https://')) return s
  if (typeof window !== 'undefined' && s.startsWith('/')) {
    return `${window.location.origin}${s}`
  }
  return s
}

async function loadImageFromUrlViaCanvas(url, filename = 'inpaint_source.png') {
  const src = resolveFetchUrl(url)
  const img = new Image()
  img.crossOrigin = 'anonymous'
  await new Promise((resolve, reject) => {
    img.onload = () => resolve()
    img.onerror = () => reject(new Error('图片解码失败'))
    img.src = src
  })
  const canvas = document.createElement('canvas')
  canvas.width = img.naturalWidth
  canvas.height = img.naturalHeight
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('无法创建画布')
  ctx.drawImage(img, 0, 0)
  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error('无法导出图片'))),
      'image/png',
    )
  })
  const file = new File([blob], filename, { type: 'image/png' })
  await loadFile(file)
}

async function loadImageFromUrl(url, filename = 'inpaint_source.png') {
  const resolved = resolveFetchUrl(url)
  if (!resolved) throw new Error('无效的图片地址')

  try {
    const res = await fetch(resolved, {
      credentials: 'include',
      headers: fetchHeadersForImage(),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const blob = await res.blob()
    if (!blob.size) throw new Error('空文件')
    const type =
      blob.type && blob.type.startsWith('image/') ? blob.type : 'image/png'
    const file = new File([blob], filename || 'inpaint_source.png', { type })
    await loadFile(file)
  } catch {
    await loadImageFromUrlViaCanvas(resolved, filename)
  }
}

async function loadFile(file) {
  if (!file?.type?.startsWith('image/')) {
    throw new Error('请选择图片文件')
  }
  revokePreviewUrl()
  const bmp = await createImageBitmap(file)
  sourceFile.value = file
  sourcePreviewUrl.value = URL.createObjectURL(file)
  imageBitmap.value = bmp
  imageWidth.value = bmp.width
  imageHeight.value = bmp.height
  imageName.value = file.name
  resizeCanvases(bmp.width, bmp.height)
  await nextTick()
  updateStageLayout()
  drawImageToDisplay()
  emit('image-loaded', { file, width: bmp.width, height: bmp.height })
  emit('mask-changed')
}

function pickFile() {
  if (props.disabled) return
  fileInput.value?.click()
}

async function onFileChange(ev) {
  const file = ev.target.files?.[0]
  ev.target.value = ''
  if (!file) return
  try {
    await loadFile(file)
  } catch (e) {
    console.error(e)
  }
}

function clearMask() {
  const canvas = maskRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  hasMask.value = false
  pushUndoState()
  emit('mask-changed')
}

function getSourceFile() {
  return sourceFile.value
}

function getSourcePreviewUrl() {
  return sourcePreviewUrl.value
}

function bindResizeObserver() {
  if (!wrapRef.value || typeof ResizeObserver === 'undefined') return
  resizeObserver?.disconnect()
  resizeObserver = new ResizeObserver(() => {
    updateStageLayout()
  })
  resizeObserver.observe(wrapRef.value)
}

defineExpose({
  getMaskCanvas: () => maskRef.value,
  getSourceFile,
  getSourcePreviewUrl,
  loadFile,
  loadImageFromUrl,
  hasMask: () => hasMask.value,
  clearMask,
  undo,
  imageName,
})

watch(imageBitmap, () => {
  requestAnimationFrame(() => {
    updateStageLayout()
    drawImageToDisplay()
  })
})

onMounted(() => {
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('resize', updateStageLayout)
  bindResizeObserver()
})

onUnmounted(() => {
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('resize', updateStageLayout)
  resizeObserver?.disconnect()
  revokePreviewUrl()
  imageBitmap.value?.close?.()
})
</script>

<template>
  <div class="space-y-3">
    <input
      ref="fileInput"
      type="file"
      accept="image/png,image/jpeg,image/webp"
      class="hidden"
      @change="onFileChange"
    />

    <div class="flex flex-wrap items-center gap-2">
      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="disabled"
        @click="pickFile"
      >
        <Upload class="mr-1 h-3.5 w-3.5" />
        上传原图
      </Button>
      <span
        v-if="imageName"
        class="text-xs text-muted-foreground truncate max-w-[12rem]"
        :title="imageName"
      >
        {{ imageName }}
      </span>
      <div class="ml-auto flex flex-wrap items-center gap-1">
        <Button
          type="button"
          size="sm"
          :variant="!erasing ? 'default' : 'outline'"
          :disabled="!canPaint"
          @click="erasing = false"
        >
          <Paintbrush class="mr-1 h-3.5 w-3.5" />
          画笔
        </Button>
        <Button
          type="button"
          size="sm"
          :variant="erasing ? 'default' : 'outline'"
          :disabled="!canPaint"
          @click="erasing = true"
        >
          <Eraser class="mr-1 h-3.5 w-3.5" />
          橡皮
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          :disabled="!canUndo"
          title="Ctrl+Z 撤回"
          @click="undo"
        >
          <Undo2 class="mr-1 h-3.5 w-3.5" />
          撤回
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          :disabled="!canPaint"
          @click="clearMask"
        >
          <RotateCcw class="mr-1 h-3.5 w-3.5" />
          清空
        </Button>
      </div>
    </div>

    <div class="space-y-1">
      <Label class="text-xs text-muted-foreground">
        画笔大小（{{ brushSize }}px，按原图像素）· Ctrl+Z 撤回
      </Label>
      <input
        v-model.number="brushSize"
        type="range"
        min="8"
        max="160"
        step="4"
        class="w-full accent-primary"
        :disabled="!canPaint"
      />
    </div>

    <div
      ref="wrapRef"
      :class="
        cn(
          'flex w-full justify-center overflow-hidden rounded-lg border border-border bg-muted/30 py-2',
          !imageBitmap && 'min-h-[280px] items-center',
        )
      "
    >
      <p
        v-if="!imageBitmap"
        class="text-sm text-muted-foreground px-4 text-center"
      >
        上传图片后，在图上涂抹<span class="text-foreground">红色区域</span>为将要重绘的部分
      </p>
      <div
        v-show="imageBitmap && stageDisplayW"
        class="relative shrink-0"
        :style="stageBoxStyle"
      >
        <canvas
          ref="displayRef"
          class="block"
          :width="imageWidth"
          :height="imageHeight"
          :style="canvasCssStyle"
        />
        <canvas
          ref="maskRef"
          class="absolute left-0 top-0 cursor-crosshair opacity-70"
          :width="imageWidth"
          :height="imageHeight"
          :style="canvasCssStyle"
          @pointerdown="onPointerDown"
          @pointermove="onPointerMove"
          @pointerleave="finishStroke"
        />
      </div>
    </div>

    <p class="text-[11px] text-muted-foreground leading-relaxed">
      涂抹区域=重绘；未涂区域=保留。预览按原图比例缩放，蒙版像素与原图一致（{{ imageWidth }}×{{ imageHeight }}）。
    </p>
  </div>
</template>
