<script setup lang="ts">
import {
  ArrowLeft,
  FileQuestion,
  FileText,
  FolderSearch,
  BookOpen,
  CircleAlert,
  Link,
  ListFilter,
  Pencil,
  Plus,
  Search,
  Trash2,
  Upload,
  X,
} from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { ApiError } from '@/api/client'
import { usePaperStore } from '@/stores/papers'
import { useProjectStore } from '@/stores/projects'
import type { InvalidPaperRecord, PaperSourceStatus, PaperSummary } from '@/types/api'

type ImportMode = 'upload' | 'path' | 'scan' | 'manual'

const route = useRoute()
const paperStore = usePaperStore()
const projectStore = useProjectStore()
const projectId = computed(() => String(route.params.projectId))
const query = ref('')
const sourceStatus = ref<PaperSourceStatus | ''>('')
const groupFilter = ref('')
const sort = ref('-updated_at')
const importOpen = ref(false)
const importMode = ref<ImportMode>('upload')
const editOpen = ref(false)
const editingPaper = ref<PaperSummary | null>(null)
const editForm = ref({
  title: '',
  authors: '',
  affiliations: '',
  venue: '',
  publicationDate: '',
  readingDate: '',
  citationCount: '',
  language: '',
  keywords: '',
  abstractText: '',
  group: '',
})
const busy = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const pathInput = ref('')
const manualTitle = ref('')
const uploadTitle = ref('')
const uploadFile = ref<File | null>(null)
const scanDirectory = ref('')
const recursive = ref(false)
const selectedCandidates = ref<string[]>([])
const visibleColumns = ref({
  source: true,
  group: true,
  publication: true,
  citations: true,
  pages: true,
  reading: true,
  updated: true,
})

const project = computed(() => projectStore.current)
const statuses: Array<{ value: PaperSourceStatus | ''; label: string }> = [
  { value: '', label: '全部来源状态' },
  { value: 'available', label: '来源正常' },
  { value: 'unlinked', label: '未关联文件' },
  { value: 'missing', label: '文件缺失' },
  { value: 'changed', label: '文件已变化' },
  { value: 'unreadable', label: '无法解析' },
]
const canSubmitImport = computed(() => {
  if (importMode.value === 'upload') return uploadFile.value !== null
  if (importMode.value === 'path') return pathInput.value.trim().length > 0
  if (importMode.value === 'manual') return manualTitle.value.trim().length > 0
  if (!scanDirectory.value.trim()) return false
  return !paperStore.scanResult || selectedCandidates.value.length > 0
})
const submitImportLabel = computed(() => {
  if (busy.value) return '处理中…'
  if (importMode.value === 'scan' && !paperStore.scanResult) return '扫描目录'
  return '添加记录'
})

function sourceLabel(status: PaperSourceStatus) {
  return {
    available: '正常',
    unlinked: '未关联',
    missing: '缺失',
    changed: '已变化',
    unreadable: '无法解析',
  }[status]
}

