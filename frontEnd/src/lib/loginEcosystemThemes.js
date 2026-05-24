/** 登录页萤火生态背景：4 种视觉模式 + 扩展配色预设 */

export const ECOSYSTEM_MODES = [
  {
    id: 0,
    label: '01',
    name: '萤火',
    bodyClass: '',
    particleType: 'spore',
    tendrilStyle: 'thin',
    drawDome: false,
    wind: 0,
    fadeRgb: '5, 5, 5',
    colors: ['rgba(0, 255, 204, ', 'rgba(0, 153, 255, ', 'rgba(0, 200, 150, '],
    accent: '#00ffcc',
    accentRgb: '0, 255, 204',
    textSecondary: '#8e8e93',
  },
  {
    id: 1,
    label: '02',
    name: '紫境',
    bodyClass: 'theme-1',
    particleType: 'spore',
    tendrilStyle: 'thin',
    drawDome: true,
    wind: 0,
    fadeRgb: '5, 5, 5',
    colors: ['rgba(204, 102, 255, ', 'rgba(255, 102, 153, ', 'rgba(153, 51, 255, '],
    accent: '#cc66ff',
    accentRgb: '204, 102, 255',
    textSecondary: '#8e8e93',
  },
  {
    id: 2,
    label: '03',
    name: '矩阵',
    bodyClass: 'theme-2',
    particleType: 'sparks',
    tendrilStyle: 'straight',
    drawDome: false,
    wind: 150,
    fadeRgb: '0, 10, 0',
    colors: ['rgba(0, 255, 102, ', 'rgba(50, 255, 150, ', 'rgba(0, 200, 80, '],
    accent: '#00ff66',
    accentRgb: '0, 255, 102',
    textSecondary: '#00cc55',
    matrixUi: true,
  },
  {
    id: 3,
    label: '04',
    name: '深海',
    bodyClass: 'theme-3',
    particleType: 'bubble',
    tendrilStyle: 'thick',
    drawDome: false,
    wind: 0,
    fadeRgb: '2, 10, 25',
    colors: ['rgba(0, 153, 255, ', 'rgba(51, 204, 255, ', 'rgba(0, 102, 204, '],
    accent: '#0099ff',
    accentRgb: '0, 153, 255',
    textSecondary: '#8e8e93',
    waterRipples: true,
  },
]

/** 额外配色（随机池）；不改变粒子/藤蔓形态，只换色 */
export const COLOR_PRESETS = [
  {
    name: '琥珀',
    colors: ['rgba(255, 180, 60, ', 'rgba(255, 140, 40, ', 'rgba(255, 210, 120, '],
    accent: '#ffb43c',
    accentRgb: '255, 180, 60',
  },
  {
    name: '玫红',
    colors: ['rgba(255, 80, 140, ', 'rgba(255, 120, 180, ', 'rgba(220, 60, 120, '],
    accent: '#ff508c',
    accentRgb: '255, 80, 140',
  },
  {
    name: '霜白',
    colors: ['rgba(200, 220, 255, ', 'rgba(160, 190, 240, ', 'rgba(230, 240, 255, '],
    accent: '#c8dcff',
    accentRgb: '200, 220, 255',
  },
  {
    name: '熔岩',
    colors: ['rgba(255, 90, 40, ', 'rgba(255, 50, 80, ', 'rgba(255, 160, 60, '],
    accent: '#ff5a28',
    accentRgb: '255, 90, 40',
  },
  {
    name: '极光',
    colors: ['rgba(80, 255, 200, ', 'rgba(120, 80, 255, ', 'rgba(40, 200, 255, '],
    accent: '#50ffc8',
    accentRgb: '80, 255, 200',
  },
  {
    name: '金杏',
    colors: ['rgba(255, 215, 100, ', 'rgba(255, 180, 80, ', 'rgba(255, 240, 160, '],
    accent: '#ffd764',
    accentRgb: '255, 215, 100',
  },
  {
    name: '薄荷',
    colors: ['rgba(100, 255, 200, ', 'rgba(60, 220, 180, ', 'rgba(150, 255, 220, '],
    accent: '#64ffc8',
    accentRgb: '100, 255, 200',
  },
  {
    name: '霓虹',
    colors: ['rgba(255, 0, 255, ', 'rgba(0, 255, 255, ', 'rgba(255, 255, 0, '],
    accent: '#ff00ff',
    accentRgb: '255, 0, 255',
  },
]

function hslToRgb(h, s, l) {
  s /= 100
  l /= 100
  const k = (n) => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))
  return [
    Math.round(255 * f(0)),
    Math.round(255 * f(8)),
    Math.round(255 * f(4)),
  ]
}

/** 生成完全随机的配色 */
export function generateRandomPalette() {
  const h1 = Math.floor(Math.random() * 360)
  const h2 = (h1 + 35 + Math.floor(Math.random() * 90)) % 360
  const h3 = (h1 + 140 + Math.floor(Math.random() * 80)) % 360
  const mk = (h, l = 58) => {
    const [r, g, b] = hslToRgb(h, 88 + Math.random() * 12, l)
    return `rgba(${r}, ${g}, ${b}, `
  }
  const [ar, ag, ab] = hslToRgb(h1, 90, 62)
  return {
    name: '随机',
    colors: [mk(h1), mk(h2, 52), mk(h3, 48)],
    accent: `rgb(${ar}, ${ag}, ${ab})`,
    accentRgb: `${ar}, ${ag}, ${ab}`,
  }
}

export function pickRandomPalette() {
  if (Math.random() < 0.45) {
    return COLOR_PRESETS[Math.floor(Math.random() * COLOR_PRESETS.length)]
  }
  return generateRandomPalette()
}

/** 将配色覆盖合并到模式（保留形态参数） */
export function applyPaletteToMode(mode, palette) {
  if (!palette) return { ...mode }
  return {
    ...mode,
    colors: palette.colors?.length ? [...palette.colors] : mode.colors,
    accent: palette.accent ?? mode.accent,
    accentRgb: palette.accentRgb ?? mode.accentRgb,
    paletteName: palette.name,
  }
}

export const LOGIN_BG_MODE_KEY = 'login-ecosystem-mode'
export const LOGIN_BG_PALETTE_KEY = 'login-ecosystem-palette'

export function loadSavedModeId() {
  try {
    const v = Number(localStorage.getItem(LOGIN_BG_MODE_KEY))
    if (Number.isFinite(v) && v >= 0 && v < ECOSYSTEM_MODES.length) return v
  } catch {
    /* ignore */
  }
  return 0
}

export function saveModeId(id) {
  try {
    localStorage.setItem(LOGIN_BG_MODE_KEY, String(id))
  } catch {
    /* ignore */
  }
}

export function loadSavedPalette() {
  try {
    const raw = localStorage.getItem(LOGIN_BG_PALETTE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!data?.colors?.length) return null
    return data
  } catch {
    return null
  }
}

export function savePalette(palette) {
  try {
    if (!palette) {
      localStorage.removeItem(LOGIN_BG_PALETTE_KEY)
      return
    }
    localStorage.setItem(
      LOGIN_BG_PALETTE_KEY,
      JSON.stringify({
        name: palette.name,
        colors: palette.colors,
        accent: palette.accent,
        accentRgb: palette.accentRgb,
      }),
    )
  } catch {
    /* ignore */
  }
}
