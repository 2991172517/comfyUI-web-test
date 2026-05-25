import { inject, onUnmounted, provide, reactive, ref } from 'vue'
import { api, statusLabel } from '@/api/client.js'
import { applyQuotaFromApi, hasSingleQuotaLeft } from '@/composables/useAuth.js'
import { exportMaskPngBlob } from '@/lib/exportMaskPng.js'
import {
  INPAINT_NODES,
  INPAINT_RTX_UI_ENABLED,
  INPAINT_WORKFLOW_ID,
  INPAINT_WORKFLOW_ID_RTX,
} from '@/lib/inpaintWorkflow.js'

const INPAINT_STORE = Symbol('inpaintStore')

export function createInpaintStore() {
  const loading = ref(false)
  const message = ref('')
  const error = ref('')

  const checkpoint = ref('')
  const positive = ref('masterpiece, best quality, detailed')
  const negative = ref(
    'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry',
  )
  const bootstrapSourceWorkflowId = ref('')
  const seed = ref(Math.floor(Math.random() * 2 ** 31))
  const denoise = ref(0.55)
  const steps = ref(28)
  const cfg = ref(6)
  /** 完成后 RTX 1.5x 放大（需 RTX 插件，默认关以保持轻量） */
  const rtxUpscale = ref(false)

  const compareBeforeUrl = ref('')
  const compareAfterUrl = ref('')

  const job = reactive({
    promptId: '',
    clientId: '',
    status: 'idle',
    statusText: '',
    currentNode: null,
    progress: null,
    message: '',
    images: [],
  })

  let pollTimer = null
  let beforeUrlOwned = ''

  function setCompareBefore(url) {
    if (beforeUrlOwned && beforeUrlOwned !== url) {
      URL.revokeObjectURL(beforeUrlOwned)
    }
    beforeUrlOwned = url?.startsWith('blob:') ? url : ''
    compareBeforeUrl.value = url || ''
  }

  function clearCompare() {
    setCompareBefore('')
    compareAfterUrl.value = ''
  }

  function setMessage(text, isError = false) {
    message.value = text
    error.value = isError ? text : ''
  }

  function resetJob() {
    Object.assign(job, {
      promptId: '',
      clientId: '',
      status: 'idle',
      statusText: '',
      currentNode: null,
      progress: null,
      message: '',
      images: [],
    })
    compareAfterUrl.value = ''
  }

  function isGenerating() {
    return ['pending', 'in_progress', 'finalizing'].includes(job.status)
  }

  const progressPercent = ref(null)

  const showCompare = ref(false)

  function stopPoll() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    progressPercent.value = null
  }

  function applyJobDetail(detail) {
    job.status = detail.status || 'unknown'
    job.statusText = statusLabel(job.status)
    job.message = detail.message || ''
    job.currentNode = detail.current_node ?? null
    job.progress = detail.progress ?? null
    job.images = detail.images || []
    if (detail.progress?.max) {
      progressPercent.value = Math.round(
        (100 * (detail.progress.value || 0)) / detail.progress.max,
      )
    }
    if (detail.status === 'completed' && job.images[0]?.url) {
      compareAfterUrl.value = job.images[0].url
      showCompare.value = true
    }
  }

  async function pollJobOnce(promptId) {
    try {
      const detail = await api.getJob(promptId)
      applyJobDetail(detail)
      if (detail.status === 'cancelled') {
        stopPoll()
        setMessage(job.message || '已取消生成')
        return
      }
      if (detail.status === 'failed') {
        stopPoll()
        setMessage(job.message || '生成失败', true)
        return
      }
      if (detail.status === 'completed') {
        stopPoll()
        setMessage(
          job.images.length
            ? `生成完成，共 ${job.images.length} 张`
            : job.message || '未找到输出',
          !job.images.length,
        )
      }
    } catch {
      /* retry */
    }
  }

  function startJobPolling(promptId) {
    stopPoll()
    pollJobOnce(promptId)
    pollTimer = setInterval(() => pollJobOnce(promptId), 1000)
  }

  async function cancelJob() {
    if (!job.promptId || !isGenerating()) return
    try {
      await api.cancelJob(job.promptId)
      stopPoll()
      job.status = 'cancelled'
      job.statusText = statusLabel('cancelled')
      job.message = '已取消生成'
      setMessage('已取消当前任务')
    } catch (e) {
      setMessage(e.message, true)
    }
  }

  async function submitInpaint(editorRef, opts = {}) {
    if (!hasSingleQuotaLeft()) {
      setMessage('本次登录单图额度已用尽', true)
      return
    }
    if (isGenerating()) return

    const sourceFile = editorRef?.getSourceFile?.()
    const maskCanvas = editorRef?.getMaskCanvas?.()
    const previewUrl = editorRef?.getSourcePreviewUrl?.()
    if (!sourceFile) {
      setMessage('请先上传原图', true)
      return
    }
    if (!editorRef?.hasMask?.()) {
      setMessage('请用画笔涂抹要重绘的区域', true)
      return
    }

    loading.value = true
    resetJob()
    stopPoll()
    showCompare.value = false
    if (previewUrl) setCompareBefore(previewUrl)

    try {
      const maskBlob = await exportMaskPngBlob(maskCanvas)
      const maskFile = new File([maskBlob], `mask_${Date.now()}.png`, { type: 'image/png' })

      const [srcUp, maskUp] = await Promise.all([
        api.uploadComfyImage(sourceFile, { overwrite: true }),
        api.uploadComfyImage(maskFile, { overwrite: true }),
      ])

      const overrides = {
        [INPAINT_NODES.sourceImage]: { image: srcUp.name },
        [INPAINT_NODES.maskImage]: { image: maskUp.name, channel: 'red' },
        [INPAINT_NODES.positive]: { text: positive.value.trim() },
        [INPAINT_NODES.negative]: { text: negative.value.trim() },
        [INPAINT_NODES.sampler]: {
          seed: Number(seed.value) || 0,
          denoise: Number(denoise.value),
          steps: Number(steps.value),
          cfg: Number(cfg.value),
        },
      }
      const ckpt = String(checkpoint.value || '').trim()
      if (ckpt) {
        overrides[INPAINT_NODES.checkpoint] = { ckpt_name: ckpt }
      }

      const useRtx = INPAINT_RTX_UI_ENABLED && rtxUpscale.value
      const workflowId =
        opts.workflowId ||
        (useRtx ? INPAINT_WORKFLOW_ID_RTX : INPAINT_WORKFLOW_ID)

      const res = await api.queueWorkflow(workflowId, overrides)
      Object.assign(job, {
        promptId: res.prompt_id,
        clientId: res.client_id,
        status: 'pending',
        statusText: statusLabel('pending'),
        message: useRtx ? '已提交（含 RTX 1.5× 放大）…' : '已提交局部重绘任务…',
      })
      applyQuotaFromApi(res)
      setMessage(`已提交，任务 ID: ${job.promptId}`)
      startJobPolling(job.promptId)
    } catch (e) {
      setMessage(e.message, true)
      job.status = 'failed'
      job.statusText = statusLabel('failed')
    } finally {
      loading.value = false
    }
  }

  onUnmounted(() => {
    stopPoll()
    if (beforeUrlOwned) URL.revokeObjectURL(beforeUrlOwned)
  })

  function applyBootstrapSettings(settings) {
    if (!settings) return
    if (settings.checkpoint) checkpoint.value = settings.checkpoint
    if (settings.positive) positive.value = settings.positive
    if (settings.negative) negative.value = settings.negative
    if (settings.seed != null && Number.isFinite(Number(settings.seed))) {
      seed.value = Number(settings.seed)
    }
    if (settings.steps != null && Number.isFinite(Number(settings.steps))) {
      steps.value = Number(settings.steps)
    }
    if (settings.cfg != null && Number.isFinite(Number(settings.cfg))) {
      cfg.value = Number(settings.cfg)
    }
    if (settings.denoise != null && Number.isFinite(Number(settings.denoise))) {
      denoise.value = Number(settings.denoise)
    }
    bootstrapSourceWorkflowId.value = settings.source_workflow_id || ''
  }

  const store = reactive({
    workflowId: INPAINT_WORKFLOW_ID,
    loading,
    message,
    error,
    checkpoint,
    bootstrapSourceWorkflowId,
    positive,
    negative,
    seed,
    denoise,
    steps,
    cfg,
    rtxUpscale,
    compareBeforeUrl,
    compareAfterUrl,
    showCompare,
    job,
    progressPercent,
    get isGenerating() {
      return isGenerating()
    },
    setMessage,
    submitInpaint,
    cancelJob,
    clearCompare,
    randomizeSeed() {
      seed.value = Math.floor(Math.random() * 2 ** 31)
    },
    applyBootstrapSettings,
  })

  return store
}

export function provideInpaintStore() {
  const store = createInpaintStore()
  provide(INPAINT_STORE, store)
  return store
}

export function useInpaintStore() {
  const store = inject(INPAINT_STORE)
  if (!store) {
    throw new Error('useInpaintStore 需在 InpaintView 内使用')
  }
  return store
}
