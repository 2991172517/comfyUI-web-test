/**
 * 从涂蒙版画布导出 ComfyUI LoadImageMask 用 PNG：白=重绘，黑=保留。
 * @param {HTMLCanvasElement} maskCanvas 与图像同尺寸，涂过处为不透明/白色
 */
export function exportMaskPngBlob(maskCanvas) {
  const w = maskCanvas.width
  const h = maskCanvas.height
  if (!w || !h) {
    return Promise.reject(new Error('蒙版画布尺寸无效'))
  }

  const out = document.createElement('canvas')
  out.width = w
  out.height = h
  const ctx = out.getContext('2d')
  if (!ctx) {
    return Promise.reject(new Error('无法创建导出画布'))
  }

  ctx.fillStyle = '#000000'
  ctx.fillRect(0, 0, w, h)

  const srcCtx = maskCanvas.getContext('2d')
  if (!srcCtx) {
    return Promise.reject(new Error('蒙版画布不可用'))
  }
  const imgData = srcCtx.getImageData(0, 0, w, h)
  const outData = ctx.getImageData(0, 0, w, h)
  const s = imgData.data
  const d = outData.data
  for (let i = 0; i < s.length; i += 4) {
    const painted = s[i + 3] > 8
    const v = painted ? 255 : 0
    d[i] = v
    d[i + 1] = v
    d[i + 2] = v
    d[i + 3] = 255
  }
  ctx.putImageData(outData, 0, 0)

  return new Promise((resolve, reject) => {
    out.toBlob(
      (blob) => {
        if (blob) resolve(blob)
        else reject(new Error('导出蒙版失败'))
      },
      'image/png',
    )
  })
}
