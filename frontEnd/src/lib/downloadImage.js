/** 浏览器下载 ComfyUI 输出图到本机 */

export function resolveDownloadFilename(imgOrUrl, fallback = 'image.png') {
  if (imgOrUrl && typeof imgOrUrl === 'object') {
    const name = (imgOrUrl.filename || imgOrUrl.name || '').trim()
    if (name) return name
    return resolveDownloadFilename(imgOrUrl.url, fallback)
  }
  const url = typeof imgOrUrl === 'string' ? imgOrUrl : ''
  if (!url) return fallback
  try {
    const path = new URL(url, window.location.origin).pathname
    const base = path.split('/').filter(Boolean).pop()
    if (base && base.includes('.')) return decodeURIComponent(base)
  } catch {
    /* ignore */
  }
  return fallback
}

/**
 * @param {{ url: string, filename?: string }} img
 * @returns {Promise<string>} 实际使用的文件名
 */
export async function downloadImageFile(img) {
  const url = (img?.url || '').trim()
  if (!url) throw new Error('缺少图片地址')
  const filename = resolveDownloadFilename(img)
  const res = await fetch(url)
  if (!res.ok) throw new Error('下载失败')
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(a.href)
  return filename
}

/**
 * @param {Array<{ url?: string, filename?: string }>} images
 * @param {{ delayMs?: number }} [opts]
 */
export async function downloadImagesSequential(images, opts = {}) {
  const delayMs = opts.delayMs ?? 300
  const list = (images || []).filter((i) => i?.url)
  const saved = []
  for (let i = 0; i < list.length; i++) {
    const name = await downloadImageFile(list[i])
    saved.push(name)
    if (delayMs > 0 && i < list.length - 1) {
      await new Promise((r) => setTimeout(r, delayMs))
    }
  }
  return saved
}
