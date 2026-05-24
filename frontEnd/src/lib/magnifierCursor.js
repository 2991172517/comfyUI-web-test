/** 放大镜激活时隐藏系统光标（多实例引用计数） */
let lockCount = 0

export function lockMagnifierCursor() {
  if (typeof document === 'undefined') return () => {}

  lockCount += 1
  if (lockCount === 1) {
    document.documentElement.classList.add('image-magnifier-cursor-hidden')
  }

  let released = false
  return () => {
    if (released) return
    released = true
    lockCount = Math.max(0, lockCount - 1)
    if (lockCount === 0) {
      document.documentElement.classList.remove('image-magnifier-cursor-hidden')
    }
  }
}
