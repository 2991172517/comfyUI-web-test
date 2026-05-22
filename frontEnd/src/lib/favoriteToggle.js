/** 用 POST toggle 取消收藏，避免非管理员无法调用 DELETE。 */

export function favoriteEntryToTogglePayload(entry) {
  if (!entry) return null
  return {
    workflow_id: entry.workflow_id,
    source: entry.source,
    prompt_id: entry.prompt_id ?? null,
    batch_id: entry.batch_id ?? null,
    grid_ia: entry.grid_ia,
    grid_ib: entry.grid_ib,
    label: entry.label,
    seed: entry.seed,
    image: entry.image
      ? {
          filename: entry.image.filename,
          subfolder: entry.image.subfolder || '',
          type: entry.image.type || 'output',
        }
      : undefined,
    overrides: entry.overrides || {},
    loras_snapshot: entry.loras_snapshot,
  }
}