function readingLabel(status: PaperSummary['reading_status']) {
  return {
    unread: '未读',
    skimmed: '粗读',
    deep_read: '精读',
    summarized: '已总结',
    reported: '已汇报',
  }[status]
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function onFileChange(event: Event) {
  uploadFile.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function load() {
  errorMessage.value = ''
  try {
    await paperStore.load(projectId.value, {
      q: query.value,
      sourceStatus: sourceStatus.value,
      group: groupFilter.value,
      sort: sort.value,
    })
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '无法加载论文记录。'
  }
}

async function submitImport() {
  busy.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    if (importMode.value === 'upload') {
      if (!uploadFile.value) throw new Error('请选择 PDF 文件。')
      await paperStore.upload(projectId.value, uploadFile.value, uploadTitle.value)
      successMessage.value = '已读取 PDF 并创建未关联记录；PDF 文件未保存到工作区。'
    } else if (importMode.value === 'path') {
      await paperStore.link(projectId.value, pathInput.value)
      successMessage.value = '已登记原 PDF 路径，源文件保持不变。'
    } else if (importMode.value === 'manual') {
      await paperStore.createManual(projectId.value, manualTitle.value)
      successMessage.value = '已创建未关联 PDF 的论文记录。'
    } else if (!paperStore.scanResult) {
      const result = await paperStore.scan(scanDirectory.value, recursive.value)
      selectedCandidates.value = result.items.map((item) => item.candidate_id)
      successMessage.value = `找到 ${result.items.length} 个 PDF 候选，请确认选择后登记。`
      return
    } else {
      const result = await paperStore.importCandidates(projectId.value, selectedCandidates.value)
      successMessage.value = `已登记 ${result.imported.length} 篇，跳过 ${result.skipped.length} 篇。`
    }
    await load()
    importOpen.value = false
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError || error instanceof Error ? error.message : '操作失败。'
  } finally {
    busy.value = false
  }
}

async function openEdit(paper: PaperSummary) {
  busy.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const full = await paperStore.get(projectId.value, paper.paper_id)
    editingPaper.value = paper
    editForm.value = {
      title: full.bibliography.title,
      authors: full.bibliography.authors?.join(', ') ?? '',
      affiliations: full.bibliography.affiliations?.join(', ') ?? '',
      venue: full.bibliography.venue ?? '',
      publicationDate: full.bibliography.publication_date ?? '',
      readingDate: full.organization.reading_date ?? '',
      citationCount:
        full.bibliography.citation_count == null ? '' : String(full.bibliography.citation_count),
      language: full.bibliography.language ?? '',
      keywords: full.bibliography.keywords?.join(', ') ?? '',
      abstractText: full.bibliography.abstract_text ?? '',
      group: full.organization.group ?? '',
    }
    editOpen.value = true
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '论文信息格式暂不兼容，请刷新页面后再试。'
  } finally {
    busy.value = false
  }
}

