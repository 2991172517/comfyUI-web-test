/**
 * 子工作流「流水线说明」——在工作流配置页展示，便于理解节点顺序与用途。
 * key 为 workflow id（与列表 API 一致）。
 */

/** @typedef {{ label: string, text: string }} PipelineStep */
/** @typedef {{ title: string, steps: PipelineStep[], notes?: string[], link?: { to: string, label: string } }} PipelineGuide */

/** @type {Record<string, PipelineGuide>} */
export const WORKFLOW_PIPELINE_GUIDES = {
  'variants/究极参考流': {
    title: '究极参考流 · 出图流水线',
    steps: [
      {
        label: '① 文生图（一采）',
        text: '从空画面开始：WeiLin 分栏提示词 + LoRA，约 832×1331，30 步采样，得到第一张完整图。',
      },
      {
        label: '② RTX 放大 1.5×',
        text: '用 NVIDIA RTX 超分节点把一采图放大到约 1.5 倍（高清放大，仍是「整张图」）。为后面分块二采提供更清晰的底图。',
      },
      {
        label: '③ TTP 分块二采',
        text: '把放大后的图切成 2×2 块（带重叠），每块做 img2img（denoise≈0.35）再拼回。目的是整图细化、省显存——不是手动画蒙版的局部重绘。',
      },
      {
        label: '④ FaceDetailer 修脸',
        text: '自动检测人脸，只对人脸区域再采样（denoise≈0.3），贴回原图。放在二采之后：先整图细化，再专门修容易糊的脸。',
      },
      {
        label: '⑤ RTX 竖图超分',
        text: '再次用 RTX 超分到约 1600×2560，作为最终交付分辨率。这是第二次「放大」，和步骤②目的不同（②为中间清晰度，⑤为最终尺寸）。',
      },
      {
        label: '⑥ 清理显存并保存',
        text: 'RAM/VRAM 清理后 SaveImage；可用对比节点看放大前后差异。',
      },
    ],
    notes: [
      '「超分」= 超分辨率 / 高清放大：本流用 RTX Video Super Resolution，需 RTX 显卡与对应插件。',
      '本流不含手动画蒙版 Inpaint；若只改衣服/背景等指定区域，请用导航「局部重绘」页。',
      'TTP 是整图分块再画，FaceDetailer 是自动只修脸，二者都不是你在网页上涂蒙版那种局部重绘。',
    ],
  },
  'variants/局部重绘_inpaint': {
    title: '局部重绘 · 蒙版 Inpaint',
    steps: [
      {
        label: '① 输入',
        text: '原图 + 蒙版（白=要改，黑=保留）。不在此工作流里文生图。',
      },
      {
        label: '② 条件与采样',
        text: 'InpaintModelConditioning 把蒙版区与提示词结合，KSampler 在蒙版内去噪（denoise 可调，典型 0.45–0.55）。',
      },
      {
        label: '③ 输出',
        text: 'VAE 解码后保存。逻辑与图生图类似，只是改动范围由蒙版限制。',
      },
    ],
    notes: [
      '运行入口在顶部导航「局部重绘」，不在「生成」页；此处工作流配置页仅可改 Checkpoint / 提示词 encode 等（若已映射）。',
      '不要与究极参考流混用：后者含 TTP、修脸、双次 RTX，不适合「只改一小块」。',
    ],
    link: { to: '/inpaint', label: '打开局部重绘页' },
  },
  'variants/局部重绘_inpaint_rtx': {
    title: '局部重绘 + RTX 1.5×',
    steps: [
      {
        label: '① Inpaint',
        text: '与「局部重绘_inpaint」相同：原图 + 蒙版 + 采样。',
      },
      {
        label: '② RTX 放大',
        text: '解码后 RTX Video Super Resolution 放大 1.5× 再保存（需 RTX 插件）。',
      },
    ],
    notes: [
      '在局部重绘页勾选「完成后 RTX 放大」时自动使用本工作流；默认不勾选则保持原分辨率、更快。',
    ],
    link: { to: '/inpaint', label: '打开局部重绘页' },
  },
  'variants/test_chain_edit': {
    title: '链测试 · 双阶段（一采已对齐究极）',
    steps: [
      {
        label: '① 一采（究极式）',
        text: 'KSampler Adv + euler_ancestral、vae_decode=false → VAEDecode → RTX 1.5×。看预览①（RTX 后），①a 为纯解码对照。',
      },
      {
        label: '② 4x 放大 + 定标',
        text: '从 RTX 后图进 4x 模型 → 1536×2240，二采画布（与旧链相同）。',
      },
      {
        label: '③ 二采',
        text: 'VAEEncodeTiled + KSampler denoise 0.35。提示词未改，仅优化一采管线。',
      },
    ],
    notes: [
      '仍用 miaomiaoHarem + 原 LoRA/CLIP；未换究极的 Efficient Loader / WeiLin。',
      '需 RTX 插件。预览 #106 = 究极「一采」同等阶段。',
      '实测：一采若改回 dpmpp_2m_sde 易花屏；请保持 euler_ancestral。二采仍可用 dpmpp。',
    ],
  },
  'variants/test_chain_rtx_ttp': {
    title: '链测试·RTX+TTP · 出图流水线',
    steps: [
      {
        label: '① 文生图（一采）',
        text: '832×1216；KSampler Adv + euler_ancestral + VAEDecode（与链测试优化版一致，勿用 dpmpp 一采）。',
      },
      {
        label: '② RTX + 定标',
        text: 'RTX 1.5× 后定标 1536×2240 再进 TTP（避免小瓦片花脸）。预览①=RTX 后，等同究极「一采」。',
      },
      {
        label: '③ TTP 分块二采',
        text: '2×2、overlap 0.15。VAEEncode + KSampler Efficient，denoise 0.35，VAEDecode 后 TTP 拼回。',
      },
      {
        label: '④ RTX 终放大',
        text: '拼回后再 RTX 1.5×（HIGH）保存。无 FaceDetailer；要修脸请用究极参考流。',
      },
    ],
    notes: [
      '主力高清流：TTP 二采 + 双 RTX；无 4x 模型。',
      '一采请保持 euler_ancestral；二采对齐究极（15 步 / denoise 0.35）。',
      '需 RTX + TTP + Efficiency Nodes。',
    ],
  },
  'variants/高清放大_rtx': {
    title: '高清放大（RTX）· 仅超分',
    steps: [
      {
        label: '① 输入',
        text: '上传一张已生成的成图（任意来源）。',
      },
      {
        label: '② RTX 超分',
        text: '按倍数放大（默认 1.5×），AI 补细节；不是按提示词重画。',
      },
      {
        label: '③ 保存',
        text: '输出放大后的 PNG。',
      },
    ],
    notes: [
      '与局部重绘、文生图是不同「路子」：超分 ≠ Inpaint。',
      'Web 入口：顶部导航「高清放大」→ /upscale',
      '连续放大 2 次 ≈ 1.5×1.5：需连跑两次或改 JSON 串联节点。',
    ],
  },
}

/**
 * @param {string} workflowId
 * @returns {PipelineGuide | null}
 */
export function getWorkflowPipelineGuide(workflowId) {
  if (!workflowId) return null
  const id = String(workflowId).trim()
  if (WORKFLOW_PIPELINE_GUIDES[id]) return WORKFLOW_PIPELINE_GUIDES[id]
  const stem = id.replace(/^variants\//, '')
  const key = `variants/${stem}`
  return WORKFLOW_PIPELINE_GUIDES[key] || null
}
