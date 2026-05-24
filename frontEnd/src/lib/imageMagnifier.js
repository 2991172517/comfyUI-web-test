/**
 * object-contain 下图片在容器内的实际显示区域
 * @param {HTMLImageElement} img
 * @param {DOMRect} containerRect
 */
export function getContainedImageRect(img, containerRect) {
  const nw = img.naturalWidth
  const nh = img.naturalHeight
  if (!nw || !nh || !containerRect.width || !containerRect.height) {
    return null
  }
  const scale = Math.min(containerRect.width / nw, containerRect.height / nh)
  const dispW = nw * scale
  const dispH = nh * scale
  const offsetX = (containerRect.width - dispW) / 2
  const offsetY = (containerRect.height - dispH) / 2
  return { offsetX, offsetY, dispW, dispH, scale, nw, nh }
}

/** @param {HTMLImageElement} img */
export function getDisplayedImageViewportRect(img) {
  const box = img.getBoundingClientRect()
  const inner = getContainedImageRect(img, box)
  if (!inner) return null
  return {
    left: box.left + inner.offsetX,
    top: box.top + inner.offsetY,
    width: inner.dispW,
    height: inner.dispH,
    scale: inner.scale,
    naturalWidth: inner.nw,
    naturalHeight: inner.nh,
  }
}

/**
 * 放大镜内图片位移：使 (ix, iy) 落在镜头中心
 * @param {number} ix 相对显示图左上角的 x（CSS 像素）
 * @param {number} iy
 * @param {{ dispW: number, dispH: number }} bounds
 * @param {number} zoom
 * @param {number} lensSize
 */
export function magnifierImageTransform(ix, iy, bounds, zoom, lensSize) {
  const bgW = bounds.dispW * zoom
  const bgH = bounds.dispH * zoom
  let tx = lensSize / 2 - ix * zoom
  let ty = lensSize / 2 - iy * zoom
  if (bgW > lensSize) {
    tx = Math.min(0, Math.max(lensSize - bgW, tx))
  } else {
    tx = (lensSize - bgW) / 2
  }
  if (bgH > lensSize) {
    ty = Math.min(0, Math.max(lensSize - bgH, ty))
  } else {
    ty = (lensSize - bgH) / 2
  }
  return { bgW, bgH, tx, ty }
}

/**
 * 圆形放大镜：圆心跟随鼠标（视口坐标）
 */
export function magnifierLensViewportPosition(clientX, clientY, diameter) {
  const half = diameter / 2
  return { left: clientX - half, top: clientY - half }
}
