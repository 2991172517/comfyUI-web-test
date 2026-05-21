const VIDEO_EXT = /\.(mp4|webm|mov|m4v)(\?|$)/i

/** 统一 parse/version 返回的预览字段（string | { url, mediaType }） */
export function normalizePreviewMedia(raw) {
  if (!raw) return { url: '', mediaType: 'image', isVideo: false }
  if (typeof raw === 'string') {
    const isVideo = VIDEO_EXT.test(raw)
    return { url: raw, mediaType: isVideo ? 'video' : 'image', isVideo }
  }
  const url = raw.url || ''
  const isVideo =
    raw.isVideo === true ||
    raw.mediaType === 'video' ||
    VIDEO_EXT.test(url)
  return {
    url,
    width: raw.width,
    height: raw.height,
    mediaType: isVideo ? 'video' : 'image',
    isVideo,
  }
}

/** 收集可导入的静态参考图 URL */
export function collectStaticPreviewUrls(versionDetail, parseResult) {
  const urls = []
  const add = (u) => {
    if (!u || urls.includes(u) || VIDEO_EXT.test(u)) return
    urls.push(u)
  }
  for (const u of versionDetail?.staticPreviewUrls || []) add(u)
  for (const img of versionDetail?.images || []) {
    if (img?.mediaType === 'video') continue
    add(img?.url)
  }
  const prev = normalizePreviewMedia(versionDetail?.previewImage)
  if (!prev.isVideo) add(prev.url)
  const modelPrev = normalizePreviewMedia(parseResult?.model?.previewMedia)
  if (!modelPrev.isVideo) add(modelPrev.url)
  const legacy = parseResult?.model?.previewImage
  if (typeof legacy === 'string' && !VIDEO_EXT.test(legacy)) add(legacy)
  return urls.slice(0, 3)
}
