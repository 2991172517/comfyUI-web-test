<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client.js'
import { useAppStore } from '@/stores/useAppStore.js'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Textarea from '@/components/ui/Textarea.vue'
import SelectNative from '@/components/ui/SelectNative.vue'
import Badge from '@/components/ui/Badge.vue'
import Progress from '@/components/ui/Progress.vue'
import { cn } from '@/lib/utils'
import ModelPreviewMedia from '@/components/models/ModelPreviewMedia.vue'
import { prependSourceUrl } from '@/lib/modelDescription.js'
import { collectStaticPreviewUrls } from '@/lib/modelPreviewMedia.js'
import {
  hasCivitaiApiKey,
  loadCivitaiApiKey,
  saveCivitaiApiKey,
} from '@/composables/useCivitaiApiKey.js'
import { KeyRound, Pencil, X } from 'lucide-vue-next'

const props = defineProps({
  /** 预填并自动解析的模型页链接（C 站浏览选中时传入） */
  initialUrl: { type: String, default: '' },
  /** 浏览页内嵌：隐藏「粘贴链接」输入区 */
  embedded: { type: Boolean, default: false },
})

const app = useAppStore()

const civitaiApiKey = ref(loadCivitaiApiKey())
const civitaiApiKeyDraft = ref(loadCivitaiApiKey())
const civitaiKeyEditing = ref(false)
const civitaiAccountUrl = ref('https://civitai.com/user/account')
const serverTokenConfigured = ref(false)

const url = ref('')
const parsing = ref(false)
const parseResult = ref(null)
const selectedVersionId = ref(null)
const versionDetail = ref(null)
const loadingVersion = ref(false)
const importing = ref(false)
const conflict = ref(null)
const importJob = ref(null)
const civitaiTokenReady = computed(
  () => hasCivitaiApiKey(civitaiApiKey.value) || serverTokenConfigured.value,
)

async function applyInitialUrl(raw) {
  const u = (raw || '').trim()
  if (!u) return
  url.value = u
  await doParse()
}

onMounted(async () => {
  civitaiApiKey.value = loadCivitaiApiKey()
  try {
    const s = await api.getModelSourceSettings()
    serverTokenConfigured.value = !!s.civitaiTokenConfigured
    if (s.civitaiAccountUrl) civitaiAccountUrl.value = s.civitaiAccountUrl
  } catch {
    serverTokenConfigured.value = false
  }
  if (props.initialUrl) await applyInitialUrl(props.initialUrl)
})

watch(
  () => props.initialUrl,
  async (v) => {
    if (v && v.trim() && v.trim() !== url.value.trim()) {
      await applyInitialUrl(v)
    }
  },
)

function persistCivitaiApiKey() {
  saveCivitaiApiKey(civitaiApiKey.value)
  civitaiApiKeyDraft.value = civitaiApiKey.value
  app.setMessage(
    hasCivitaiApiKey(civitaiApiKey.value)
      ? 'Civitai API Key 已保存到本浏览器'
      : '已清除本地 API Key',
  )
}

function startEditCivitaiKey() {
  civitaiApiKeyDraft.value = civitaiApiKey.value
  civitaiKeyEditing.value = true
}

function cancelEditCivitaiKey() {
  civitaiApiKeyDraft.value = civitaiApiKey.value
  civitaiKeyEditing.value = false
}

function applyCivitaiKeyEdit() {
  civitaiApiKey.value = civitaiApiKeyDraft.value.trim()
  persistCivitaiApiKey()
  civitaiKeyEditing.value = false
}

function clearCivitaiKey() {
  civitaiApiKey.value = ''
  civitaiApiKeyDraft.value = ''
  persistCivitaiApiKey()
  civitaiKeyEditing.value = false
}

const civitaiKeyMasked = computed(() => {
  const k = civitaiApiKey.value
  if (!k) return '（未配置）'
  if (k.length <= 8) return '••••••••'
  return `${k.slice(0, 4)}••••${k.slice(-4)}`
})

const descriptionEn = ref('')
const modelDescriptionPlain = ref('')
const descriptionZh = ref('')
const folder = ref('checkpoints')
const selectedFileIndex = ref(0)

