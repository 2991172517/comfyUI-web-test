<script setup>
import PageAlert from '@/components/layout/PageAlert.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Label from '@/components/ui/Label.vue'
import Slider from '@/components/ui/Slider.vue'
import ImageMagnifierPreview from '@/components/media/ImageMagnifierPreview.vue'
import {
  MAGNIFIER_PREVIEW_SAMPLE,
  useMagnifierSettings,
} from '@/composables/useMagnifierSettings.js'
import { useUiFontScale } from '@/composables/useUiFontScale.js'
import { cn } from '@/lib/utils'

const { lensSize, borderWidth, zoom, limits, resetToDefaults: resetMagnifierDefaults } =
  useMagnifierSettings()
const { presetId, activePreset, presets, resetToDefault: resetFontScaleDefault } = useUiFontScale()
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-4">
    <PageAlert />

    <Card>
      <CardHeader class="flex flex-row items-start justify-between gap-4 space-y-0">
        <div>
          <CardTitle>界面字号</CardTitle>
          <CardDescription>
            调整全站文字与间距基准（基于 rem）。当前：{{ activePreset.label }}（{{
              activePreset.hint
            }}）
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" @click="resetFontScaleDefault">恢复默认</Button>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Button
            v-for="item in presets"
            :key="item.id"
            type="button"
            :variant="presetId === item.id ? 'default' : 'outline'"
            class="h-auto flex-col gap-0.5 py-2.5"
            @click="presetId = item.id"
          >
            <span class="font-medium">{{ item.label }}</span>
            <span
              :class="
                cn(
                  'text-xs',
                  presetId === item.id ? 'text-primary-foreground/80' : 'text-muted-foreground',
                )
              "
            >
              {{ item.hint }}
            </span>
          </Button>
        </div>
        <p class="text-sm text-muted-foreground leading-relaxed">
          导航、卡片、按钮等使用 rem 的尺寸会同步缩放；部分固定像素（如图片网格、动画）保持不变。
        </p>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle>放大镜预览</CardTitle>
        <CardDescription>
          在下方示例图上移动鼠标预览效果；滚轮可调节放大倍数（与下方滑块同步）。设置会自动保存到本机浏览器。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          class="relative mx-auto flex h-[min(52vh,420px)] w-full max-w-md items-center justify-center overflow-hidden rounded-xl border border-border bg-muted/30"
        >
          <ImageMagnifierPreview
            fill
            wheel-sync-global-zoom
            :src="MAGNIFIER_PREVIEW_SAMPLE"
            img-class="object-contain"
          />
        </div>
        <p class="mt-3 text-center text-sm text-muted-foreground">
          桌面端悬停生效；在预览区滚轮可调整放大倍数。参考图按原比例完整显示，不裁剪。
        </p>
      </CardContent>
    </Card>

    <Card>
      <CardHeader class="flex flex-row items-start justify-between gap-4 space-y-0">
        <div>
          <CardTitle>放大镜参数</CardTitle>
          <CardDescription>调整镜头尺寸、边框粗细与放大倍数。</CardDescription>
        </div>
        <Button variant="outline" size="sm" @click="resetMagnifierDefaults">恢复默认</Button>
      </CardHeader>
      <CardContent class="space-y-6">
        <div class="space-y-2">
          <div class="flex items-center justify-between gap-2">
            <Label>镜头直径</Label>
            <span class="text-sm tabular-nums text-muted-foreground">{{ lensSize }} px</span>
          </div>
          <Slider
            v-model="lensSize"
            :min="limits.lensSize.min"
            :max="limits.lensSize.max"
            :step="limits.lensSize.step"
            :show-value="false"
          />
        </div>

        <div class="space-y-2">
          <div class="flex items-center justify-between gap-2">
            <Label>边框粗细</Label>
            <span class="text-sm tabular-nums text-muted-foreground">{{ borderWidth }} px</span>
          </div>
          <Slider
            v-model="borderWidth"
            :min="limits.borderWidth.min"
            :max="limits.borderWidth.max"
            :step="limits.borderWidth.step"
            :show-value="false"
          />
        </div>

        <div class="space-y-2">
          <div class="flex items-center justify-between gap-2">
            <Label>放大倍数</Label>
            <span class="text-sm tabular-nums text-muted-foreground">{{ zoom.toFixed(1) }}×</span>
          </div>
          <Slider
            v-model="zoom"
            :min="limits.zoom.min"
            :max="limits.zoom.max"
            :step="limits.zoom.step"
            :show-value="false"
          />
        </div>
      </CardContent>
    </Card>
  </div>
</template>
