import { computed, reactive, watch } from 'vue'

const WIDTH_KEY = 'custom_project_history_card_width'
const LAYOUT_KEY = 'custom_project_history_image_layout'
const ASPECT_KEY = 'custom_project_history_card_aspect'

export const HISTORY_CARD_WIDTH_MIN = 160
export const HISTORY_CARD_WIDTH_MAX = 600
export const HISTORY_CARD_WIDTH_DEFAULT = 280

export const HISTORY_CARD_WIDTH_PRESETS = [
  { label: '窄', value: 200 },
  { label: '默认', value: 260 },
  { label: '适中', value: 360 },
  { label: '宽', value: 400 },
  { label: '超宽', value: 440 },
]

export const HISTORY_IMAGE_LAYOUT_OPTIONS = [
  { id: 'natural', label: '原比例', hint: '高度随图片变化' },
  { id: 'contain', label: '完整显示', hint: '统一画框，不裁切' },
  { id: 'cover', label: '填充裁切', hint: '统一画框，铺满裁切' },
]

export const HISTORY_ASPECT_OPTIONS = [
  { id: '4/5', label: '竖图 4:5' },
  { id: '3/4', label: '竖图 3:4' },
  { id: '1/1', label: '方形 1:1' },
  { id: '4/3', label: '横图 4:3' },
  { id: '16/9', label: '宽屏 16:9' },
]

const LEGACY_BATCH_CELL_KEY = 'batch-grid-cell-size'

function readWidth() {
  try {
    const n = Number(localStorage.getItem(WIDTH_KEY))
    if (Number.isFinite(n)) {
      return Math.min(HISTORY_CARD_WIDTH_MAX, Math.max(HISTORY_CARD_WIDTH_MIN, Math.round(n)))
    }
    const legacy = Number(localStorage.getItem(LEGACY_BATCH_CELL_KEY))
    if (Number.isFinite(legacy) && legacy >= HISTORY_CARD_WIDTH_MIN) {
      return Math.min(HISTORY_CARD_WIDTH_MAX, Math.max(HISTORY_CARD_WIDTH_MIN, Math.round(legacy)))
    }
  } catch {
    /* ignore */
  }
  return HISTORY_CARD_WIDTH_DEFAULT
}

function readLayout() {
  try {
    const v = localStorage.getItem(LAYOUT_KEY)
    if (v === 'natural' || v === 'contain' || v === 'cover') return v
  } catch {
    /* ignore */
  }
  return 'natural'
}

function readAspect() {
  try {
    const v = localStorage.getItem(ASPECT_KEY)
    if (HISTORY_ASPECT_OPTIONS.some((o) => o.id === v)) return v
  } catch {
    /* ignore */
  }
  return '4/5'
}

/** 单例：筛选栏与列表共用，模板可直接 v-model */
export const historyCardLayout = reactive({
  cardWidth: readWidth(),
  imageLayout: readLayout(),
  aspectRatio: readAspect(),
})

/** 固定列宽；勿用 minmax(_, 1fr)，否则单列时会拉满整页 */
export const historyCardGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, ${historyCardLayout.cardWidth}px)`,
  justifyContent: 'start',
}))

export const historyCardIsNatural = computed(
  () => historyCardLayout.imageLayout === 'natural',
)

export const historyCardThumbBoxStyle = computed(() => {
  if (historyCardLayout.imageLayout === 'natural') return {}
  return { aspectRatio: historyCardLayout.aspectRatio }
})

export const historyCardImgClass = computed(() => {
  if (historyCardLayout.imageLayout === 'natural') {
    return 'w-full h-auto max-h-[min(70vh,520px)] object-contain'
  }
  return historyCardLayout.imageLayout === 'cover' ? 'object-cover' : 'object-contain'
})

/** 批量 A×B 格内图片区高度（非原比例时由画框比例推算） */
export const historyBatchCellImageHeight = computed(() => {
  if (historyCardLayout.imageLayout === 'natural') return null
  const w = historyCardLayout.cardWidth
  const parts = String(historyCardLayout.aspectRatio || '4/5')
    .split('/')
    .map(Number)
  if (parts.length === 2 && parts[0] > 0 && parts[1] > 0) {
    return Math.max(72, Math.round((w * parts[1]) / parts[0]))
  }
  return Math.max(72, Math.round((w * 5) / 4))
})

/** 批量 A×B 矩阵：行标题列 + 固定列宽 */
export function historyBatchMatrixGridStyle(colCount) {
  const cols = Math.max(1, Number(colCount) || 1)
  const w = historyCardLayout.cardWidth
  return {
    gridTemplateColumns: `2.5rem repeat(${cols}, ${w}px)`,
    justifyContent: 'start',
  }
}

/** 批量平铺网格（非 A×B 矩阵时） */
export const historyBatchFlatGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, ${historyCardLayout.cardWidth}px)`,
  justifyContent: 'start',
}))

watch(
  () => historyCardLayout.cardWidth,
  (v) => {
    const clamped = Math.min(
      HISTORY_CARD_WIDTH_MAX,
      Math.max(HISTORY_CARD_WIDTH_MIN, Math.round(Number(v) || HISTORY_CARD_WIDTH_DEFAULT)),
    )
    if (clamped !== v) historyCardLayout.cardWidth = clamped
    try {
      localStorage.setItem(WIDTH_KEY, String(clamped))
    } catch {
      /* ignore */
    }
  },
)

watch(
  () => historyCardLayout.imageLayout,
  (v) => {
    try {
      localStorage.setItem(LAYOUT_KEY, v)
    } catch {
      /* ignore */
    }
  },
)

watch(
  () => historyCardLayout.aspectRatio,
  (v) => {
    try {
      localStorage.setItem(ASPECT_KEY, v)
    } catch {
      /* ignore */
    }
  },
)

export function setHistoryCardWidth(n) {
  const v = Math.round(Number(n))
  if (!Number.isFinite(v)) return
  historyCardLayout.cardWidth = Math.min(
    HISTORY_CARD_WIDTH_MAX,
    Math.max(HISTORY_CARD_WIDTH_MIN, v),
  )
}

export function applyHistoryCardWidthPreset(value) {
  setHistoryCardWidth(value)
}

export function useHistoryCardLayout() {
  return {
    layout: historyCardLayout,
    gridStyle: historyCardGridStyle,
    isNatural: historyCardIsNatural,
    thumbBoxStyle: historyCardThumbBoxStyle,
    imgClass: historyCardImgClass,
    setCardWidth: setHistoryCardWidth,
    applyWidthPreset: applyHistoryCardWidthPreset,
    HISTORY_CARD_WIDTH_MIN,
    HISTORY_CARD_WIDTH_MAX,
    HISTORY_CARD_WIDTH_PRESETS,
    HISTORY_IMAGE_LAYOUT_OPTIONS,
    HISTORY_ASPECT_OPTIONS,
  }
}
