import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/useAppStore.js'
import {
  extractInpaintSettings,
  persistInpaintBootstrap,
} from '@/lib/inpaintBootstrap.js'

export function useNavigateToInpaint() {
  const router = useRouter()
  const app = useAppStore()

  function goInpaint(rawPayload) {
    if (!rawPayload?.image?.url) {
      app.setMessage('缺少图片，无法打开局部重绘', true)
      return false
    }
    const settings = extractInpaintSettings(rawPayload)
    const payload = {
      ...rawPayload,
      settings,
    }
    const key = persistInpaintBootstrap(payload)
    if (!key) {
      app.setMessage('无法缓存跳转参数，请重试', true)
      return false
    }
    router.push({ path: '/inpaint', query: { bootstrap: key } })
    return true
  }

  return { goInpaint }
}
