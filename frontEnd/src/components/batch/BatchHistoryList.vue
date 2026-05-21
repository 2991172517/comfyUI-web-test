<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useBatchStore } from '@/stores/useBatchStore.js'
import { statusLabel } from '@/api/client.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import { cn } from '@/lib/utils'

const batch = useBatchStore()
const router = useRouter()

function openRecord(rec) {
  batch.openHistoryRecord(rec)
  router.push({ path: '/history', query: { id: rec.batch_id } })
}

onMounted(() => batch.refreshHistory())
</script>

<template>
  <Card class="h-full">
    <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
      <div>
        <CardTitle class="text-base">批量记录</CardTitle>
        <CardDescription class="text-xs">manifest.json · 无需数据库</CardDescription>
      </div>
      <Button variant="outline" size="sm" :disabled="batch.historyLoading" @click="batch.refreshHistory">
        {{ batch.historyLoading ? '…' : '刷新' }}
      </Button>
    </CardHeader>
    <CardContent class="p-0">
      <p
        v-if="!batch.historyRecords.length && !batch.historyLoading"
        class="px-4 pb-4 text-sm text-muted-foreground"
      >
        暂无记录
      </p>
      <ul v-else class="max-h-[min(70vh,640px)] divide-y divide-border overflow-y-auto xl:max-h-[calc(100vh-10rem)]">
        <li
          v-for="rec in batch.historyRecords"
          :key="rec.batch_id"
          :class="
            cn(
              'flex cursor-pointer gap-3 px-4 py-3 transition-colors hover:bg-accent/50',
              (rec.batch_id === batch.selectedHistoryId || rec.batch_id === batch.batch.batchId) &&
                'bg-accent',
            )
          "
          @click="openRecord(rec)"
        >
          <div class="h-14 w-14 shrink-0 overflow-hidden rounded-md bg-muted">
            <img
              v-if="rec.thumbnail_url"
              :src="rec.thumbnail_url"
              class="h-full w-full object-cover"
              loading="lazy"
              alt=""
            />
            <span v-else class="flex h-full items-center justify-center text-[10px] text-muted-foreground">
              无图
            </span>
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate font-mono text-xs">{{ rec.batch_id }}</p>
            <p class="mt-0.5 text-xs text-muted-foreground">
              {{ rec.workflow_id || '?' }} · {{ statusLabel(rec.status) }} ·
              {{ rec.completed }}/{{ rec.total }}
              <template v-if="rec.grid"> ({{ rec.grid.a_count }}×{{ rec.grid.b_count }})</template>
            </p>
            <p class="text-[10px] text-muted-foreground">{{ batch.formatRecordTime(rec.started_at) }}</p>
          </div>
          <Badge :variant="batch.statusBadgeVariant(rec.status)" class="shrink-0 self-start text-[10px]">
            {{ statusLabel(rec.status) }}
          </Badge>
        </li>
      </ul>
    </CardContent>
  </Card>
</template>
