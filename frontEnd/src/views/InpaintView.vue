<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { applyInpaintBootstrapFromQuery } from '@/lib/inpaintApplyBootstrap.js'
import { useAppStore } from '@/stores/useAppStore.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import WorkflowRunHeader from '@/components/run/WorkflowRunHeader.vue'
import InpaintRunBody from '@/components/run/InpaintRunBody.vue'
import { provideInpaintStore } from '@/stores/useInpaintStore.js'
import { api } from '@/api/client.js'
import {
  authSingleQuota,
  authSingleRemaining,
  hasSingleQuotaLeft,
} from '@/composables/useAuth.js'

const inpaint = provideInpaintStore()
const app = useAppStore()
const route = useRoute()
const router = useRouter()
const editorRef = ref(null)
const healthOk = ref(false)
let bootstrapApplying = false

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
    if (!h.ok) inpaint.setMessage('ComfyUI 未连接，请先启动 ComfyUI', true)
    else {
      await app.loadWorkflowList().catch(() => {})
      await app.loadModelLists().catch(() => {})
      const pick =
        app.workflows.find((w) => w.category === 'inpaint') ||
        app.workflows.find((w) => w.id.includes('inpaint'))
      if (pick && pick.id !== app.selectedId) {
        await app.loadWorkflow(pick.id)
      }
    }
  } catch (e) {
    healthOk.value = false
    inpaint.setMessage(e.message, true)
  }
})

async function tryApplyBootstrap(key) {
  if (!key || bootstrapApplying) return
  bootstrapApplying = true
  try {
    await applyInpaintBootstrapFromQuery(key, {
      editorRef,
      inpaint,
      router,
      route,
    })
  } finally {
    bootstrapApplying = false
  }
}

watch(
  () => route.query.bootstrap,
  (key) => {
    if (typeof key === 'string' && key) tryApplyBootstrap(key)
  },
  { immediate: true },
)
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-4 pb-24">
    <PageAlert />

    <div>
      <h2 class="text-lg font-semibold text-foreground">局部重绘</h2>
      <p class="mt-1 text-sm text-muted-foreground leading-relaxed">
        上传图片并涂抹要修改的区域，填写提示词后生成。涂抹区=重绘，未涂区=保留。
        <span v-if="quotaHint" class="text-foreground/80">（{{ quotaHint }}）</span>
      </p>
      <p class="mt-1 text-xs text-muted-foreground leading-relaxed">
        也可在「生成」页切换为局部重绘类工作流，与文生图共用工作流选择器。
      </p>
    </div>

    <WorkflowRunHeader />
    <InpaintRunBody :health-ok="healthOk" />
  </div>
</template>
