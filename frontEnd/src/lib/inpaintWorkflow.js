/** 局部重绘工作流 id */
export const INPAINT_WORKFLOW_ID = 'variants/局部重绘_inpaint'

/** 带 RTX 1.5x 超分的变体（需 RTX 插件）；前端 UI 暂隐藏，恢复时改 INPAINT_RTX_UI_ENABLED */
export const INPAINT_WORKFLOW_ID_RTX = 'variants/局部重绘_inpaint_rtx'

export const INPAINT_RTX_UI_ENABLED = false

export const INPAINT_NODES = {
  checkpoint: '1',
  positive: '3',
  negative: '4',
  sourceImage: '10',
  maskImage: '11',
  sampler: '30',
  saveImage: '50',
  rtxUpscale: '60',
}
