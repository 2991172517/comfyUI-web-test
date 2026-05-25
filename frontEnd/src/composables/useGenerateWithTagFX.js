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
  collectEnabledRandomGroups,
  fetchRandomGachaPlan,
  loadGlobalPromptConfigForPlan,
  waitForJobQueued,
  waitUntilJobRunning,
} from '@/lib/randomGachaReels.js'
import { scrollToGenerateStatus } from '@/lib/scrollToGenerateStatus.js'
import { useVocabularyRandomMode } from '@/composables/useVocabularyRandomMode.js'
import { useGachaAnimation } from '@/composables/useGachaAnimation.js'
import { useSessionBundleGroups } from '@/composables/useSessionBundleGroups.js'

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error(`${label} 超时（${Math.round(ms / 1000)}s）`)), ms)
    }),
  ])
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
  const { enabled: vocabRandomEnabled, rollForApp } = useVocabularyRandomMode()
  const { effectiveEnabled: gachaAnimationEnabled } = useGachaAnimation()
  const { masterEnabled: bundleGroupsEnabled } = useSessionBundleGroups()
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
      if (vocabRandomEnabled.value) {
        await showStage('抽取词库随机词…', 400)
        const vocabResult = await rollForApp(app)
        if (vocabResult.message) {
          appendGenerateStageLog(vocabResult.message)
          if (!vocabResult.applied && vocabResult.message.includes('失败')) {
            app.setMessage(vocabResult.message, true)
          }
        }
      }

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
      {
        const n = collectEnabledRandomGroups(globalConfig, app.sessionPrompts).length
        appendGenerateStageLog(
          n ? `当次提示词已就绪（${n} 个随机组待抽取）` : '当次提示词已就绪（无随机组）',
        )
      }

      const randomGroups = collectEnabledRandomGroups(globalConfig, app.sessionPrompts)
      const hasRandomWork = randomGroups.length > 0 || bundleGroupsEnabled.value
      if (!hasRandomWork) {
        appendGenerateStageLog('无随机组/词串组，跳过抽卡')
        await sleep(300)
      } else if (!gachaAnimationEnabled.value) {
        appendGenerateStageLog('抽卡动画已关闭，跳过动画')
        await sleep(200)
      } else {
        appendGenerateStageLog('抽取随机提示词…')
        stageMessage.value = '抽取随机提示词…'
        let rows = null
        try {
          rows = await fetchRandomGachaPlan(app, {
            globalConfig,
            bundleMasterEnabled: bundleGroupsEnabled.value,
          })
        } catch (err) {
          const msg = err?.message || String(err)
          appendGenerateStageLog(`随机词预览失败：${msg}（将继续提交生成）`)
          app.setMessage(`随机词预览失败，已跳过抽卡动画：${msg}`, true)
        }

        if (rows?.length) {
          appendGenerateStageLog(`共 ${rows.length} 项随机抽取，开始抽卡…`)
          try {
            const gachaOverlay = getRandomGachaOverlay()
            await withTimeout(
              gachaOverlay.playWithRows(rows, { targetEl: el }),
              12_000,
              '抽卡动画',
            )
            appendGenerateStageLog('随机参数已确定')
          } catch (err) {
            const msg = err?.message || String(err)
            appendGenerateStageLog(`抽卡动画跳过：${msg}（将继续提交生成）`)
          }
        } else if (hasRandomWork) {
          appendGenerateStageLog('随机组已启用但未抽到词条，跳过抽卡动画')
        }
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
