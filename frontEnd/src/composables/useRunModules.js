/** 抽卡 / 批量页模块 Tab */

export const RUN_MODULES = [
  { id: 'prompt', label: '提示词' },
  { id: 'lora', label: 'LoRA' },
  // Style 模块暂时隐藏
  { id: 'other', label: '其他' },
]

export function otherNodeGroups(groupedNodes) {
  const skip = new Set(['提示词', '模型', 'LoRA'])
  return groupedNodes.filter(([g]) => !skip.has(g))
}