function splitValues(value: string) {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

async function saveBasicInformation() {
  if (!editingPaper.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    await paperStore.updateBasicInformation(projectId.value, editingPaper.value, {
      title: editForm.value.title,
      authors: splitValues(editForm.value.authors),
      affiliations: splitValues(editForm.value.affiliations),
      venue: editForm.value.venue || null,
      publication_date: editForm.value.publicationDate || null,
      reading_date: editForm.value.readingDate || null,
      citation_count:
        editForm.value.citationCount === '' ? null : Number(editForm.value.citationCount),
      language: editForm.value.language || null,
      keywords: splitValues(editForm.value.keywords),
      abstract_text: editForm.value.abstractText,
      group: editForm.value.group || null,
    })
    editOpen.value = false
    successMessage.value = '论文基础信息与分组已保存。'
    await load()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '保存论文信息失败。'
  } finally {
    busy.value = false
  }
}

async function relink(paper: PaperSummary) {
  const path = window.prompt('输入允许目录内的新 PDF 绝对路径：', '')
  if (!path) return
  try {
    await paperStore.relink(projectId.value, paper, path)
    successMessage.value = '论文来源已重新关联。'
    await load()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '重新关联失败。'
  }
}

async function removePaper(paper: PaperSummary) {
  const confirmed = window.confirm(
    `从项目中移除“${paper.title}”吗？只删除 PaperMatrix 的记录和笔记，不会删除原 PDF。`,
  )
  if (!confirmed) return
  try {
    await paperStore.remove(projectId.value, paper.paper_id)
    successMessage.value = '论文记录已移除，原 PDF 未受影响。'
    await projectStore.loadList(true)
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '移除记录失败。'
  }
}

async function removeInvalidPaper(paper: InvalidPaperRecord) {
  const confirmed = window.confirm(
    `删除无法读取的论文记录“${paper.title}”吗？将删除 PaperMatrix 中对应的元数据和笔记，但不会删除原 PDF。此操作不会尝试修复或改写旧记录。`,
  )
  if (!confirmed) return
  try {
    await paperStore.remove(projectId.value, paper.paper_id)
    successMessage.value = '不兼容的论文记录已移除，原 PDF 未受影响。'
    await projectStore.loadList(true)
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '移除记录失败。'
  }
}

watch([sourceStatus, groupFilter, sort], () => void load())
let queryTimer = 0
watch(query, () => {
  window.clearTimeout(queryTimer)
  queryTimer = window.setTimeout(() => void load(), 250)
})
watch(importMode, () => {
  paperStore.scanResult = null
  selectedCandidates.value = []
  errorMessage.value = ''
  successMessage.value = ''
})
onMounted(() => {
  void Promise.all([projectStore.load(projectId.value), load()])
})
</script>

<template>
  <section class="page-heading page-heading--compact">
    <div>
      <RouterLink class="back-link" :to="`/projects/${projectId}`">
        <ArrowLeft :size="16" /> 项目概览
      </RouterLink>
      <p class="eyebrow">文献矩阵</p>
      <h1>{{ project?.name || '论文记录' }}</h1>
      <p>记录是知识库主体；PDF 可以正常关联、暂时缺失，也可以稍后再关联。</p>
    </div>
    <button class="button button--primary" type="button" @click="importOpen = true">
      <Plus :size="17" /> 添加论文
    </button>
  </section>

  <div class="paper-toolbar">
    <label class="search-field">
      <Search :size="17" />
      <span class="sr-only">搜索论文</span>
      <input v-model="query" type="search" placeholder="搜索标题、作者、主题或标签" />
    </label>
    <select v-model="sourceStatus" class="select-control" aria-label="来源状态">
      <option v-for="item in statuses" :key="item.value" :value="item.value">
        {{ item.label }}
      </option>
    </select>
    <select v-model="groupFilter" class="select-control" aria-label="论文分组">
      <option value="">全部分组</option>
      <option v-for="group in paperStore.availableGroups" :key="group" :value="group">
        {{ group }}
      </option>
    </select>
    <select v-model="sort" class="select-control" aria-label="排序方式">
      <option value="-updated_at">最近更新</option>
      <option value="title">标题 A–Z</option>
      <option value="-year">年份从新到旧</option>
    </select>
    <details class="column-menu">
      <summary class="icon-button" title="选择显示列"><ListFilter :size="18" /></summary>
      <div>
        <label v-for="(_, key) in visibleColumns" :key="key">
          <input v-model="visibleColumns[key]" type="checkbox" />
          {{
            {
              source: '来源',
              group: '分组',
              publication: '发表载体',
              citations: '被引次数',
              pages: '页数',
              reading: '阅读状态',
              updated: '更新时间',
            }[key]
          }}
        </label>
      </div>
    </details>
  </div>

  <div v-if="errorMessage" class="form-message form-message--error" role="alert">
    {{ errorMessage }}
  </div>
  <div v-if="successMessage" class="form-message form-message--success" role="status">
    {{ successMessage }}
  </div>

  <section
    v-if="paperStore.invalidItems.length"
    class="invalid-records"
    aria-labelledby="invalid-records-title"
  >
    <header>
      <div class="invalid-records__icon"><CircleAlert :size="20" /></div>
      <div>
        <h2 id="invalid-records-title">无法读取的论文记录（{{ paperStore.invalidTotal }}）</h2>
        <p>
          这些记录不符合当前 Paper Schema，未混入文献矩阵。你可以删除 PaperMatrix 元数据和笔记；原
          PDF 不会被删除。
        </p>
      </div>
    </header>
    <div class="invalid-records__table-wrap">
      <table>
        <thead>
          <tr>
            <th>记录</th>
            <th>Schema 版本</th>
            <th>原因</th>
            <th><span class="sr-only">操作</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="paper in paperStore.invalidItems" :key="paper.paper_id">
            <td>
              <strong>{{ paper.title }}</strong>
              <small>{{ paper.paper_id }}</small>
            </td>
            <td>{{ paper.schema_version ?? '无法识别' }}</td>
            <td>{{ paper.reason }}</td>
            <td>
              <button
                class="button button--danger button--compact"
                type="button"
                :aria-label="`删除不兼容记录 ${paper.title}`"
                @click="removeInvalidPaper(paper)"
              >
                <Trash2 :size="15" /> 删除记录
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <section
    v-if="
      !paperStore.loading && paperStore.items.length === 0 && paperStore.invalidItems.length === 0
    "
    class="empty-state"
  >
    <div class="empty-icon"><FileText :size="26" /></div>
    <h2>{{ query || sourceStatus ? '没有匹配的论文' : '项目中还没有论文记录' }}</h2>
    <p>
      {{
        query || sourceStatus
          ? '尝试清除搜索词或来源筛选。'
          : '可以读取单个 PDF、登记允许目录中的路径、扫描目录，或先只创建记录。'
      }}
    </p>
    <button
      v-if="!query && !sourceStatus"
      class="button button--primary"
      type="button"
      @click="importOpen = true"
    >
      <Plus :size="17" /> 添加第一篇论文
    </button>
  </section>

  <div v-if="paperStore.items.length" class="paper-table-wrap">
    <table class="paper-table">
      <thead>
        <tr>
          <th>论文</th>
          <th v-if="visibleColumns.source">来源</th>
          <th v-if="visibleColumns.group">分组</th>
          <th v-if="visibleColumns.publication">发表载体</th>
          <th v-if="visibleColumns.citations">被引</th>
          <th v-if="visibleColumns.pages">页数</th>
          <th v-if="visibleColumns.reading">阅读状态</th>
          <th v-if="visibleColumns.updated">更新时间</th>
          <th><span class="sr-only">操作</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="paper in paperStore.items" :key="paper.paper_id">
          <td>
            <RouterLink
              class="paper-title-link"
              :to="`/projects/${projectId}/papers/${paper.paper_id}`"
            >
              {{ paper.title }}
            </RouterLink>
            <span>{{ paper.authors.join('、') || paper.source_filename || '待补充作者' }}</span>
          </td>
          <td v-if="visibleColumns.source">
            <span class="source-chip" :class="`source-chip--${paper.source_status}`">
              {{ sourceLabel(paper.source_status) }}
            </span>
          </td>
          <td v-if="visibleColumns.group">{{ paper.group || '未分组' }}</td>
          <td v-if="visibleColumns.publication">
            {{ paper.venue || '—' }}
            <small v-if="paper.publication_date" class="table-subtext">
              {{ paper.publication_date }}
            </small>
          </td>
          <td v-if="visibleColumns.citations">{{ paper.citation_count ?? '—' }}</td>
          <td v-if="visibleColumns.pages">{{ paper.page_count ?? '—' }}</td>
          <td v-if="visibleColumns.reading">{{ readingLabel(paper.reading_status) }}</td>
          <td v-if="visibleColumns.updated">
            {{ new Intl.DateTimeFormat('zh-CN').format(new Date(paper.updated_at)) }}
          </td>
          <td>
            <div class="table-actions">
              <RouterLink
                class="icon-button"
                :to="`/projects/${projectId}/papers/${paper.paper_id}`"
                title="打开论文详情"
                :aria-label="`打开 ${paper.title}`"
              >
                <BookOpen :size="17" />
              </RouterLink>
              <button
                class="icon-button"
                type="button"
                title="编辑基础信息"
                :aria-label="`编辑 ${paper.title}`"
                @click="openEdit(paper)"
              >
                <Pencil :size="17" />
              </button>
              <button
                class="icon-button"
                type="button"
                title="重新关联 PDF"
                :aria-label="`重新关联 ${paper.title}`"
                @click="relink(paper)"
              >
                <Link :size="17" />
              </button>
              <button
                class="icon-button icon-button--danger"
                type="button"
                title="移除记录"
                :aria-label="`移除 ${paper.title}`"
                @click="removePaper(paper)"
              >
                <Trash2 :size="17" />
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="importOpen" class="modal-backdrop">
    <section class="import-dialog" role="dialog" aria-modal="true" aria-labelledby="import-title">
      <header>
        <div>
          <p class="eyebrow">添加到项目</p>
          <h2 id="import-title">添加论文记录</h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="importOpen = false">
          <X :size="20" />
        </button>
      </header>

      <div class="segmented-control" role="tablist" aria-label="添加方式">
        <button
          v-for="mode in [
            { value: 'upload', label: '单个 PDF' },
            { value: 'path', label: '文件路径' },
            { value: 'scan', label: '目录扫描' },
            { value: 'manual', label: '仅建记录' },
          ]"
          :key="mode.value"
          type="button"
          :class="{ active: importMode === mode.value }"
          @click="importMode = mode.value as ImportMode"
        >
          {{ mode.label }}
        </button>
      </div>

      <div v-if="importMode === 'upload'" class="import-pane">
        <div class="notice-line">
          <Upload :size="18" /><span>PDF 只在本次读取，不会保存副本；记录将标记为未关联。</span>
        </div>
        <label class="file-drop">
          <input type="file" accept="application/pdf,.pdf" @change="onFileChange" />
          <FileText :size="25" />
          <strong>{{ uploadFile?.name || '选择一个 PDF 文件' }}</strong>
          <span>最多 50 MB</span>
        </label>
        <label class="field">
          <span>论文标题（可选）</span>
          <input v-model="uploadTitle" type="text" placeholder="留空则尝试读取 PDF 标题" />
        </label>
      </div>

      <div v-else-if="importMode === 'path'" class="import-pane">
        <div class="notice-line">
          <Link :size="18" /><span>登记允许目录中的原文件路径，不复制、不移动 PDF。</span>
        </div>
        <label class="field">
          <span>PDF 绝对路径</span>
          <input v-model="pathInput" type="text" placeholder="/Users/name/Papers/paper.pdf" />
        </label>
      </div>

      <div v-else-if="importMode === 'manual'" class="import-pane">
        <div class="notice-line">
          <FileQuestion :size="18" /><span>先记录论文，稍后可通过“重新关联”补上 PDF。</span>
        </div>
        <label class="field">
          <span>论文标题</span>
          <input v-model="manualTitle" type="text" placeholder="输入完整或临时标题" />
        </label>
      </div>

      <div v-else class="import-pane">
        <div class="notice-line">
          <FolderSearch :size="18" /><span>只扫描设置中已允许的论文目录。</span>
        </div>
        <label class="field">
          <span>目录绝对路径</span>
          <input v-model="scanDirectory" type="text" placeholder="/Users/name/Papers" />
        </label>
        <label class="checkbox-field">
          <input v-model="recursive" type="checkbox" /> 包含子目录
        </label>
        <div v-if="paperStore.scanResult" class="candidate-list">
          <label v-for="candidate in paperStore.scanResult.items" :key="candidate.candidate_id">
            <input v-model="selectedCandidates" type="checkbox" :value="candidate.candidate_id" />
            <span>
              <strong>{{ candidate.title }}</strong>
              <small>{{ candidate.display_path }} · {{ formatBytes(candidate.size_bytes) }}</small>
            </span>
          </label>
        </div>
      </div>

      <footer>
        <span>所有论文结构化数据写入项目 YAML。</span>
        <div>
          <button class="button button--secondary" type="button" @click="importOpen = false">
            取消
          </button>
          <button
            class="button button--primary"
            type="button"
            :disabled="busy || !canSubmitImport"
            @click="submitImport"
          >
            {{ submitImportLabel }}
          </button>
        </div>
      </footer>
    </section>
  </div>

  <div v-if="editOpen" class="modal-backdrop">
    <section class="import-dialog" role="dialog" aria-modal="true" aria-labelledby="edit-title">
      <header>
        <div>
          <p class="eyebrow">论文档案</p>
          <h2 id="edit-title">编辑基础信息</h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="editOpen = false">
          <X :size="20" />
        </button>
      </header>
      <div class="metadata-form">
        <label class="field metadata-field--wide">
          <span>论文标题</span>
          <input v-model="editForm.title" type="text" required />
        </label>
        <label class="field">
          <span>作者</span>
          <input v-model="editForm.authors" type="text" placeholder="用逗号分隔" />
        </label>
        <label class="field">
          <span>署名单位</span>
          <input v-model="editForm.affiliations" type="text" placeholder="用逗号分隔" />
        </label>
        <label class="field">
          <span>发表载体</span>
          <input v-model="editForm.venue" type="text" placeholder="会议、期刊或平台" />
        </label>
        <label class="field">
          <span>论文分组</span>
          <input v-model="editForm.group" type="text" placeholder="例如：核心文献" />
        </label>
        <label class="field">
          <span>发表时间</span>
          <input v-model="editForm.publicationDate" type="date" />
        </label>
        <label class="field">
          <span>阅读时间</span>
          <input v-model="editForm.readingDate" type="date" />
        </label>
        <label class="field">
          <span>被引次数</span>
          <input v-model="editForm.citationCount" type="number" min="0" step="1" />
        </label>
        <label class="field">
          <span>语言</span>
          <input v-model="editForm.language" type="text" placeholder="例如：中文、English" />
        </label>
        <label class="field metadata-field--wide">
          <span>关键词</span>
          <input v-model="editForm.keywords" type="text" placeholder="用逗号分隔" />
        </label>
        <label class="field metadata-field--wide">
          <span>摘要</span>
          <textarea v-model="editForm.abstractText" placeholder="记录论文原摘要或自己的简要转述" />
        </label>
      </div>
      <footer>
        <span>这些字段将写入该论文的 YAML 记录。</span>
        <div>
          <button class="button button--secondary" type="button" @click="editOpen = false">
            取消
          </button>
          <button
            class="button button--primary"
            type="button"
            :disabled="busy || !editForm.title.trim()"
            @click="saveBasicInformation"
          >
            {{ busy ? '保存中…' : '保存信息' }}
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>
