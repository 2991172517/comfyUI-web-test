<script setup>
import { onMounted, ref } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import PageAlert from '@/components/layout/PageAlert.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Badge from '@/components/ui/Badge.vue'
import IconDeleteButton from '@/components/ui/IconDeleteButton.vue'
import { useConfirmDialog } from '@/composables/useConfirmDialog.js'

const app = useAppStore()
const { confirmDelete } = useConfirmDialog()
const invites = ref([])
const loading = ref(false)
const saving = ref(false)

const formOpen = ref(false)
const editingId = ref(null)
const form = ref({
  code: '',
  note: '',
  expires_at: '',
  max_uses: 1,
  single_quota_per_login: 5,
  enabled: true,
})

function resetForm() {
  editingId.value = null
  form.value = {
    code: '',
    note: '',
    expires_at: '',
    max_uses: 1,
    single_quota_per_login: 5,
    enabled: true,
  }
}

function openCreate() {
  resetForm()
  formOpen.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = {
    code: row.code,
    note: row.note || '',
    expires_at: row.expires_at ? row.expires_at.slice(0, 16) : '',
    max_uses: row.max_uses ?? 1,
    single_quota_per_login: row.single_quota_per_login ?? 5,
    enabled: row.enabled !== false,
  }
  formOpen.value = true
}

function maxUsesLabel(n) {
  const v = Number(n)
  if (v <= 0) return '不限次数'
  if (v === 1) return '单次有效'
  return `最多 ${v} 次`
}

function remainingLabel(row) {
  if (row.remaining == null) return '不限'
  return String(row.remaining)
}

async function load() {
  loading.value = true
  try {
    const res = await api.listInvites()
    invites.value = res.invites || []
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    loading.value = false
  }
}

async function saveForm() {
  const body = {
    code: form.value.code.trim(),
    note: form.value.note.trim(),
    expires_at: form.value.expires_at
      ? new Date(form.value.expires_at).toISOString()
      : null,
    max_uses: Number(form.value.max_uses),
    single_quota_per_login: Math.max(0, Number(form.value.single_quota_per_login) || 0),
    enabled: form.value.enabled,
  }
  if (!body.code) {
    app.setMessage('邀请码不能为空', true)
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await api.updateInvite(editingId.value, body)
      app.setMessage('已更新邀请码')
    } else {
      await api.createInvite(body)
      app.setMessage('已创建邀请码')
    }
    formOpen.value = false
    await load()
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    saving.value = false
  }
}

async function resetUsage(row) {
  try {
    await api.updateInvite(row.id, { used_count: 0 })
    app.setMessage('已重置使用次数')
    await load()
  } catch (e) {
    app.setMessage(e.message, true)
  }
}

async function remove(row) {
  if (!(await confirmDelete({ message: `删除邀请码「${row.code}」？` }))) return
  try {
    await api.deleteInvite(row.id)
    app.setMessage('已删除')
    await load()
  } catch (e) {
    app.setMessage(e.message, true)
  }
}

onMounted(() => load())
</script>

