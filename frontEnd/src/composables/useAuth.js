/** 登录会话：token + role + 额度 存 sessionStorage，关闭浏览器后清除 */

import { ref } from 'vue'

export const AUTH_TOKEN_KEY = 'cp_access_token'
export const AUTH_ROLE_KEY = 'cp_auth_role'
export const AUTH_USERNAME_KEY = 'cp_auth_username'
export const AUTH_INVITE_CODE_KEY = 'cp_auth_invite_code'
export const AUTH_ALLOW_BATCH_KEY = 'cp_auth_allow_batch'
export const AUTH_SINGLE_QUOTA_KEY = 'cp_auth_single_quota'
export const AUTH_SINGLE_REMAINING_KEY = 'cp_auth_single_remaining'

export const authRole = ref('')
export const authUsername = ref('')
export const authInviteCode = ref('')
export const authAllowBatch = ref(true)
export const authSingleQuota = ref(null)
export const authSingleRemaining = ref(null)

function readRoleFromStorage() {
  try {
    return sessionStorage.getItem(AUTH_ROLE_KEY) || ''
  } catch {
    return ''
  }
}

function readUsernameFromStorage() {
  try {
    return sessionStorage.getItem(AUTH_USERNAME_KEY) || ''
  } catch {
    return ''
  }
}

function readInviteCodeFromStorage() {
  try {
    return sessionStorage.getItem(AUTH_INVITE_CODE_KEY) || ''
  } catch {
    return ''
  }
}

function readAllowBatchFromStorage() {
  try {
    const v = sessionStorage.getItem(AUTH_ALLOW_BATCH_KEY)
    if (v === '0') return false
    if (v === '1') return true
    return getAuthRole() === 'admin'
  } catch {
    return true
  }
}

function readIntFromStorage(key) {
  try {
    const v = sessionStorage.getItem(key)
    if (v == null || v === '') return null
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  } catch {
    return null
  }
}

authRole.value = readRoleFromStorage()
authUsername.value = readUsernameFromStorage()
authInviteCode.value = readInviteCodeFromStorage()
authAllowBatch.value = readAllowBatchFromStorage()
authSingleQuota.value = readIntFromStorage(AUTH_SINGLE_QUOTA_KEY)
authSingleRemaining.value = readIntFromStorage(AUTH_SINGLE_REMAINING_KEY)

export function getAccessToken() {
  try {
    return sessionStorage.getItem(AUTH_TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function getAuthRole() {
  return authRole.value || readRoleFromStorage()
}

export function isAdmin() {
  return getAuthRole() === 'admin'
}

export function allowsBatch() {
  void authRole.value
  void authAllowBatch.value
  return isAdmin() || authAllowBatch.value === true
}

export function hasSingleQuotaLeft() {
  void authSingleRemaining.value
  if (isAdmin()) return true
  if (authSingleRemaining.value == null) return true
  return authSingleRemaining.value > 0
}

export function getAuthDisplayLabel() {
  void authRole.value
  void authUsername.value
  if (isAdmin()) {
    return authUsername.value || readUsernameFromStorage() || '管理员'
  }
  return '临时访问'
}

/** 从登录 / auth/me / 单图 queue 响应同步额度 */
export function applyQuotaFromApi(data) {
  if (!data || typeof data !== 'object') return
  if (typeof data.allow_batch === 'boolean') {
    authAllowBatch.value = data.allow_batch
    try {
      sessionStorage.setItem(AUTH_ALLOW_BATCH_KEY, data.allow_batch ? '1' : '0')
    } catch {
      /* ignore */
    }
  }
  if (data.single_quota != null) {
    authSingleQuota.value = Number(data.single_quota)
    try {
      sessionStorage.setItem(AUTH_SINGLE_QUOTA_KEY, String(data.single_quota))
    } catch {
      /* ignore */
    }
  }
  if (data.single_remaining != null) {
    authSingleRemaining.value = Number(data.single_remaining)
    try {
      sessionStorage.setItem(AUTH_SINGLE_REMAINING_KEY, String(data.single_remaining))
    } catch {
      /* ignore */
    }
  }
}

export function setAuthSession({ token, role, username, invite_code, ...quota }) {
  const r = role || 'user'
  const uname = username || ''
  const code = invite_code || ''
  try {
    sessionStorage.setItem(AUTH_TOKEN_KEY, token || '')
    sessionStorage.setItem(AUTH_ROLE_KEY, r)
    if (uname) sessionStorage.setItem(AUTH_USERNAME_KEY, uname)
    else sessionStorage.removeItem(AUTH_USERNAME_KEY)
    if (code) sessionStorage.setItem(AUTH_INVITE_CODE_KEY, code)
    else sessionStorage.removeItem(AUTH_INVITE_CODE_KEY)
  } catch {
    /* ignore */
  }
  authRole.value = r
  authUsername.value = uname
  authInviteCode.value = code
  if (r === 'admin') {
    authAllowBatch.value = true
    authSingleQuota.value = null
    authSingleRemaining.value = null
    try {
      sessionStorage.setItem(AUTH_ALLOW_BATCH_KEY, '1')
      sessionStorage.removeItem(AUTH_SINGLE_QUOTA_KEY)
      sessionStorage.removeItem(AUTH_SINGLE_REMAINING_KEY)
    } catch {
      /* ignore */
    }
  } else {
    applyQuotaFromApi(quota)
  }
}

export function setAccessToken(token) {
  setAuthSession({ token, role: getAuthRole() || 'user' })
}

export function clearAccessToken() {
  try {
    sessionStorage.removeItem(AUTH_TOKEN_KEY)
    sessionStorage.removeItem(AUTH_ROLE_KEY)
    sessionStorage.removeItem(AUTH_USERNAME_KEY)
    sessionStorage.removeItem(AUTH_INVITE_CODE_KEY)
    sessionStorage.removeItem(AUTH_ALLOW_BATCH_KEY)
    sessionStorage.removeItem(AUTH_SINGLE_QUOTA_KEY)
    sessionStorage.removeItem(AUTH_SINGLE_REMAINING_KEY)
  } catch {
    /* ignore */
  }
  authRole.value = ''
  authUsername.value = ''
  authInviteCode.value = ''
  authAllowBatch.value = true
  authSingleQuota.value = null
  authSingleRemaining.value = null
}

export function isLoggedIn() {
  return !!getAccessToken()
}
