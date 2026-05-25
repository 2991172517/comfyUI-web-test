import { inject, onUnmounted, provide, reactive, ref } from 'vue'
import { api, statusLabel } from '@/api/client.js'
import { applyQuotaFromApi, hasSingleQuotaLeft } from '@/composables/useAuth.js'
import {
  UPSCALE_DEFAULT_SCALE,
  UPSCALE_NODES,
  UPSCALE_WORKFLOW_ID,
} from '@/lib/upscaleWorkflow.js'

const UPSCALE_STORE = Symbol('upscaleStore')

export function createUpscaleStore() {
  const loading = ref(false)
  const message = ref('')
  const error = ref('')
  const scale = ref(UPSCALE_DEFAULT_SCALE)
  const quality = ref('ULTRA')

  const compareBeforeUrl = ref('')
  const compareAfterUrl = ref('')
  const showCompare = ref(false)

  const job = reactive({
    promptId: '',
    clientId: '',
    status: 'idle',
    statusText: '',
    message: '',
    images: [],
  })

  let pollTimer = null
  let beforeUrlOwned = ''

  const progressPercent = ref(null)

  function setCompareBefore(url) {
    if (beforeUrlOwned && beforeUrlOwned !== url) {
      URL.revokeObjectURL(beforeUrlOwned)
    }
    beforeUrlOwned = url?.startsWith('blob:') ? url : ''
    compareBeforeUrl.value = url || ''
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
      message: '',
      images: [],
    })
    compareAfterUrl.value = ''
  }

  function isGenerating() {
    return ['pending', 'in_progress', 'finalizing'].includes(job.status)
  }

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
        setMessage(job.message || '已取消')
        return
      }
      if (detail.status === 'failed') {
        stopPoll()
        setMessage(job.message || '放大失败', true)
        return
      }
      if (detail.status === 'completed') {
        stopPoll()
        setMessage(job.images.length ? '高清放大完成' : job.message || '未找到输出', !job.images.length)
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
      setMessage('已取消')
    } catch (e) {
      setMessage(e.message, true)
    }
  }

  async function submitUpscale(file, opts = {}) {
    if (!hasSingleQuotaLeft()) {
      setMessage('本次登录单图额度已用尽', true)
      return
    }
    if (!file) {
      setMessage('请先选择图片', true)
      return
    }
    if (isGenerating()) return

    const s = Number(scale.value)
    if (!Number.isFinite(s) || s < 1.05 || s > 4) {
      setMessage('放大倍数建议在 1.05～4 之间', true)
      return
    }

    loading.value = true
    resetJob()
    stopPoll()
    showCompare.value = false
    setCompareBefore(URL.createObjectURL(file))

    try {
      const up = await api.uploadComfyImage(file, { overwrite: true })
      const overrides = {
        [UPSCALE_NODES.sourceImage]: { image: up.name },
        [UPSCALE_NODES.rtx]: {
          'resize_type.scale': s,
          quality: quality.value,
        },
      }

      const workflowId = opts.workflowId || UPSCALE_WORKFLOW_ID
      const res = await api.queueWorkflow(workflowId, overrides)
      Object.assign(job, {
        promptId: res.prompt_id,
        clientId: res.client_id,
        status: 'pending',
        statusText: statusLabel('pending'),
        message: '已提交高清放大…',
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

  return reactive({
    workflowId: UPSCALE_WORKFLOW_ID,
    loading,
    message,
    error,
    scale,
    quality,
    compareBeforeUrl,
    compareAfterUrl,
    showCompare,
    job,
    progressPercent,
    get isGenerating() {
      return isGenerating()
    },
    setMessage,
    submitUpscale,
    cancelJob,
  })
}

export function provideUpscaleStore() {
  const store = createUpscaleStore()
  provide(UPSCALE_STORE, store)
  return store
}

export function useUpscaleStore() {
  const store = inject(UPSCALE_STORE)
  if (!store) throw new Error('useUpscaleStore 需在 UpscaleView 内使用')
  return store
}
