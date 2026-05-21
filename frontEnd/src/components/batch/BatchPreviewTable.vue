<script setup>
import { useBatchStore } from '@/stores/useBatchStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'

const batch = useBatchStore()
</script>

<template>
  <Card v-if="batch.preview && batch.batch.status === 'idle'">
    <CardHeader class="pb-2">
      <CardTitle class="text-base">计划预览（前 12 项）</CardTitle>
    </CardHeader>
    <CardContent class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-border text-left text-muted-foreground">
            <th class="pb-2 pr-4 font-medium">#</th>
            <th class="pb-2 pr-4 font-medium">A</th>
            <th class="pb-2 pr-4 font-medium">B</th>
            <th class="pb-2 pr-4 font-medium">seed</th>
            <th class="pb-2 font-medium">随机提示</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in batch.preview.items.slice(0, 12)"
            :key="row.index"
            class="border-b border-border/50"
          >
            <td class="py-2 pr-4">{{ row.index }}</td>
            <td class="py-2 pr-4">{{ row.loras.A.strength_model }}</td>
            <td class="py-2 pr-4">{{ row.loras.B.strength_model }}</td>
            <td class="py-2 pr-4">{{ row.seed }}</td>
            <td class="py-2 text-xs text-muted-foreground max-w-[200px] truncate">
              <template v-if="row.prompt_picks?.length">
                {{ row.prompt_picks.map((p) => p.group_name + ':' + p.text).join(' · ') }}
              </template>
              <span v-else>—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </CardContent>
  </Card>
</template>
