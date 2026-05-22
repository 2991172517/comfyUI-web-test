import { useAppStore } from '@/stores/useAppStore.js'
import { api } from '@/api/client.js'
import {
  downloadImageFile,
  downloadImagesSequential,
  resolveDownloadFilename,
} from '@/lib/downloadImage.js'

/** 带 Toast 提示的图片保存 */
export function useImageDownload() {
  const app = useAppStore()

  async function saveOne(imgOrUrl, fallbackName) {
    try {
      const payload =
        typeof imgOrUrl === 'string'
          ? { url: imgOrUrl, filename: resolveDownloadFilename(imgOrUrl, fallbackName) }
          : imgOrUrl
      const name = await downloadImageFile(payload)
      app.setMessage(`已保存: ${name}`)
      return name
    } catch (e) {
      app.setMessage(e.message || '下载失败', true)
      throw e
    }
  }

  async function saveAll(images, fallbackPrefix = 'image') {
    const list = (images || [])
      .filter((i) => i?.url)
      .map((i, idx) => ({
        url: i.url,
        filename: i.filename || resolveDownloadFilename(i, `${fallbackPrefix}_${idx + 1}.png`),
      }))
    if (!list.length) {
      app.setMessage('没有可保存的图片', true)
      return []
    }
    try {
      const saved = await downloadImagesSequential(list, { delayMs: 300 })
      app.setMessage(
        saved.length === 1 ? `已保存: ${saved[0]}` : `已保存 ${saved.length} 张图片`,
      )
      return saved
    } catch (e) {
      app.setMessage(e.message || '下载失败', true)
      throw e
    }
  }

  async function saveWithDelay(images) {
    const list = (images || []).filter((i) => i?.url)
    for (let i = 0; i < list.length; i++) {
      await saveOne(list[i])
      if (i < list.length - 1) await api.sleep(300)
    }
  }

  return { saveOne, saveAll, saveWithDelay, resolveDownloadFilename }
}
