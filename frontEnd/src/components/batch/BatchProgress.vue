<script setup>
import { useBatchStore } from '@/stores/useBatchStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Progress from '@/components/ui/Progress.vue'

const batch = useBatchStore()
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
      <p class="text-sm text-muted-foreground">
        {{ batch.batch.message }} — {{ batch.batch.completed }}/{{ batch.batch.total }}
      </p>
      <Progress :value="batch.batchProgress" />
      <p v-if="batch.batch.currentLabel" class="text-xs text-muted-foreground">
        当前：{{ batch.batch.currentLabel }}
      </p>
      <p v-if="batch.batch.batchId" class="font-mono text-xs text-muted-foreground">
        {{ batch.batch.batchId }}
      </p>
    </CardContent>
  </Card>
</template>
