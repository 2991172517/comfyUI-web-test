<script setup>
import { computed, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { ChevronDown, MoreHorizontal } from 'lucide-vue-next'
import {
  buildMoreNavItems,
  buildPrimaryNavItems,
  isMoreNavActive,
} from '@/lib/appNavItems.js'
import { cn } from '@/lib/utils'

const route = useRoute()
const moreOpen = ref(false)
const moreRef = ref(null)

onClickOutside(moreRef, () => {
  moreOpen.value = false
})

const primaryNav = computed(() => buildPrimaryNavItems())
const moreNav = computed(() => {
  void route.path
  return buildMoreNavItems()
})

const moreActive = computed(() => isMoreNavActive(route.path))

const linkClass =
  'flex items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 py-2 text-sm transition-colors text-muted-foreground hover:bg-accent hover:text-foreground lg:px-3'

function isActive(to) {
  return route.path === to || route.path.startsWith(`${to}/`)
}

function goMore(item) {
  moreOpen.value = false
}
</script>

<template>
  <nav class="flex min-w-0 flex-1 items-center gap-0.5">
    <RouterLink
      v-for="item in primaryNav"
      :key="item.to"
      :to="item.to"
      :title="item.label"
      :class="cn(linkClass, isActive(item.to) && '!bg-primary/15 !text-primary font-medium')"
    >
      <component :is="item.icon" class="h-4 w-4 shrink-0" />
      <span class="hidden md:inline">{{ item.label }}</span>
    </RouterLink>

    <div v-if="moreNav.length" ref="moreRef" class="relative shrink-0">
      <button
        type="button"
        :class="
          cn(
            linkClass,
            'border border-transparent',
            (moreOpen || moreActive) && '!bg-primary/15 !text-primary font-medium',
          )
        "
        :aria-expanded="moreOpen"
        aria-haspopup="menu"
        @click="moreOpen = !moreOpen"
      >
        <MoreHorizontal class="h-4 w-4 shrink-0 md:hidden" />
        <span class="hidden md:inline">更多</span>
        <ChevronDown
          :class="
            cn(
              'h-3.5 w-3.5 shrink-0 transition-transform hidden md:inline',
              moreOpen && 'rotate-180',
            )
          "
        />
      </button>

      <div
        v-if="moreOpen"
        role="menu"
        class="absolute left-0 top-full z-[60] mt-1 min-w-[10.5rem] overflow-hidden rounded-lg border border-border bg-popover py-1 shadow-lg"
      >
        <RouterLink
          v-for="item in moreNav"
          :key="item.to"
          :to="item.to"
          role="menuitem"
          :class="
            cn(
              'flex items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-accent',
              isActive(item.to) ? 'bg-primary/10 text-primary font-medium' : 'text-foreground',
            )
          "
          @click="goMore(item)"
        >
          <component :is="item.icon" class="h-4 w-4 shrink-0 opacity-80" />
          {{ item.label }}
        </RouterLink>
      </div>
    </div>
  </nav>
</template>
