<script setup>
import { computed } from 'vue'
import { useBatchStore } from '@/stores/useBatchStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Progress from '@/components/ui/Progress.vue'

const batch = useBatchStore()

const cellPct = computed(() => {
  const p = batch.batch.cellProgress
  return typeof p === 'number' ? p : null
})

const detailLine = computed(() => {
  const parts = []
  if (batch.batch.currentLabel) {
    parts.push(`当前格：${batch.batch.currentLabel}`)
  }
  if (cellPct.value != null) {
    parts.push(`采样进度 ${cellPct.value}%`)
  }
  if (batch.batch.currentPromptId) {
    parts.push(`任务 ${batch.batch.currentPromptId.slice(0, 8)}…`)
  }
  return parts.join(' · ')
})
</script>

<template>
  <Card v-if="batch.isBatchRunning || batch.batch.completed > 0">
    <CardHeader class="flex flex-row flex-wrap items-center gap-3 space-y-0 pb-2">
      <CardTitle class="text-base">执行进度</CardTitle>
      <Badge :variant="batch.statusBadgeVariant(batch.batch.status)">
        {{ batch.batch.statusText }}
      </Badge>
      <Button
        v-if="batch.isBatchRunning"
        variant="secondary"
        size="sm"
        class="ml-auto shrink-0"
        @click="batch.cancelBatch"
      >
        取消批量
      </Button>
    </CardHeader>
    <CardContent class="space-y-3">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <p class="text-sm text-muted-foreground">
          {{ batch.batch.message }}
        </p>
        <p class="text-sm font-medium tabular-nums">
          {{ batch.batchProgressFraction }}
          <span class="text-muted-foreground font-normal">·</span>
          {{ batch.batchProgress }}%
        </p>
      </div>
      <Progress :value="batch.batchProgress" />
      <p v-if="detailLine" class="text-xs text-muted-foreground leading-relaxed">
        {{ detailLine }}
      </p>
      <p v-else-if="batch.batch.completed > 0 && !batch.isBatchRunning" class="text-xs text-muted-foreground">
        已完成 {{ batch.batch.completed }}/{{ batch.batch.total }} 张
      </p>
      <p v-if="batch.batch.batchId" class="font-mono text-xs text-muted-foreground">
        {{ batch.batch.batchId }}
      </p>
    </CardContent>
  </Card>
</template>
