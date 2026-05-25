<script setup>
import { computed, onMounted, ref } from 'vue'
import PageAlert from '@/components/layout/PageAlert.vue'
import WorkflowRunHeader from '@/components/run/WorkflowRunHeader.vue'
import UpscaleRunBody from '@/components/run/UpscaleRunBody.vue'
import { useAppStore } from '@/stores/useAppStore.js'
import { provideUpscaleStore } from '@/stores/useUpscaleStore.js'
import { api } from '@/api/client.js'
import {
  authSingleQuota,
  authSingleRemaining,
} from '@/composables/useAuth.js'

provideUpscaleStore()
const upscale = useUpscaleStore()
const app = useAppStore()
const healthOk = ref(false)

const quotaHint = computed(() => {
  void authSingleQuota.value
  void authSingleRemaining.value
  const total = authSingleQuota.value
  const left = authSingleRemaining.value
  if (total == null || left == null) return ''
  return `剩余 ${left}/${total} 张`
})

onMounted(async () => {
  try {
    const h = await api.health()
    healthOk.value = !!h.ok
    if (!h.ok) upscale.setMessage('ComfyUI 未连接，请先启动 ComfyUI', true)
    else {
      await app.loadWorkflowList().catch(() => {})
      const pick =
        app.workflows.find((w) => w.category === 'upscale') ||
        app.workflows.find((w) => w.id.includes('高清'))
      if (pick && pick.id !== app.selectedId) {
        await app.loadWorkflow(pick.id)
      }
    }
  } catch (e) {
    healthOk.value = false
    upscale.setMessage(e.message, true)
  }
})
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-4 pb-24">
    <PageAlert />

    <div>
      <h2 class="text-lg font-semibold text-foreground">高清放大</h2>
      <p class="mt-1 text-sm text-muted-foreground leading-relaxed">
        上传成图后使用 RTX 超分辨率放大（非扩散重绘，不改提示词）。
        <span v-if="quotaHint" class="text-foreground/80">（{{ quotaHint }}）</span>
      </p>
      <p class="mt-1 text-xs text-muted-foreground">
        也可在「生成」页切换为高清放大类工作流。需 RTX 显卡与 ComfyUI RTX Nodes 插件。
      </p>
    </div>

    <WorkflowRunHeader />
    <UpscaleRunBody :health-ok="healthOk" />
  </div>
</template>