const selectedVersion = computed(() =>
  parseResult.value?.versions?.find(
    (v) => String(v.versionId) === String(selectedVersionId.value),
  ),
)

const files = computed(() => versionDetail.value?.files || [])
const selectedFile = computed(() => files.value[selectedFileIndex.value])

async function doParse() {
  if (!url.value.trim()) return
  parsing.value = true
  conflict.value = null
  parseResult.value = null
  versionDetail.value = null
  try {
    const res = await api.parseModelSourceUrl(url.value.trim())
    parseResult.value = res
    folder.value = res.suggestedFolder || 'checkpoints'
    selectedVersionId.value = res.selectedVersion
    modelDescriptionPlain.value =
      res.model?.descriptionPlain || res.model?.description || ''
    descriptionEn.value = prependSourceUrl(url.value.trim(), modelDescriptionPlain.value)
    descriptionZh.value = ''
    if (selectedVersionId.value) await loadVersion()
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    parsing.value = false
  }
}

async function loadVersion() {
  if (!parseResult.value || !selectedVersionId.value) return
  loadingVersion.value = true
  try {
    const res = await api.getModelSourceVersion(
      parseResult.value.site,
      selectedVersionId.value,
      parseResult.value.model?.id,
    )
    versionDetail.value = res
    const merged =
      res.description || res.modelDescription || modelDescriptionPlain.value
    descriptionEn.value = prependSourceUrl(url.value.trim(), merged)
    selectedFileIndex.value = 0
  } catch (e) {
    app.setMessage(e.message, true)
  } finally {
    loadingVersion.value = false
  }
}

async function selectVersion(vid) {
  selectedVersionId.value = vid
  await loadVersion()
}

function previewUrls() {
  return collectStaticPreviewUrls(versionDetail.value, parseResult.value)
}

/** 只保留一处预览：有版本详情用版本图，否则用解析结果 */
const activePreviewSource = computed(() => {
  if (versionDetail.value?.previewImage) {
    return versionDetail.value.previewImage
  }
  const m = parseResult.value?.model
  if (!m) return null
  return m.previewMedia || m.previewImage || null
})

const importPageUrl = computed(() => {
  const u = url.value.trim()
  if (!u) return ''
  return /^https?:\/\//i.test(u) ? u : `https://${u}`
})

const importProgressValue = computed(() => {
  const j = importJob.value
  if (!j) return 0
  if (j.phase === 'downloading_model' && j.progress > 0) return j.progress
  if (j.status === 'completed') return 100
  if (j.phase === 'downloading_preview' && j.previewTotal > 0) {
    return Math.round((j.previewIndex / j.previewTotal) * 100)
  }
  if (j.phase === 'writing_description') return 90
  return j.progress || 5
})

function buildImportBody(importMetadataOnly = false, downloadModel = true) {
  const f = selectedFile.value
  return {
    site: parseResult.value.site,
    folder: folder.value,
    filename: f?.name || 'model.safetensors',
    download_url: f?.downloadUrl || null,
    download_model: downloadModel && !importMetadataOnly,
    import_metadata_only: importMetadataOnly,
    description_original: descriptionEn.value,
    description_translated: descriptionZh.value,
    preview_image_urls: previewUrls(),
    model_id: String(parseResult.value.model?.id || ''),
    version_id: selectedVersionId.value,
    source_url: url.value.trim(),
    civitai_api_token: civitaiApiKey.value.trim(),
  }
}

