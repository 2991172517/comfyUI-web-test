<script setup>
import { ref, watch } from 'vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  open: { type: Boolean, default: false },
  /** 若从预设导入则有值 */
  importedPresetId: { type: String, default: '' },
  importedPresetName: { type: String, default: '' },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open', 'confirm'])

const step = ref('choose')
const newName = ref('')
const description = ref('')

watch(
  () => props.open,
  (v) => {
    if (!v) return
    description.value = ''
    if (props.importedPresetId) {
      step.value = 'choose'
      newName.value = `${props.importedPresetName || '预设'}（副本）`
    } else {
      step.value = 'create'
      newName.value = '新预设'
    }
  },
)

function close() {
  emit('update:open', false)
}

function goCreate() {
  step.value = 'create'
}

function confirmOverwrite() {
  emit('confirm', {
    mode: 'overwrite',
    name: props.importedPresetName,
    description: description.value,
  })
}

function confirmCreate() {
  if (!newName.value.trim()) return
  emit('confirm', {
    mode: 'create',
    name: newName.value.trim(),
    description: description.value,
  })
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4"
      @click.self="close"
    >
      <div
        role="dialog"
        aria-modal="true"
        class="w-full max-w-md rounded-lg border border-border bg-card p-5 shadow-lg space-y-4"
        @click.stop
      >
        <h3 class="text-base font-semibold">导出为提示词预设</h3>

        <template v-if="step === 'choose' && importedPresetId">
          <p class="text-sm text-muted-foreground">
            当前配置来自预设「<strong class="text-foreground">{{ importedPresetName }}</strong>」。请选择保存方式：
          </p>
          <div class="flex flex-col gap-2">
            <Button :disabled="saving" @click="confirmOverwrite">
              覆盖原预设「{{ importedPresetName }}」
            </Button>
            <Button variant="outline" :disabled="saving" @click="goCreate">
              另存为新预设
            </Button>
          </div>
        </template>

        <template v-else>
          <p class="text-sm text-muted-foreground">
            {{ importedPresetId ? '为新预设填写名称（不会改动原预设）。' : '将当前抽卡页的固定提示与随机组保存为预设。' }}
          </p>
          <div class="space-y-3">
            <div class="space-y-1">
              <Label>预设名称</Label>
              <Input v-model="newName" placeholder="例：修女丝袜 v2" />
            </div>
            <div class="space-y-1">
              <Label>说明（可选）</Label>
              <Input v-model="description" placeholder="备注用途" />
            </div>
          </div>
          <div class="flex justify-end gap-2">
            <Button variant="ghost" :disabled="saving" @click="close">取消</Button>
            <Button :disabled="saving || !newName.trim()" @click="confirmCreate">
              {{ saving ? '保存中…' : '创建预设' }}
            </Button>
          </div>
        </template>

        <button
          v-if="step === 'choose'"
          type="button"
          :class="cn('text-xs text-muted-foreground underline')"
          :disabled="saving"
          @click="close"
        >
          取消
        </button>
      </div>
    </div>
  </Teleport>
</template>
