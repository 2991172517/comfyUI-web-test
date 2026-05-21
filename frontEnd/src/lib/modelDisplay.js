/** 模型文件名 → 短标题（去路径与扩展名） */
export function modelDisplayTitle(name) {
  const base = String(name || '')
    .split(/[/\\]/)
    .pop()
  return base.replace(/\.(safetensors|pt|ckpt|pth|bin)$/i, '') || base || '—'
}

/** @deprecated 使用 modelDisplayTitle */
export const loraDisplayTitle = modelDisplayTitle

/** 从 catalog 项取首图 URL */
export function catalogThumb(item) {
  if (!item?.previews?.length) return null
  return item.previews[0]?.url || null
}

/** @deprecated 使用 catalogThumb */
export const loraCatalogThumb = catalogThumb
