<script setup>
import { onMounted, ref } from 'vue'
import { gsap, prefersReducedMotion } from '@/lib/gsap/motion.js'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client.js'
import { applyQuotaFromApi, setAuthSession } from '@/composables/useAuth.js'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import FireflyEcosystemBackground from '@/components/background/FireflyEcosystemBackground.vue'
import { cn } from '@/lib/utils'

const route = useRoute()
const router = useRouter()

const mode = ref('invite')
const code = ref('')
const username = ref('admin')
const password = ref('admin123')
const loading = ref(false)
const error = ref('')
const cardRef = ref(null)

onMounted(() => {
  if (prefersReducedMotion() || !cardRef.value) return
  gsap.fromTo(
    cardRef.value,
    { opacity: 0, y: 28, scale: 0.96 },
    { opacity: 1, y: 0, scale: 1, duration: 0.55, ease: 'power3.out' },
  )
})

async function afterLogin(res) {
  if (!res.ok || !res.token) {
    error.value = res.error || '登录失败'
    return false
  }
  setAuthSession({
    token: res.token,
    role: res.role || 'user',
    username: res.username,
    invite_code: res.invite_code,
    allow_batch: res.allow_batch,
    single_quota: res.single_quota,
    single_remaining: res.single_remaining,
  })
  applyQuotaFromApi(res)
  const redirect =
    typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      ? route.query.redirect
      : res.role === 'admin'
        ? '/admin/invites'
        : '/generate'
  await router.replace(redirect)
  return true
}

async function submitInvite() {
  error.value = ''
  const v = code.value.trim()
  if (!v) {
    error.value = '请输入邀请码'
    return
  }
  loading.value = true
  try {
    await afterLogin(await api.authLogin(v))
  } catch (e) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}

async function submitAdmin() {
  error.value = ''
  if (!username.value.trim() || !password.value) {
    error.value = '请输入管理员账号和密码'
    return
  }
  loading.value = true
  try {
    await afterLogin(await api.authAdminLogin(username.value.trim(), password.value))
  } catch (e) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <FireflyEcosystemBackground variant="login">
    <div class="flex min-h-screen items-center justify-center px-4 py-16">
      <div ref="cardRef" class="w-full max-w-sm">
        <Card
          class="w-full border-[color-mix(in_srgb,var(--login-accent)_22%,transparent)] bg-[#050505]/78 text-slate-100 shadow-2xl shadow-black/50 backdrop-blur-md"
        >
          <CardHeader>
            <CardTitle class="text-lg text-slate-50">ComfyUI 控制台</CardTitle>
            <CardDescription class="text-[var(--login-text-secondary)]">
              邀请码或管理员账号登录；关闭浏览器后需重新登录。
            </CardDescription>
          </CardHeader>
          <CardContent class="space-y-4">
            <div
              class="grid grid-cols-2 rounded-lg border border-[color-mix(in_srgb,var(--login-accent)_18%,transparent)] bg-black/35 p-0.5 text-sm"
            >
              <button
                type="button"
                :class="
                  cn(
                    'rounded-md py-1.5 transition-colors',
                    mode === 'invite'
                      ? 'bg-[color-mix(in_srgb,var(--login-accent)_75%,#1a1a1a)] text-[#050505] shadow-sm'
                      : 'text-slate-400 hover:text-slate-200',
                  )
                "
                @click="mode = 'invite'"
              >
                邀请码
              </button>
              <button
                type="button"
                :class="
                  cn(
                    'rounded-md py-1.5 transition-colors',
                    mode === 'admin'
                      ? 'bg-[color-mix(in_srgb,var(--login-accent)_75%,#1a1a1a)] text-[#050505] shadow-sm'
                      : 'text-slate-400 hover:text-slate-200',
                  )
                "
                @click="mode = 'admin'"
              >
                管理员
              </button>
            </div>

            <form v-if="mode === 'invite'" class="space-y-3" @submit.prevent="submitInvite">
              <div class="space-y-1.5">
                <Label for="auth-code">邀请码</Label>
                <Input
                  id="auth-code"
                  v-model="code"
                  class="border-white/10 bg-black/40 font-mono uppercase tracking-wider"
                  placeholder="COMFY-XXXX"
                  autocomplete="off"
                  :disabled="loading"
                />
              </div>
              <p class="text-[11px] text-slate-500">
                每次登录仅可单张生成，张数由管理员配置；无法使用批量与任务计划。
              </p>
              <Button
                type="submit"
                class="w-full border-0 bg-[color-mix(in_srgb,var(--login-accent)_88%,#111)] text-[#050505] hover:bg-[var(--login-accent)]"
                :disabled="loading"
              >
                {{ loading ? '验证中…' : '进入控制台' }}
              </Button>
            </form>

            <form v-else class="space-y-3" @submit.prevent="submitAdmin">
              <div class="space-y-1.5">
                <Label for="auth-user">账号</Label>
                <Input
                  id="auth-user"
                  v-model="username"
                  class="border-white/10 bg-black/40"
                  autocomplete="username"
                  :disabled="loading"
                />
              </div>
              <div class="space-y-1.5">
                <Label for="auth-pass">密码</Label>
                <Input
                  id="auth-pass"
                  v-model="password"
                  type="password"
                  class="border-white/10 bg-black/40"
                  autocomplete="current-password"
                  :disabled="loading"
                />
              </div>
              <p class="text-[11px] text-slate-500">
                管理员可无限次登录，并可管理邀请码、执行删除操作。
              </p>
              <Button
                type="submit"
                class="w-full border-0 bg-[color-mix(in_srgb,var(--login-accent)_88%,#111)] text-[#050505] hover:bg-[var(--login-accent)]"
                :disabled="loading"
              >
                {{ loading ? '登录中…' : '管理员登录' }}
              </Button>
            </form>

            <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  </FireflyEcosystemBackground>
</template>
