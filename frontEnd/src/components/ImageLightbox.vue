<script setup>
import { ref } from 'vue'
import VueEasyLightbox from 'vue-easy-lightbox'

const visible = ref(false)
const index = ref(0)
const imgs = ref([])

function normalizeOne(item) {
  if (typeof item === 'string') return item
  if (item?.url) return item.title ? { src: item.url, title: item.title } : item.url
  return null
}

/** 仅打开一张图（轻量，避免整批网格导致卡顿） */
function openOne(image, title = '') {
  const url = typeof image === 'string' ? image : image?.url
  if (!url) return
  const entry = title ? { src: url, title } : url
  imgs.value = [entry]
  index.value = 0
  visible.value = true
}

/**
 * 画廊模式：大图浏览时最多挂载相邻 5 张，减轻 vue-easy-lightbox 压力。
 * @param {Array} images
 * @param {number} startIndex
 */
function open(images, startIndex = 0) {
  const list = (images || []).map(normalizeOne).filter(Boolean)
  if (!list.length) return
  const i = Math.min(Math.max(0, startIndex), list.length - 1)
  if (list.length <= 12) {
    imgs.value = list
    index.value = i
  } else {
    const from = Math.max(0, i - 2)
    const to = Math.min(list.length, from + 5)
    imgs.value = list.slice(from, to)
    index.value = i - from
  }
  visible.value = true
}

function onHide() {
  visible.value = false
  imgs.value = []
}

defineExpose({ open, openOne })
</script>

<template>
  <VueEasyLightbox
    :visible="visible"
    :imgs="imgs"
    :index="index"
    teleport="body"
    :scroll-disabled="true"
    @hide="onHide"
  />
</template>
