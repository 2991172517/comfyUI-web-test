export function buildSingleFavoritePayload(workflowId, img, overrides, promptId) {
  return {
    workflow_id: workflowId,
    source: 'single',
    prompt_id: promptId || null,
    image: {
      filename: img.filename,
      subfolder: img.subfolder || '',
      type: img.type || 'output',
    },
    overrides: JSON.parse(JSON.stringify(overrides || {})),
  }
}

export function buildBatchFavoritePayload(workflowId, cell, batchId, baseOverrides) {
  const img = cell.images?.[0]
  if (!img) return null
  const loras = cell.loras
  let loras_snapshot = null
  if (loras) {
    loras_snapshot = []
    for (const key of ['A', 'B']) {
      const x = loras[key]
      if (x) {
        loras_snapshot.push({
          node_id: x.node_id,
          lora_name: x.lora_name,
          short_name: x.short_name,
          strength_model: x.strength_model,
          strength_clip: x.strength_clip,
        })
      }
    }
  }
  return {
    workflow_id: workflowId,
    source: 'batch',
    batch_id: batchId || null,
    grid_ia: cell.ia,
    grid_ib: cell.ib,
    label: cell.label,
    seed: cell.seed,
    image: {
      filename: img.filename,
      subfolder: img.subfolder || '',
      type: img.type || 'output',
    },
    overrides: JSON.parse(JSON.stringify(cell.overrides || baseOverrides || {})),
    loras_snapshot,
  }
}
