import { nextTick } from 'vue'
import { peekInpaintBootstrap, consumeInpaintBootstrap } from '@/lib/inpaintBootstrap.js'

/**
 * 等待 MaskPaintEditor 挂载并暴露 loadImageFromUrl。
 * @param {import('vue').Ref} editorRef
 */
export async function waitForMaskEditor(editorRef, { maxWaitMs = 4000 } = {}) {
  const deadline = Date.now() + maxWaitMs
  while (Date.now() < deadline) {
    await nextTick()
    const ed = editorRef.value
    if (ed?.loadImageFromUrl) return ed
    await new Promise((r) => setTimeout(r, 40))
  }
  return null
}

/**
 * 从 bootstrap query 载入原图与提示词参数。
 * @returns {Promise<boolean>}
 */
export async function applyInpaintBootstrapFromQuery(
  bootstrapKey,
  { editorRef, inpaint, router, route },
) {
  if (!bootstrapKey || typeof bootstrapKey !== 'string') return false

  const payload = peekInpaintBootstrap(bootstrapKey)
  if (!payload) {
    inpaint.setMessage('跳转参数已失效，请从历史/收藏重新打开', true)
    return false
  }

  if (payload.settings) inpaint.applyBootstrapSettings(payload.settings)

  if (!payload.image?.url) {
    inpaint.setMessage('跳转数据缺少图片地址', true)
    return false
  }

  const editor = await waitForMaskEditor(editorRef)
  if (!editor) {
    inpaint.setMessage('编辑器未就绪，请稍后重试或手动上传原图', true)
    return false
  }

  try {
    await editor.loadImageFromUrl(
      payload.image.url,
      payload.image.filename || 'inpaint_source.png',
    )
    consumeInpaintBootstrap(bootstrapKey)

    const src =
      payload.source_workflow_id || payload.settings?.source_workflow_id
    if (src) {
      inpaint.setMessage(`已载入图片，Checkpoint/提示词来自工作流「${src}」`)
    } else {
      inpaint.setMessage('已载入图片与提示词参数')
    }

    if (route.query.bootstrap) {
      router.replace({ path: '/inpaint' })
    }
    return true
  } catch (e) {
    inpaint.setMessage(`图片加载失败：${e.message}`, true)
    return false
  }
}
