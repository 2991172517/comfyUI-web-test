import { onBeforeUnmount, ref, shallowRef, unref, watch } from 'vue'
import { api } from '@/api/client.js'
import {
  applyTokenCompletion,
  getTokenAtCursor,
  normalizeTokenForSearch,
} from '@/lib/promptTokenAtCursor.js'

const MIN_QUERY_LEN = 1
const MAX_QUERY_LEN = 64
const DEBOUNCE_MS = 180

/**
 * @param {import('vue').Ref<HTMLTextAreaElement | HTMLInputElement | null>} textareaRef
 * @param {{
 *   enabled?: import('vue').Ref<boolean> | boolean
 *   onSelect?: (item: Record<string, unknown>) => void
 * }} [options]
 */
export function usePromptAutocomplete(textareaRef, options = {}) {
  const open = ref(false)
  const loading = ref(false)
  const items = shallowRef([])
  const selectedIndex = ref(0)
  /** 视口坐标（fixed），配合 Teleport 到 body */
  const position = ref({ top: 0, left: 0 })

  let debounceTimer = null
  let abortController = null
  let lastRange = { tokenStart: 0, tokenEnd: 0 }
  const queryCache = new Map()

  function isEnabled() {
    return unref(options.enabled) !== false
  }

  function close() {
    open.value = false
    items.value = []
    selectedIndex.value = 0
  }

  function cancelFetch() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
  }

  async function fetchSuggestions(query) {
    const key = query.toLowerCase()
    if (queryCache.has(key)) {
      items.value = queryCache.get(key)
      open.value = items.value.length > 0
      selectedIndex.value = 0
      updatePosition()
      return
    }

    cancelFetch()
    abortController = new AbortController()
    loading.value = true
    try {
      const res = await api.vocabularySuggest(query, { signal: abortController.signal })
      const list = res.items || []
      if (queryCache.size > 200) queryCache.clear()
      queryCache.set(key, list)
      items.value = list
      open.value = list.length > 0
      selectedIndex.value = 0
      if (open.value) updatePosition()
    } catch (e) {
      if (e?.name !== 'AbortError') {
        items.value = []
        open.value = false
      }
    } finally {
      loading.value = false
      abortController = null
    }
  }

  function updatePosition() {
    const el = textareaRef.value
    if (!el) return

    const cursor = el.selectionStart ?? 0
    const textBefore = el.value.slice(0, cursor)
    const lineStart = textBefore.lastIndexOf('\n') + 1
    const lineText = textBefore.slice(lineStart)

    const style = window.getComputedStyle(el)
    const mirror = document.createElement('div')
    mirror.setAttribute('aria-hidden', 'true')
    Object.assign(mirror.style, {
      position: 'fixed',
      visibility: 'hidden',
      whiteSpace: 'pre-wrap',
      wordWrap: 'break-word',
      top: '0',
      left: '0',
      width: style.width,
      font: style.font,
      padding: style.padding,
      lineHeight: style.lineHeight,
      letterSpacing: style.letterSpacing,
      border: style.border,
      boxSizing: style.boxSizing,
    })

    const marker = document.createElement('span')
    marker.textContent = lineText || '\u200b'
    mirror.appendChild(marker)
    document.body.appendChild(mirror)

    const textareaRect = el.getBoundingClientRect()
    const markerRect = marker.getBoundingClientRect()
    const mirrorRect = mirror.getBoundingClientRect()
    document.body.removeChild(mirror)

    const lineOffsetY = markerRect.top - mirrorRect.top
    const lineOffsetX = markerRect.left - mirrorRect.left
    const caretLeft = textareaRect.left + lineOffsetX
    const caretBottom = textareaRect.top + lineOffsetY + parseFloat(style.lineHeight || '16')

    const panelWidth = 320
    const maxLeft = window.innerWidth - panelWidth - 8
    position.value = {
      top: Math.min(caretBottom + 4, window.innerHeight - 8),
      left: Math.max(8, Math.min(caretLeft, maxLeft)),
    }
  }

  function scheduleSuggest() {
    if (!isEnabled()) return
    const el = textareaRef.value
    if (!el) return

    const cursor = el.selectionStart ?? 0
    const { token, tokenStart, tokenEnd } = getTokenAtCursor(el.value, cursor)
    lastRange = { tokenStart, tokenEnd }

    const searchQ = normalizeTokenForSearch(token)
    if (!searchQ || searchQ.length < MIN_QUERY_LEN || searchQ.length > MAX_QUERY_LEN) {
      close()
      return
    }

    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      updatePosition()
      fetchSuggestions(searchQ)
    }, DEBOUNCE_MS)
  }

  function selectItem(index) {
    const item = items.value[index]
    if (!item) return

    if (options.onSelect) {
      options.onSelect(item)
      close()
      return undefined
    }

    const el = textareaRef.value
    if (!el) return

    const insertText = item.insertText || item.insert_text || ''
    const { newText, newCursor } = applyTokenCompletion(el.value, lastRange, insertText)
    close()
    el.value = newText
    el.dispatchEvent(new Event('input', { bubbles: true }))
    requestAnimationFrame(() => {
      el.focus()
      el.setSelectionRange(newCursor, newCursor)
    })
    return newText
  }

  function onDocumentPointerDown(event) {
    if (!open.value) return
    const el = textareaRef.value
    const target = event.target
    if (el && (el === target || el.contains(target))) return
    if (target?.closest?.('[data-prompt-autocomplete]')) return
    close()
  }

  watch(open, (isOpen) => {
    if (isOpen) {
      document.addEventListener('mousedown', onDocumentPointerDown)
      document.addEventListener('touchstart', onDocumentPointerDown, { passive: true })
    } else {
      document.removeEventListener('mousedown', onDocumentPointerDown)
      document.removeEventListener('touchstart', onDocumentPointerDown)
    }
  })

  function onKeydown(event) {
    if (event.key === 'Escape') {
      if (open.value) {
        event.preventDefault()
        close()
        return true
      }
      return false
    }
    if (!open.value || items.value.length === 0) return false

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, items.value.length - 1)
      return true
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
      return true
    }
    if (event.key === 'Tab' || event.key === 'Enter') {
      event.preventDefault()
      selectItem(selectedIndex.value)
      return true
    }
    return false
  }

  onBeforeUnmount(() => {
    document.removeEventListener('mousedown', onDocumentPointerDown)
    document.removeEventListener('touchstart', onDocumentPointerDown)
    if (debounceTimer) clearTimeout(debounceTimer)
    cancelFetch()
    close()
  })

  return {
    open,
    loading,
    items,
    selectedIndex,
    position,
    close,
    scheduleSuggest,
    selectItem,
    onKeydown,
  }
}