async function doImport(downloadModel, metadataOnly = false) {
  if (!selectedFile.value && downloadModel && !metadataOnly) {
    app.setMessage('请选择要下载的文件', true)
    return
  }
  if (
    downloadModel &&
    !metadataOnly &&
    parseResult.value?.site === 'civitai' &&
    !civitaiTokenReady.value
  ) {
    app.setMessage(
      '请先填写并保存 Civitai API Key（在上方），或到 C 站账户页创建',
      true,
    )
    return
  }
  importing.value = true
  conflict.value = null
  importJob.value = { phase: 'pending', message: '正在启动…', progress: 0 }
  try {
    const res = await api.importModelSourceWithProgress(
      buildImportBody(metadataOnly, downloadModel),
      (job) => {
        importJob.value = job
      },
    )
    app.setMessage(res?.message || '导入完成')
    await app.loadModelLists().catch(() => {})
  } catch (e) {
    if (e.conflict) {
      conflict.value = e.conflict
      app.setMessage(e.message, true)
    } else {
      app.setMessage(e.message, true)
    }
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <Card class="border-dashed">
      <CardHeader class="pb-2">
        <CardTitle class="text-sm flex items-center gap-2">
          <KeyRound class="h-4 w-4" />
          Civitai API Key（下载模型用）
        </CardTitle>
        <CardDescription>
          与模型链接分开配置，避免复制时混淆。仅保存在本浏览器。
        </CardDescription>
      </CardHeader>
      <CardContent
        class="space-y-3"
        :class="
          civitaiTokenReady
            ? ''
            : 'rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 -mt-1'
        "
      >
        <p v-if="!civitaiTokenReady" class="text-xs text-amber-700 dark:text-amber-300">
          下载 C 站模型前需配置 Key。到
          <a
            :href="civitaiAccountUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="underline font-medium"
          >Civitai 账户设置</a>
          创建 API Key 后点击「编辑」粘贴。
        </p>
        <p v-else class="text-xs text-muted-foreground">
          已就绪{{ serverTokenConfigured ? '（本机 + 服务端备用）' : '（本机已保存）' }}
        </p>

        <div v-if="!civitaiKeyEditing" class="flex flex-wrap items-center gap-2">
          <code
            class="flex-1 min-w-[180px] rounded-md border border-border bg-muted/30 px-3 py-2 text-xs font-mono"
          >
            {{ civitaiKeyMasked }}
          </code>
          <Button variant="outline" size="sm" class="gap-1" @click="startEditCivitaiKey">
            <Pencil class="h-3.5 w-3.5" />
            编辑
          </Button>
          <Button
            v-if="civitaiApiKey"
            variant="ghost"
            size="sm"
            class="gap-1"
            @click="clearCivitaiKey"
          >
            <X class="h-3.5 w-3.5" />
            清除
          </Button>
        </div>

        <div v-else class="space-y-2 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3">
          <Label class="text-xs">粘贴 API Key</Label>
          <Input
            v-model="civitaiApiKeyDraft"
            type="password"
            class="font-mono text-xs"
            placeholder="仅在此处粘贴，勿与模型链接混用"
            autocomplete="off"
          />
          <div class="flex flex-wrap gap-2">
            <Button size="sm" @click="applyCivitaiKeyEdit">保存到浏览器</Button>
            <Button variant="outline" size="sm" @click="cancelEditCivitaiKey">取消</Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <Card v-if="!embedded">
      <CardHeader>
        <CardTitle class="text-base">模型导入</CardTitle>
        <CardDescription>支持 Civitai（官方 API）与 Shakker 链接解析与导入。</CardDescription>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="flex flex-wrap gap-2">
          <Input
            v-model="url"
            class="flex-1 min-w-[240px]"
            placeholder="粘贴 Civitai / Shakker 模型链接"
          />
          <Button :disabled="parsing" @click="doParse">{{ parsing ? '解析中…' : '解析' }}</Button>
        </div>
      </CardContent>
    </Card>
    <div
      v-else-if="url"
      class="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/20 px-3 py-2 text-xs"
    >
      <span class="text-muted-foreground shrink-0">当前模型</span>
      <a
        :href="importPageUrl || url"
        target="_blank"
        rel="noopener noreferrer"
        class="font-mono text-primary underline truncate min-w-0 flex-1"
      >{{ url }}</a>
      <Button variant="outline" size="sm" :disabled="parsing" @click="doParse">
        {{ parsing ? '刷新…' : '重新解析' }}
      </Button>
    </div>

    <template v-if="parseResult">
      <Card>
        <CardHeader>
          <CardTitle class="text-base flex flex-wrap items-center gap-2">
            {{ parseResult.model?.name }}
            <Badge variant="outline">{{ parseResult.site }}</Badge>
            <Badge v-if="parseResult.model?.type" variant="secondary">{{ parseResult.model.type }}</Badge>
          </CardTitle>
          <CardDescription>{{ parseResult.model?.creator }}</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <ModelPreviewMedia v-if="activePreviewSource" :source="activePreviewSource" />

          <div>
            <Label class="text-xs">版本</Label>
            <div class="flex flex-wrap gap-1.5 mt-1">
              <button
                v-for="v in parseResult.versions"
                :key="v.versionId"
                type="button"
                :class="
                  cn(
                    'rounded-md border px-2.5 py-1 text-xs transition-colors',
                    String(v.versionId) === String(selectedVersionId)
                      ? 'border-primary bg-primary/15'
                      : 'border-border hover:bg-accent',
                  )
                "
                @click="selectVersion(v.versionId)"
              >
                {{ v.name }}
                <span class="text-muted-foreground">({{ v.filesCount }} 文件)</span>
              </button>
            </div>
          </div>

          <div v-if="loadingVersion" class="text-sm text-muted-foreground">加载版本详情…</div>

          <template v-else-if="versionDetail">
            <div
              v-if="versionDetail.trainedWords?.length"
              class="rounded-md border border-border/60 bg-muted/20 p-2 text-xs"
            >
              <span class="text-foreground/80">触发词：</span>
              <span class="font-mono">{{ versionDetail.trainedWords.join(', ') }}</span>
            </div>

            <div class="grid gap-3 sm:grid-cols-2">
              <div class="space-y-1.5">
                <Label>保存目录</Label>
                <SelectNative v-model="folder">
                  <option value="checkpoints">checkpoints（底模）</option>
                  <option value="loras">loras（LoRA / Style）</option>
                </SelectNative>
              </div>
              <div v-if="files.length" class="space-y-1.5">
                <Label>下载文件</Label>
                <SelectNative v-model.number="selectedFileIndex">
                  <option v-for="(f, i) in files" :key="i" :value="i">
                    {{ f.name }}{{ f.sizeDisplay ? ` (${f.sizeDisplay})` : '' }}
                  </option>
                </SelectNative>
              </div>
            </div>

            <div class="space-y-1.5">
              <Label>说明（模型页全文 + 当前版本补充，已去 HTML）</Label>
              <a
                v-if="importPageUrl"
                :href="importPageUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="text-primary hover:underline text-xs block break-all"
              >
                访问链接：{{ importPageUrl }}
              </a>
              <Textarea v-model="descriptionEn" rows="12" class="text-xs font-mono" readonly />
            </div>
            <div class="space-y-1.5">
              <Label>说明（译文，可编辑后提交保存）</Label>
              <Textarea
                v-model="descriptionZh"
                rows="4"
                class="text-xs"
                placeholder="请自行翻译后粘贴；保存时将写入模型目录下的 模型说明.txt"
              />
            </div>

            <div v-if="conflict" class="rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm">
              <p>{{ conflict.message || conflict.detail?.message }}</p>
              <Button
                size="sm"
                variant="outline"
                class="mt-2"
                :disabled="importing"
                @click="doImport(false, true)"
              >
                仅导入说明与参考图
              </Button>
            </div>

            <div
              v-if="importing && importJob"
              class="rounded-md border border-border bg-muted/20 p-3 space-y-2"
            >
              <p class="text-sm">{{ importJob.message }}</p>
              <Progress :value="importProgressValue" />
              <p class="text-[10px] text-muted-foreground">
                阶段：{{ importJob.phase }}
                <span v-if="importJob.phase === 'downloading_preview'">
                  · 参考图 {{ importJob.previewIndex }}/{{ importJob.previewTotal }}（最多 3 张）
                </span>
              </p>
            </div>

            <div class="flex flex-wrap gap-2">
              <Button variant="outline" :disabled="importing" @click="doImport(false, true)">
                不下载模型 · 仅写入说明/参考图
              </Button>
              <Button :disabled="importing || !files.length" @click="doImport(true, false)">
                {{ importing ? '导入中…' : '下载并导入' }}
              </Button>
            </div>
          </template>
        </CardContent>
      </Card>
    </template>
  </div>
</template>
