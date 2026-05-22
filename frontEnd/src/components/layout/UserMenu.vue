<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { ChevronDown, LogOut, User } from 'lucide-vue-next'
import { api } from '@/api/client.js'
import {
  authInviteCode,
  authRole,
  authSingleQuota,
  authSingleRemaining,
  authUsername,
  clearAccessToken,
  getAuthDisplayLabel,
  isAdmin,
} from '@/composables/useAuth.js'
import { cn } from '@/lib/utils'

const router = useRouter()
const open = ref(false)
const rootRef = ref(null)
const loggingOut = ref(false)

onClickOutside(rootRef, () => {
  open.value = false
})

const displayLabel = computed(() => {
  void authRole.value
  void authUsername.value
  return getAuthDisplayLabel()
})

const roleHint = computed(() => {
  void authRole.value
  void authInviteCode.value
  void authSingleQuota.value
  void authSingleRemaining.value
  if (isAdmin()) return '管理员 · 无单图额度限制'
  const parts = []
  if (authInviteCode.value) parts.push(`邀请码 · ${authInviteCode.value}`)
  if (authSingleRemaining.value != null && authSingleQuota.value != null) {
    parts.push(`单图剩余 ${authSingleRemaining.value}/${authSingleQuota.value}`)
  }
  return parts.join(' · ') || '邀请码访问 · 仅单张生成'
})

function toggle() {
  open.value = !open.value
}

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  open.value = false
  try {
    await api.authLogout()
  } catch {
    clearAccessToken()
  }
  await router.replace('/login')
  loggingOut.value = false
}
</script>

<template>
  <div ref="rootRef" class="relative shrink-0">
    <button
      type="button"
      :class="
        cn(
          'flex items-center gap-1.5 rounded-md border border-border bg-background/80 px-2.5 py-1.5 text-sm transition-colors',
          'hover:bg-accent hover:text-foreground',
          open && 'bg-accent text-foreground',
        )
      "
      :aria-expanded="open"
      aria-haspopup="menu"
      @click="toggle"
    >
      <User class="h-4 w-4 shrink-0 text-muted-foreground" />
      <span class="max-w-[8rem] truncate hidden sm:inline">{{ displayLabel }}</span>
      <ChevronDown
        :class="
          cn('h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform', open && 'rotate-180')
        "
      />
    </button>

    <div
      v-if="open"
      role="menu"
      class="absolute right-0 top-full z-[60] mt-1.5 min-w-[11rem] overflow-hidden rounded-lg border border-border bg-popover text-popover-foreground shadow-lg"
    >
      <div class="border-b border-border px-3 py-2.5">
        <p class="text-sm font-medium leading-tight">{{ displayLabel }}</p>
        <p class="mt-0.5 text-[11px] text-muted-foreground">{{ roleHint }}</p>
      </div>
      <div class="p-1">
        <button
          type="button"
          role="menuitem"
          class="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
          :disabled="loggingOut"
          @click="logout"
        >
          <LogOut class="h-4 w-4 shrink-0" />
          {{ loggingOut ? '退出中…' : '退出登录' }}
        </button>
      </div>
    </div>
  </div>
</template>