<template>
  <div class="space-y-4 max-w-5xl mx-auto">
    <PageAlert />

    <Card>
      <CardHeader>
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle class="text-base">邀请码管理</CardTitle>
            <CardDescription>
              增删改邀请码、登录次数、每次登录单图额度；邀请码用户仅可单张生成，无法批量与任务计划。
            </CardDescription>
          </div>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" :disabled="loading" @click="load">刷新</Button>
            <Button size="sm" @click="openCreate">新建邀请码</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p v-if="loading" class="text-sm text-muted-foreground">加载中…</p>
        <div v-else-if="!invites.length" class="text-sm text-muted-foreground py-8 text-center">
          暂无邀请码，点击「新建邀请码」添加。
        </div>
        <div v-else class="overflow-x-auto rounded-lg border border-border">
          <table class="w-full text-sm">
            <thead class="bg-muted/40 text-left text-xs text-muted-foreground">
              <tr>
                <th class="px-3 py-2">邀请码</th>
                <th class="px-3 py-2">说明</th>
                <th class="px-3 py-2">登录次数</th>
                <th class="px-3 py-2">单图/次登录</th>
                <th class="px-3 py-2">已用/剩余</th>
                <th class="px-3 py-2">过期</th>
                <th class="px-3 py-2">状态</th>
                <th class="px-3 py-2 text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in invites"
                :key="row.id"
                class="border-t border-border/80 hover:bg-muted/20"
              >
                <td class="px-3 py-2 font-mono text-xs">{{ row.code }}</td>
                <td class="px-3 py-2 text-xs text-muted-foreground max-w-[10rem] truncate">
                  {{ row.note || '—' }}
                </td>
                <td class="px-3 py-2 text-xs">{{ maxUsesLabel(row.max_uses) }}</td>
                <td class="px-3 py-2 text-xs tabular-nums">
                  {{ row.single_quota_per_login ?? 5 }} 张
                </td>
                <td class="px-3 py-2 text-xs tabular-nums">
                  {{ row.used_count || 0 }} / {{ remainingLabel(row) }}
                </td>
                <td class="px-3 py-2 text-xs text-muted-foreground">
                  {{ row.expires_at ? new Date(row.expires_at).toLocaleString('zh-CN') : '永不过期' }}
                </td>
                <td class="px-3 py-2">
                  <Badge :variant="row.enabled !== false ? 'success' : 'secondary'" class="text-[10px]">
                    {{ row.enabled !== false ? '启用' : '禁用' }}
                  </Badge>
                </td>
                <td class="px-3 py-2">
                  <div class="flex justify-end gap-1">
                    <Button variant="ghost" size="sm" class="h-7 text-xs" @click="openEdit(row)">
                      编辑
                    </Button>
                    <Button variant="ghost" size="sm" class="h-7 text-xs" @click="resetUsage(row)">
                      重置次数
                    </Button>
                    <IconDeleteButton size="sm" title="删除" @click="remove(row)" />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="text-[11px] text-muted-foreground mt-3">
          登录次数：1=单次登录；0=不限；N=最多 N 次。单图/次登录：该邀请码用户每次登录后可生成的单图张数。过期时间为空表示永不过期。
        </p>
      </CardContent>
    </Card>

    <div
      v-if="formOpen"
      class="fixed inset-0 z-[80] flex items-center justify-center bg-black/50 p-4"
      @click.self="formOpen = false"
    >
      <Card class="w-full max-w-md" @click.stop>
        <CardHeader>
          <CardTitle class="text-base">{{ editingId ? '编辑邀请码' : '新建邀请码' }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-3">
          <div class="space-y-1.5">
            <Label>邀请码</Label>
            <Input v-model="form.code" class="font-mono uppercase" :disabled="!!editingId" />
          </div>
          <div class="space-y-1.5">
            <Label>备注</Label>
            <Input v-model="form.note" />
          </div>
          <div class="space-y-1.5">
            <Label>过期时间（留空=不过期）</Label>
            <Input v-model="form.expires_at" type="datetime-local" />
          </div>
          <div class="space-y-1.5">
            <Label>登录次数 max_uses（1=单次，0=不限，N=多次）</Label>
            <Input v-model.number="form.max_uses" type="number" min="0" />
          </div>
          <div class="space-y-1.5">
            <Label>每次登录单图额度</Label>
            <Input
              v-model.number="form.single_quota_per_login"
              type="number"
              min="0"
              placeholder="默认 5"
            />
            <p class="text-[11px] text-muted-foreground">
              邀请码用户每次登录后，在退出或关闭浏览器前最多可生成的单图张数；0 表示不可生成。
            </p>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.enabled" type="checkbox" class="rounded border-input" />
            启用
          </label>
          <div class="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" @click="formOpen = false">取消</Button>
            <Button size="sm" :disabled="saving" @click="saveForm">
              {{ saving ? '保存中…' : '保存' }}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
