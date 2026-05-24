import { ref } from 'vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { useGenerateRunMode } from '@/composables/useGenerateRunMode.js'
import { getRandomGachaOverlay } from '@/composables/useRandomGachaOverlay.js'
import {
  appendGenerateStageLog,
  beginGeneratePrep,
  endGeneratePrep,
  useGenerateStageLog,
} from '@/composables/useGenerateStageLog.js'
import {
  fetchRandomGachaPlan,
  loadGlobalPromptConfigForPlan,
  waitForJobQueued,
  waitUntilJobRunning,
} from '@/lib/randomGachaReels.js'
import { scrollToGenerateStatus } from '@/lib/scrollToGenerateStatus.js'

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

/** 每步至少展示时长，便于在状态栏与按钮上阅读 */
async function showStage(text, minMs = 900) {
  appendGenerateStageLog(text)
  await sleep(minMs)
}

/**
 * @param {{ getTargetEl?: () => HTMLElement | null }} opts
 */
export function useGenerateWithTagFX(opts = {}) {
  const app = useAppStore()
  const batch = useBatchStore()
  const { usesBatchApi } = useGenerateRunMode()
  const animating = ref(false)
  const { stageMessage } = useGenerateStageLog()

  async function runGenerate() {
    if (usesBatchApi.value) {
      await batch.startBatch()
    } else {
      await app.queueWorkflow()
    }
  }

  /**
   * 先加载提示词并抽卡，再提交 ComfyUI 任务。
   * @param {HTMLElement | null} [targetEl]
   */
  async function generateWithFX(targetEl) {
    if (animating.value) return false

    const el = targetEl ?? opts.getTargetEl?.() ?? null
    const multi = usesBatchApi.value

    animating.value = true
    beginGeneratePrep()
    scrollToGenerateStatus({ sweep: multi })

    try {
      if (multi) {
        await showStage('加载当次提示词…')
        await runGenerate()
        appendGenerateStageLog('生成任务已启动')
        return true
      }

      await showStage('加载全局提示词…')
      const globalConfig = await loadGlobalPromptConfigForPlan()
      appendGenerateStageLog(
        globalConfig ? '全局提示词配置已就绪' : '未读取到全局配置，使用当次设置',
      )

      await showStage('加载当次提示词…')
      appendGenerateStageLog('当次提示词与会话随机组已加载')

      appendGenerateStageLog('抽取随机提示词…')
      stageMessage.value = '抽取随机提示词…'
      const rows = await fetchRandomGachaPlan(app, { globalConfig })
      const gachaOverlay = getRandomGachaOverlay()

      if (rows?.length) {
        appendGenerateStageLog(`共 ${rows.length} 个随机组，开始抽卡…`)
        await gachaOverlay.playWithRows(rows, { targetEl: el })
        appendGenerateStageLog('随机参数已确定')
      } else {
        appendGenerateStageLog('无随机组，跳过抽卡')
        await sleep(500)
      }

      await showStage('提交生成任务…')
      await runGenerate()

      const queued = await waitForJobQueued(app)
      if (queued) appendGenerateStageLog('任务已提交，等待 ComfyUI 执行…')

      const running = await waitUntilJobRunning(app)
      if (running) appendGenerateStageLog('工作流已开始执行')

      return true
    } finally {
      animating.value = false
      endGeneratePrep()
      stageMessage.value = ''
    }
  }

  return { animating, stageMessage, generateWithFX, runGenerate }
}
