<script setup lang="ts">
import {
  ArrowLeft,
  BookOpenText,
  Check,
  Clipboard,
  FileQuestion,
  FileText,
  ListTree,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  ScanText,
  Trash2,
  X,
} from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, RouterLink, useRoute } from 'vue-router'

import { ApiError } from '@/api/client'
import AnalysisItemDialog from '@/components/AnalysisItemDialog.vue'
import NoteCandidateReviewDialog from '@/components/NoteCandidateReviewDialog.vue'
import { usePaperStore } from '@/stores/papers'
import type {
  AnalysisItem,
  AnalysisItemInput,
  EvidenceReference,
  NoteItemDocument,
  NoteItemSource,
  NoteParsePreview,
  Paper,
  PaperAnalysisDocument,
  PaperNote,
  QuestionInput,
  QuestionsDocument,
  QuestionStatus,
  ReadingQuestion,
} from '@/types/api'

type DetailTab = 'overview' | 'note' | 'supplement' | 'questions' | 'analysis'
type SaveState = 'loading' | 'saved' | 'dirty' | 'saving' | 'failed' | 'conflict'
type NoteMode = 'document' | 'items'
type SupplementDraft = { markdown: string; revision: number }

const route = useRoute()
const paperStore = usePaperStore()
const projectId = computed(() => String(route.params.projectId))
const paperId = computed(() => String(route.params.paperId))
const activeTab = ref<DetailTab>('overview')
const paper = ref<Paper | null>(null)
const note = ref<PaperNote | null>(null)
const noteDraft = ref('')
const savedDraft = ref('')
const noteState = ref<SaveState>('loading')
const supplement = ref<PaperNote | null>(null)
const supplementDraft = ref('')
const savedSupplementDraft = ref('')
const supplementState = ref<SaveState>('loading')
const noteMode = ref<NoteMode>('document')
const noteItems = ref<NoteItemDocument | null>(null)
const selectedNoteItemId = ref<string | null>(null)
const noteItemDraft = ref('')
const savedNoteItemDraft = ref('')
const questions = ref<QuestionsDocument | null>(null)
const analysis = ref<PaperAnalysisDocument | null>(null)
const loading = ref(true)
const busy = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const editOpen = ref(false)
const questionOpen = ref(false)
const analysisOpen = ref(false)
const candidateReviewOpen = ref(false)
const candidatePreview = ref<NoteParsePreview | null>(null)
const editingAnalysisItem = ref<AnalysisItem | null>(null)
const editingQuestionId = ref<string | null>(null)
const questionInitial = ref('')
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
const questionForm = ref<QuestionInput>(emptyQuestion())
let saveTimer = 0
let supplementSaveTimer = 0

const noteStateLabel = computed(
  () =>
    ({
      loading: '正在读取',
      saved: '已保存',
      dirty: '未保存',
      saving: '保存中',
      failed: '保存失败',
      conflict: '存在版本冲突',
    })[noteState.value],
)
const noteItemDirty = computed(() => noteItemDraft.value !== savedNoteItemDraft.value)
const supplementStateLabel = computed(
  () =>
    ({
      loading: '正在读取',
      saved: '已保存',
      dirty: '未保存',
      saving: '保存中',
      failed: '保存失败',
      conflict: '存在版本冲突',
    })[supplementState.value],
)
const hasUnsavedNote = computed(
  () =>
    ['dirty', 'saving', 'failed', 'conflict'].includes(noteState.value) ||
    ['dirty', 'saving', 'failed', 'conflict'].includes(supplementState.value) ||
    noteItemDirty.value,
)
const selectedNoteItem = computed(
  () => noteItems.value?.items.find((item) => item.item_id === selectedNoteItemId.value) ?? null,
)
const canSaveNoteItem = computed(
  () => noteItemDirty.value && selectedNoteItem.value?.sync_status === 'synced' && !busy.value,
)
const canSaveSupplement = computed(
  () =>
    supplementState.value !== 'saving' &&
    supplementState.value !== 'conflict' &&
    supplementDraft.value !== savedSupplementDraft.value,
)
const questionDirty = computed(
  () => questionOpen.value && JSON.stringify(questionForm.value) !== questionInitial.value,
)
const sourceLabel = computed(
  () =>
    ({
      available: '来源正常',
      unlinked: '未关联 PDF',
      missing: '源文件缺失',
      changed: '源文件已变化',
      unreadable: 'PDF 无法解析',
    })[paper.value?.source.status ?? 'unlinked'],
)
const analysisWithEvidence = computed(
  () => analysis.value?.items.filter((item) => item.evidence_refs.length > 0).length ?? 0,
)

function emptyEvidence(): EvidenceReference {
  return {
    paper_id: paperId.value,
    page_label: null,
    pdf_page_index: null,
    section: null,
    figure: null,
    table: null,
    locator_note: '',
    source_item_id: null,
  }
}

function emptyQuestion(): QuestionInput {
  return { question: '', status: 'open', answer: '', evidence: [], tags: [] }
}

function splitValues(value: string) {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function questionStatusLabel(status: QuestionStatus) {
  return { open: '待回答', answered: '已回答', deferred: '暂缓' }[status]
}

function supplementDraftKey() {
  return `papermatrix.supplement-draft:${projectId.value}:${paperId.value}`
}

function saveSupplementDraft() {
  if (!supplement.value || supplementDraft.value === savedSupplementDraft.value) {
    localStorage.removeItem(supplementDraftKey())
    return
  }
  const draft: SupplementDraft = {
    markdown: supplementDraft.value,
    revision: supplement.value.revision,
  }
  try {
    localStorage.setItem(supplementDraftKey(), JSON.stringify(draft))
  } catch {
    errorMessage.value = '补充笔记草稿无法写入本地浏览器存储，请及时复制内容。'
  }
}

function restoreSupplementDraft(remote: PaperNote) {
  let draft: SupplementDraft | null = null
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(supplementDraftKey()) ?? 'null')
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      typeof (parsed as SupplementDraft).markdown === 'string' &&
      typeof (parsed as SupplementDraft).revision === 'number'
    ) {
      draft = parsed as SupplementDraft
    }
  } catch {
    localStorage.removeItem(supplementDraftKey())
  }
  supplement.value = remote
  savedSupplementDraft.value = remote.markdown
  if (draft === null || draft.markdown === remote.markdown) {
    supplementDraft.value = remote.markdown
    supplementState.value = 'saved'
    localStorage.removeItem(supplementDraftKey())
    return
  }
  supplementDraft.value = draft.markdown
  if (draft.revision === remote.revision) {
    supplementState.value = 'dirty'
    successMessage.value = '已恢复未保存的个人补充笔记草稿。'
  } else {
    supplementState.value = 'conflict'
    errorMessage.value = '个人补充笔记已在其他位置更新，请先复制本地草稿并重新加载后合并。'
  }
}

async function loadAll() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [
      paperResult,
      noteResult,
      supplementResult,
      questionResult,
      analysisResult,
      noteItemsResult,
    ] = await Promise.all([
      paperStore.get(projectId.value, paperId.value),
      paperStore.getNote(projectId.value, paperId.value),
      paperStore.getSupplement(projectId.value, paperId.value),
      paperStore.getQuestions(projectId.value, paperId.value),
      paperStore.getAnalysis(projectId.value, paperId.value),
      paperStore.getNoteItems(projectId.value, paperId.value),
    ])
    paper.value = paperResult
    note.value = noteResult
    noteDraft.value = noteResult.markdown
    savedDraft.value = noteResult.markdown
    noteState.value = 'saved'
    restoreSupplementDraft(supplementResult)
    questions.value = questionResult
    analysis.value = analysisResult
    applyNoteItems(noteItemsResult)
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '无法读取论文详情。'
  } finally {
    loading.value = false
  }
}

async function saveSupplement() {
  if (
    !supplement.value ||
    supplementDraft.value === savedSupplementDraft.value ||
    supplementState.value === 'saving' ||
    supplementState.value === 'conflict'
  ) {
    return
  }
  window.clearTimeout(supplementSaveTimer)
  const draftToSave = supplementDraft.value
  supplementState.value = 'saving'
  try {
    const saved = await paperStore.saveSupplement(
      projectId.value,
      paperId.value,
      draftToSave,
      supplement.value.revision,
    )
    supplement.value = saved
    savedSupplementDraft.value = saved.markdown
    if (supplementDraft.value === saved.markdown) {
      supplementState.value = 'saved'
      localStorage.removeItem(supplementDraftKey())
    } else {
      supplementState.value = 'dirty'
      supplementSaveTimer = window.setTimeout(() => void saveSupplement(), 1500)
    }
  } catch (error: unknown) {
    supplementState.value =
      error instanceof ApiError && error.code === 'PM-CONFLICT-001' ? 'conflict' : 'failed'
    errorMessage.value =
      error instanceof ApiError ? error.message : '个人补充笔记保存失败，草稿仍保留在当前页面。'
  }
}

async function saveNote() {
  if (!note.value || noteDraft.value === savedDraft.value || noteState.value === 'saving') return
  window.clearTimeout(saveTimer)
  const draftToSave = noteDraft.value
  noteState.value = 'saving'
  try {
    const saved = await paperStore.saveNote(
      projectId.value,
      paperId.value,
      draftToSave,
      note.value.revision,
    )
    note.value = saved
    savedDraft.value = saved.markdown
    if (noteDraft.value === savedDraft.value) {
      noteState.value = 'saved'
      await reloadNoteItems().catch(() => {
        errorMessage.value = '笔记已保存，但条目视图刷新失败，请重新加载页面。'
      })
    } else {
      noteState.value = 'dirty'
      saveTimer = window.setTimeout(() => void saveNote(), 1500)
    }
  } catch (error: unknown) {
    noteState.value =
      error instanceof ApiError && error.code === 'PM-CONFLICT-001' ? 'conflict' : 'failed'
    errorMessage.value =
      error instanceof ApiError ? error.message : '笔记保存失败，草稿仍保留在当前页面。'
  }
}

async function copyNote() {
  await navigator.clipboard.writeText(noteDraft.value)
  successMessage.value = '笔记草稿已复制。'
}

async function copySupplement() {
  await navigator.clipboard.writeText(supplementDraft.value)
  successMessage.value = '个人补充笔记草稿已复制。'
}

function selectInitialNoteItem(document: NoteItemDocument) {
  const selected =
    document.items.find((item) => item.item_id === selectedNoteItemId.value) ??
    document.items[0] ??
    null
  selectedNoteItemId.value = selected?.item_id ?? null
  noteItemDraft.value = selected?.markdown ?? ''
  savedNoteItemDraft.value = selected?.markdown ?? ''
}

function applyNoteItems(document: NoteItemDocument) {
  noteItems.value = document
  candidatePreview.value = {
    paper_id: document.paper_id,
    note_revision: document.note_revision,
    paper_revision: document.paper_revision,
    candidates: document.candidates,
    warnings: document.warnings,
  }
  selectInitialNoteItem(document)
}

async function reloadNoteItems() {
  const document = await paperStore.getNoteItems(projectId.value, paperId.value)
  applyNoteItems(document)
}

function selectNoteItem(item: NoteItemSource) {
  if (noteItemDirty.value && !window.confirm('放弃当前条目尚未保存的修改吗？')) return
  selectedNoteItemId.value = item.item_id
  noteItemDraft.value = item.markdown
  savedNoteItemDraft.value = item.markdown
}

function switchNoteMode(mode: NoteMode) {
  if (mode === noteMode.value) return
  if (mode === 'items' && noteState.value !== 'saved') {
    errorMessage.value = '请先保存完整文档，再进入条目模式。'
    return
  }
  if (mode === 'document' && noteItemDirty.value) {
    if (!window.confirm('放弃当前条目尚未保存的修改吗？')) return
    noteItemDraft.value = savedNoteItemDraft.value
  }
  noteMode.value = mode
}

async function saveNoteItem() {
  const item = selectedNoteItem.value
  if (
    !item ||
    !noteItems.value ||
    !item.source_fingerprint ||
    item.sync_status !== 'synced' ||
    !noteItemDirty.value
  ) {
    return
  }
  busy.value = true
  errorMessage.value = ''
  try {
    const result = await paperStore.updateNoteItem(
      projectId.value,
      paperId.value,
      item.item_id,
      noteItemDraft.value,
      noteItems.value.note_revision,
      noteItems.value.paper_revision,
      item.source_fingerprint,
    )
    note.value = result.note
    noteDraft.value = result.note.markdown
    savedDraft.value = result.note.markdown
    analysis.value = result.analysis
    syncPaperRevision(result.analysis)
    const refreshed = await reloadNoteItems()
      .then(() => true)
      .catch(() => false)
    if (refreshed) {
      successMessage.value = '条目正文和分析投影已同步保存。'
    } else {
      noteMode.value = 'document'
      errorMessage.value = '条目已保存，但条目视图刷新失败，请重新加载页面。'
    }
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '条目保存失败，当前草稿仍保留。'
  } finally {
    busy.value = false
  }
}

function openPaperEdit() {
  if (!paper.value) return
  editForm.value = {
    title: paper.value.bibliography.title,
    authors: paper.value.bibliography.authors.join(', '),
    affiliations: paper.value.bibliography.affiliations.join(', '),
    venue: paper.value.bibliography.venue ?? '',
    publicationDate: paper.value.bibliography.publication_date ?? '',
    readingDate: paper.value.organization.reading_date ?? '',
    citationCount:
      paper.value.bibliography.citation_count == null
        ? ''
        : String(paper.value.bibliography.citation_count),
    language: paper.value.bibliography.language ?? '',
    keywords: paper.value.bibliography.keywords.join(', '),
    abstractText: paper.value.bibliography.abstract_text,
    group: paper.value.organization.group ?? '',
  }
  editOpen.value = true
}

async function savePaper() {
  if (!paper.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    paper.value = await paperStore.updateBasicInformation(projectId.value, paper.value, {
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
    if (analysis.value) analysis.value.revision = paper.value.revision
    editOpen.value = false
    successMessage.value = '论文基础信息已保存。'
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '保存论文信息失败。'
  } finally {
    busy.value = false
  }
}

function openQuestion(item?: ReadingQuestion) {
  editingQuestionId.value = item?.question_id ?? null
  questionForm.value = item
    ? {
        question: item.question,
        status: item.status,
        answer: item.answer,
        evidence: item.evidence.map((evidence) => ({ ...evidence })),
        tags: [...item.tags],
      }
    : emptyQuestion()
  questionInitial.value = JSON.stringify(questionForm.value)
  questionOpen.value = true
}

function closeQuestion() {
  if (questionDirty.value && !window.confirm('放弃尚未保存的问题修改吗？')) return
  questionOpen.value = false
}

function addEvidence() {
  questionForm.value.evidence.push(emptyEvidence())
}

async function saveQuestion() {
  if (!questions.value || !questionForm.value.question.trim()) return
  if (questionForm.value.status === 'answered' && !questionForm.value.answer.trim()) {
    errorMessage.value = '标记为已回答时需要填写答案。'
    return
  }
  busy.value = true
  errorMessage.value = ''
  const input: QuestionInput = {
    ...questionForm.value,
    question: questionForm.value.question.trim(),
    answer: questionForm.value.answer.trim(),
    tags: questionForm.value.tags.map((tag) => tag.trim()).filter(Boolean),
  }
  try {
    questions.value = editingQuestionId.value
      ? await paperStore.updateQuestion(
          projectId.value,
          paperId.value,
          editingQuestionId.value,
          input,
          questions.value.revision,
        )
      : await paperStore.createQuestion(
          projectId.value,
          paperId.value,
          input,
          questions.value.revision,
        )
    questionOpen.value = false
    successMessage.value = editingQuestionId.value ? '问题已更新。' : '问题已添加。'
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '问题保存失败。'
  } finally {
    busy.value = false
  }
}

async function deleteQuestion(item: ReadingQuestion) {
  if (!questions.value || !window.confirm(`删除问题“${item.question}”吗？`)) return
  try {
    questions.value = await paperStore.deleteQuestion(
      projectId.value,
      paperId.value,
      item.question_id,
      questions.value.revision,
    )
    successMessage.value = '问题已删除。'
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '问题删除失败。'
  }
}

function analysisKindLabel(kind: AnalysisItem['kind']) {
  return {
    research_problem: '研究问题',
    scenario: '适用场景',
    method: '方法路线',
    method_component: '方法组件',
    mechanism: '关键机制',
    challenge: '挑战',
    innovation: '创新点',
    contribution: '附加贡献',
    experiment: '实验',
    finding: '关键发现',
    author_limitation: '作者局限',
    reviewer_limitation: '我的评价',
    condition: '成立条件',
  }[kind]
}

function openAnalysisItem(item: AnalysisItem | null = null) {
  editingAnalysisItem.value = item
  analysisOpen.value = true
}

function syncPaperRevision(document: PaperAnalysisDocument) {
  if (!paper.value) return
  paper.value = {
    ...paper.value,
    revision: document.revision,
    updated_at: document.updated_at,
    structured_summary: {
      ...paper.value.structured_summary,
      items: document.items,
    },
  }
}

async function saveAnalysisItem(input: AnalysisItemInput) {
  if (!analysis.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    analysis.value = editingAnalysisItem.value
      ? await paperStore.updateAnalysisItem(
          projectId.value,
          paperId.value,
          editingAnalysisItem.value.item_id,
          input,
          analysis.value.revision,
        )
      : await paperStore.createAnalysisItem(
          projectId.value,
          paperId.value,
          input,
          analysis.value.revision,
        )
    syncPaperRevision(analysis.value)
    analysisOpen.value = false
    successMessage.value = editingAnalysisItem.value ? '分析条目已更新。' : '分析条目已添加。'
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '分析条目保存失败。'
  } finally {
    busy.value = false
  }
}

async function deleteAnalysisItem(item: AnalysisItem) {
  if (!analysis.value || !window.confirm(`删除分析条目“${item.title}”吗？`)) return
  try {
    analysis.value = await paperStore.deleteAnalysisItem(
      projectId.value,
      paperId.value,
      item.item_id,
      analysis.value.revision,
    )
    syncPaperRevision(analysis.value)
    successMessage.value = '分析条目已删除。'
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '分析条目删除失败。'
  }
}

async function openCandidateReview() {
  if (noteItemDirty.value) {
    errorMessage.value = '请先保存或放弃当前条目修改，再审阅完整文档变化。'
    return
  }
  if (noteState.value !== 'saved') {
    errorMessage.value = '请先等待结构化笔记保存完成，再审阅自动解析结果。'
    return
  }
  if (!candidatePreview.value) {
    await refreshNoteCandidates()
    return
  }
  candidateReviewOpen.value = true
}

async function refreshNoteCandidates() {
  busy.value = true
  errorMessage.value = ''
  try {
    await reloadNoteItems()
    candidateReviewOpen.value = true
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '自动解析结果刷新失败。'
  } finally {
    busy.value = false
  }
}

async function importNoteCandidates(candidateIds: string[]) {
  if (!candidatePreview.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    const result = await paperStore.importNoteCandidates(
      projectId.value,
      paperId.value,
      candidateIds,
      candidatePreview.value.note_revision,
      candidatePreview.value.paper_revision,
    )
    analysis.value = result.analysis
    syncPaperRevision(result.analysis)
    note.value = result.note
    noteDraft.value = result.note.markdown
    savedDraft.value = result.note.markdown
    noteState.value = 'saved'
    candidateReviewOpen.value = false
    candidatePreview.value = null
    const refreshed = await reloadNoteItems()
      .then(() => true)
      .catch(() => false)
    if (refreshed) {
      successMessage.value = `已导入 ${result.imported_items.length} 条、同步 ${result.synchronized_items.length} 条分析候选。`
    } else {
      noteMode.value = 'document'
      errorMessage.value = '候选分析已保存，但条目视图刷新失败，请重新加载页面。'
    }
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '分析候选导入失败，论文数据未修改。'
  } finally {
    busy.value = false
  }
}

function confirmLeave() {
  return !hasUnsavedNote.value || window.confirm('笔记尚未成功保存，仍要离开吗？')
}

function handleBeforeUnload(event: BeforeUnloadEvent) {
  if (!hasUnsavedNote.value) return
  event.preventDefault()
  event.returnValue = ''
}

watch(noteDraft, () => {
  if (!note.value || noteDraft.value === savedDraft.value) return
  noteState.value = 'dirty'
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => void saveNote(), 1500)
})
watch(supplementDraft, () => {
  if (!supplement.value || supplementDraft.value === savedSupplementDraft.value) {
    saveSupplementDraft()
    return
  }
  if (supplementState.value === 'conflict') {
    saveSupplementDraft()
    return
  }
  supplementState.value = 'dirty'
  saveSupplementDraft()
  window.clearTimeout(supplementSaveTimer)
  supplementSaveTimer = window.setTimeout(() => void saveSupplement(), 1500)
})
watch(
  () => questionForm.value.status,
  (status) => {
    if (status !== 'answered' || questionForm.value.answer.trim()) return
    questionForm.value.answer = ''
  },
)
onBeforeRouteLeave(() => confirmLeave())
onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  void loadAll()
})
onBeforeUnmount(() => {
  window.clearTimeout(saveTimer)
  window.clearTimeout(supplementSaveTimer)
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<template>
  <section v-if="loading" class="detail-loading">正在读取论文信息…</section>
  <template v-else-if="paper">
    <section class="paper-detail-heading">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}/papers`">
          <ArrowLeft :size="16" /> 返回论文矩阵
        </RouterLink>
        <p class="eyebrow">论文档案</p>
        <h1>{{ paper.bibliography.title }}</h1>
        <p>
          {{ paper.bibliography.authors.join('、') || '作者待补充' }}
          <span>·</span>
          {{ paper.bibliography.venue || '发表载体待补充' }}
        </p>
      </div>
      <button class="button button--secondary" type="button" @click="openPaperEdit">
        <Pencil :size="17" /> 编辑信息
      </button>
    </section>

    <div v-if="errorMessage" class="form-message form-message--error" role="alert">
      {{ errorMessage }}
    </div>
    <div v-if="successMessage" class="form-message form-message--success" role="status">
      {{ successMessage }}
    </div>

    <nav class="detail-tabs" aria-label="论文详情分区">
      <button :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">
        <BookOpenText :size="17" /> 概览
      </button>
      <button :class="{ active: activeTab === 'note' }" @click="activeTab = 'note'">
        <FileText :size="17" /> 结构化笔记
      </button>
      <button :class="{ active: activeTab === 'supplement' }" @click="activeTab = 'supplement'">
        <Clipboard :size="17" /> 个人补充
      </button>
      <button :class="{ active: activeTab === 'questions' }" @click="activeTab = 'questions'">
        <FileQuestion :size="17" /> 问题
        <span class="tab-count">{{ questions?.questions.length ?? 0 }}</span>
      </button>
      <button :class="{ active: activeTab === 'analysis' }" @click="activeTab = 'analysis'">
        <ListTree :size="17" /> 分析条目
        <span class="tab-count">{{ analysis?.items.length ?? 0 }}</span>
      </button>
    </nav>

    <section v-if="activeTab === 'overview'" class="detail-overview">
      <div class="detail-section">
        <h2>书目信息</h2>
        <dl class="metadata-grid">
          <div>
            <dt>发表时间</dt>
            <dd>{{ paper.bibliography.publication_date || '待补充' }}</dd>
          </div>
          <div>
            <dt>署名单位</dt>
            <dd>{{ paper.bibliography.affiliations.join('、') || '待补充' }}</dd>
          </div>
          <div>
            <dt>阅读时间</dt>
            <dd>{{ paper.organization.reading_date || '待补充' }}</dd>
          </div>
          <div>
            <dt>被引次数</dt>
            <dd>{{ paper.bibliography.citation_count ?? '待补充' }}</dd>
          </div>
          <div>
            <dt>语言</dt>
            <dd>{{ paper.bibliography.language || '待补充' }}</dd>
          </div>
          <div>
            <dt>项目分组</dt>
            <dd>{{ paper.organization.group || '未分组' }}</dd>
          </div>
        </dl>
      </div>
      <div class="detail-section">
        <h2>来源状态</h2>
        <div class="source-detail">
          <span class="source-chip" :class="`source-chip--${paper.source.status}`">
            {{ sourceLabel }}
          </span>
          <p>{{ paper.source.path || '当前记录没有可长期访问的 PDF 路径。' }}</p>
          <small>{{
            paper.source.page_count ? `${paper.source.page_count} 页` : '页数未知'
          }}</small>
        </div>
      </div>
      <div class="detail-section">
        <h2>摘要与关键词</h2>
        <p class="abstract-text">{{ paper.bibliography.abstract_text || '尚未填写摘要。' }}</p>
        <div class="tag-list">
          <span v-for="keyword in paper.bibliography.keywords" :key="keyword">{{ keyword }}</span>
          <span v-if="paper.bibliography.keywords.length === 0">暂无关键词</span>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'note'" class="note-workspace">
      <header class="note-toolbar">
        <div>
          <strong>Markdown 结构化笔记</strong>
          <span class="save-state" :class="`save-state--${noteState}`">
            <Check v-if="noteState === 'saved'" :size="14" />
            <RefreshCw v-else-if="noteState === 'saving'" :size="14" class="spin" />
            {{ noteStateLabel }}
          </span>
        </div>
        <div class="note-mode-switch" aria-label="笔记编辑模式">
          <button
            type="button"
            :class="{ active: noteMode === 'document' }"
            @click="switchNoteMode('document')"
          >
            完整文档
          </button>
          <button
            type="button"
            :class="{ active: noteMode === 'items' }"
            @click="switchNoteMode('items')"
          >
            条目模式
          </button>
        </div>
        <div>
          <button
            v-if="noteMode === 'document' && (noteState === 'failed' || noteState === 'conflict')"
            class="button button--secondary button--compact"
            type="button"
            @click="copyNote"
          >
            <Clipboard :size="15" /> 复制草稿
          </button>
          <button
            v-if="noteMode === 'document'"
            class="button button--primary button--compact"
            type="button"
            :disabled="noteState === 'saving' || noteDraft === savedDraft"
            @click="saveNote"
          >
            <Save :size="15" /> 保存
          </button>
          <button
            v-else
            class="button button--primary button--compact"
            type="button"
            :disabled="!canSaveNoteItem"
            @click="saveNoteItem"
          >
            <Save :size="15" /> 保存条目
          </button>
        </div>
      </header>
      <textarea
        v-if="noteMode === 'document'"
        v-model="noteDraft"
        class="note-editor"
        aria-label="论文结构化笔记"
        spellcheck="false"
      />
      <div v-else class="note-item-mode">
        <aside class="note-item-list">
          <header>
            <div>
              <strong>确认条目</strong>
              <small>{{ noteItems?.items.length ?? 0 }} 条</small>
            </div>
            <button
              v-if="noteItems?.pending_candidate_count"
              class="button button--secondary button--compact"
              type="button"
              :disabled="busy"
              @click="openCandidateReview"
            >
              审阅 {{ noteItems.pending_candidate_count }} 项变化
            </button>
          </header>
          <div v-if="noteItems?.items.length === 0" class="empty-state empty-state--compact">
            <p v-if="noteItems.note_revision === 0">填写并保存结构化文档后将自动解析候选。</p>
            <p v-else-if="noteItems.pending_candidate_count">
              已自动解析 {{ noteItems.pending_candidate_count }} 项候选，确认后可在条目模式编辑。
            </p>
            <p v-else>文档已自动解析，暂未发现可确认的结构化内容。</p>
            <button
              v-if="noteItems.pending_candidate_count"
              class="button button--secondary"
              type="button"
              @click="openCandidateReview"
            >
              <ScanText :size="16" /> 审阅自动解析结果
            </button>
          </div>
          <button
            v-for="item in noteItems?.items"
            :key="item.item_id"
            type="button"
            class="note-item-list-entry"
            :class="{ active: item.item_id === selectedNoteItemId }"
            @click="selectNoteItem(item)"
          >
            <span>
              <strong>{{ item.title }}</strong>
              <small>
                {{ item.section_title || '未绑定章节' }}
                <template v-if="item.section_order"> · 第 {{ item.section_order }} 条</template>
              </small>
            </span>
            <span class="note-sync-state" :class="`note-sync-state--${item.sync_status}`">
              {{
                item.sync_status === 'synced'
                  ? '已同步'
                  : item.sync_status === 'review_required'
                    ? '待审阅'
                    : '来源缺失'
              }}
            </span>
          </button>
        </aside>
        <main class="note-item-editor-pane">
          <div v-if="!selectedNoteItem" class="empty-state">
            <ListTree :size="28" />
            <h2>选择一个条目</h2>
            <p>条目模式直接编辑完整 Markdown 中对应稳定锚点的正文。</p>
          </div>
          <template v-else>
            <header>
              <div>
                <span class="analysis-kind">{{ analysisKindLabel(selectedNoteItem.kind) }}</span>
                <h2>{{ selectedNoteItem.title }}</h2>
              </div>
              <small>条目 ID {{ selectedNoteItem.item_id }}</small>
            </header>
            <div
              v-if="selectedNoteItem.sync_status !== 'synced'"
              class="note-review-required"
              role="status"
            >
              <strong>
                {{
                  selectedNoteItem.sync_status === 'missing'
                    ? '稳定来源锚点缺失'
                    : '完整文档已发生变化'
                }}
              </strong>
              <p>请先通过候选差异审阅确认变化，系统不会用旧投影覆盖当前 Markdown。</p>
              <button
                class="button button--secondary button--compact"
                type="button"
                @click="openCandidateReview"
              >
                打开差异审阅
              </button>
            </div>
            <textarea
              v-model="noteItemDraft"
              class="note-editor note-item-editor"
              aria-label="结构化笔记条目正文"
              spellcheck="false"
              :disabled="selectedNoteItem.sync_status !== 'synced'"
            />
            <footer>只更新此稳定锚点对应的 Markdown 片段；其他章节和段落不会重排。</footer>
          </template>
        </main>
      </div>
    </section>

    <section v-else-if="activeTab === 'supplement'" class="note-workspace">
      <header class="note-toolbar">
        <div>
          <strong>个人补充笔记</strong>
          <span class="save-state" :class="`save-state--${supplementState}`">
            <Check v-if="supplementState === 'saved'" :size="14" />
            <RefreshCw v-else-if="supplementState === 'saving'" :size="14" class="spin" />
            {{ supplementStateLabel }}
          </span>
        </div>
        <div>
          <button
            v-if="supplementState === 'failed' || supplementState === 'conflict'"
            class="button button--secondary button--compact"
            type="button"
            @click="copySupplement"
          >
            <Clipboard :size="15" /> 复制草稿
          </button>
          <button
            class="button button--primary button--compact"
            type="button"
            :disabled="!canSaveSupplement"
            @click="saveSupplement"
          >
            <Save :size="15" /> 保存
          </button>
        </div>
      </header>
      <textarea
        v-model="supplementDraft"
        class="note-editor"
        aria-label="个人补充笔记"
        placeholder="记录自己的联想、待验证想法、阅读过程和后续行动。这里不会自动解析为分析条目。"
        spellcheck="false"
      />
      <footer class="note-editor-footer">
        独立保存，不参与结构化候选解析；发生冲突时请先复制草稿并重新加载后合并。
      </footer>
    </section>

    <section v-else-if="activeTab === 'questions'" class="questions-workspace">
      <header class="questions-header">
        <div>
          <h2>阅读问题</h2>
          <p>答案可以暂时留空；证据可记录页码、章节、图和表。</p>
        </div>
        <button class="button button--primary" type="button" @click="openQuestion()">
          <Plus :size="17" /> 添加问题
        </button>
      </header>
      <div v-if="questions?.questions.length === 0" class="empty-state empty-state--compact">
        <FileQuestion :size="28" />
        <h2>还没有阅读问题</h2>
        <p>记录阅读时尚未解决的问题，之后可以继续回答和补充证据。</p>
      </div>
      <div v-else class="question-list">
        <article v-for="item in questions?.questions" :key="item.question_id">
          <header>
            <span class="question-status" :class="`question-status--${item.status}`">
              {{ questionStatusLabel(item.status) }}
            </span>
            <div class="table-actions">
              <button
                class="icon-button"
                type="button"
                title="编辑问题"
                @click="openQuestion(item)"
              >
                <Pencil :size="16" />
              </button>
              <button
                class="icon-button icon-button--danger"
                type="button"
                title="删除问题"
                @click="deleteQuestion(item)"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </header>
          <h3>{{ item.question }}</h3>
          <p :class="{ 'question-empty-answer': !item.answer }">
            {{ item.answer || '暂未回答' }}
          </p>
          <div v-if="item.evidence.length" class="evidence-list">
            <span v-for="evidence in item.evidence" :key="evidence.evidence_id">
              {{ evidence.page_label ? `第 ${evidence.page_label} 页` : '页码待补' }}
              {{ evidence.figure || evidence.table || evidence.section || '' }}
            </span>
          </div>
          <div class="tag-list">
            <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
          </div>
        </article>
      </div>
    </section>

    <section v-else class="analysis-workspace">
      <header class="questions-header">
        <div>
          <h2>可比较的分析条目</h2>
          <p>
            {{ analysis?.items.length ?? 0 }} 条记录，{{ analysisWithEvidence }} 条已有证据；
            无证据条目会明确标记。
          </p>
        </div>
        <div class="analysis-header-actions">
          <button
            v-if="noteItems?.pending_candidate_count"
            class="button button--secondary"
            type="button"
            :disabled="busy || noteState !== 'saved'"
            @click="openCandidateReview"
          >
            <ScanText :size="17" /> 审阅 {{ noteItems.pending_candidate_count }} 项自动解析结果
          </button>
          <button v-else class="button button--secondary" type="button" disabled>
            <Check :size="17" />
            {{ noteItems?.note_revision === 0 ? '保存笔记后自动解析' : '笔记已自动解析' }}
          </button>
          <button class="button button--primary" type="button" @click="openAnalysisItem()">
            <Plus :size="17" /> 添加条目
          </button>
        </div>
      </header>
      <div v-if="analysis?.items.length === 0" class="empty-state empty-state--compact">
        <ListTree :size="28" />
        <h2>还没有分析条目</h2>
        <p>先记录方法、挑战、实验、发现或局限，之后才能可靠地进入多论文比较。</p>
      </div>
      <div v-else class="analysis-list">
        <article v-for="item in analysis?.items" :key="item.item_id">
          <header>
            <div>
              <span class="analysis-kind">{{ analysisKindLabel(item.kind) }}</span>
              <span
                class="evidence-state"
                :class="{ 'evidence-state--missing': item.evidence_refs.length === 0 }"
              >
                {{ item.evidence_refs.length ? `${item.evidence_refs.length} 条证据` : '待补证据' }}
              </span>
            </div>
            <div class="table-actions">
              <button
                class="icon-button"
                type="button"
                :aria-label="`编辑 ${item.title}`"
                @click="openAnalysisItem(item)"
              >
                <Pencil :size="16" />
              </button>
              <button
                class="icon-button icon-button--danger"
                type="button"
                :aria-label="`删除 ${item.title}`"
                @click="deleteAnalysisItem(item)"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </header>
          <h3>{{ item.title }}</h3>
          <p v-if="item.section_key" class="analysis-source">
            {{ item.section_title }} · 第 {{ item.section_order }} 条 · 笔记版本
            {{ item.source_note_revision }}
          </p>
          <p>{{ item.summary || '尚未填写摘要。' }}</p>
          <dl v-if="Object.keys(item.attributes).length" class="analysis-attributes">
            <div v-for="(value, key) in item.attributes" :key="key">
              <dt>{{ key }}</dt>
              <dd>{{ value }}</dd>
            </div>
          </dl>
          <div v-if="item.evidence_refs.length" class="evidence-list">
            <span v-for="evidence in item.evidence_refs" :key="evidence.evidence_id">
              {{ evidence.page_label ? `第 ${evidence.page_label} 页` : '页码待补' }}
              {{ evidence.figure || evidence.table || evidence.section || '' }}
            </span>
          </div>
          <div class="tag-list">
            <span v-for="use in item.writing_uses" :key="use">{{ use }}</span>
            <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
          </div>
        </article>
      </div>
    </section>

    <AnalysisItemDialog
      v-if="analysisOpen"
      :paper-id="paperId"
      :item="editingAnalysisItem"
      :busy="busy"
      @close="analysisOpen = false"
      @save="saveAnalysisItem"
    />

    <NoteCandidateReviewDialog
      v-if="candidateReviewOpen && candidatePreview"
      :preview="candidatePreview"
      :busy="busy"
      @close="candidateReviewOpen = false"
      @refresh="refreshNoteCandidates"
      @import="importNoteCandidates"
    />

    <div v-if="editOpen" class="modal-backdrop">
      <section
        class="import-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="paper-edit-title"
      >
        <header>
          <div>
            <p class="eyebrow">论文档案</p>
            <h2 id="paper-edit-title">编辑基础信息</h2>
          </div>
          <button class="icon-button" type="button" aria-label="关闭" @click="editOpen = false">
            <X :size="20" />
          </button>
        </header>
        <div class="metadata-form">
          <label class="field metadata-field--wide">
            <span>论文标题</span>
            <input v-model="editForm.title" />
          </label>
          <label class="field">
            <span>作者</span>
            <input v-model="editForm.authors" placeholder="用逗号分隔" />
          </label>
          <label class="field">
            <span>署名单位</span>
            <input v-model="editForm.affiliations" placeholder="用逗号分隔" />
          </label>
          <label class="field"><span>发表载体</span><input v-model="editForm.venue" /></label>
          <label class="field"><span>论文分组</span><input v-model="editForm.group" /></label>
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
            <input v-model="editForm.citationCount" type="number" min="0" />
          </label>
          <label class="field"><span>语言</span><input v-model="editForm.language" /></label>
          <label class="field metadata-field--wide">
            <span>关键词</span>
            <input v-model="editForm.keywords" placeholder="用逗号分隔" />
          </label>
          <label class="field metadata-field--wide">
            <span>摘要</span>
            <textarea v-model="editForm.abstractText" />
          </label>
        </div>
        <footer>
          <span>这些字段写回论文 YAML。</span>
          <div>
            <button class="button button--secondary" type="button" @click="editOpen = false">
              取消
            </button>
            <button
              class="button button--primary"
              type="button"
              :disabled="busy || !editForm.title.trim()"
              @click="savePaper"
            >
              {{ busy ? '保存中…' : '保存信息' }}
            </button>
          </div>
        </footer>
      </section>
    </div>

    <div v-if="questionOpen" class="modal-backdrop">
      <section
        class="question-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="question-title"
      >
        <header>
          <div>
            <p class="eyebrow">阅读问题</p>
            <h2 id="question-title">{{ editingQuestionId ? '编辑问题' : '添加问题' }}</h2>
          </div>
          <button class="icon-button" type="button" aria-label="关闭" @click="closeQuestion">
            <X :size="20" />
          </button>
        </header>
        <div class="question-form">
          <label class="field"><span>问题</span><textarea v-model="questionForm.question" /></label>
          <div class="question-form-row">
            <label class="field">
              <span>状态</span>
              <select v-model="questionForm.status" class="select-control">
                <option value="open">待回答</option>
                <option value="answered">已回答</option>
                <option value="deferred">暂缓</option>
              </select>
            </label>
            <label class="field">
              <span>标签</span>
              <input
                :value="questionForm.tags.join(', ')"
                placeholder="用逗号分隔"
                @input="questionForm.tags = splitValues(($event.target as HTMLInputElement).value)"
              />
            </label>
          </div>
          <label class="field">
            <span>答案{{ questionForm.status === 'answered' ? '（必填）' : '（可留空）' }}</span>
            <textarea v-model="questionForm.answer" class="answer-input" />
          </label>
          <section class="evidence-editor">
            <header>
              <strong>证据定位</strong
              ><button
                class="button button--secondary button--compact"
                type="button"
                @click="addEvidence"
              >
                <Plus :size="15" /> 添加证据
              </button>
            </header>
            <div
              v-for="(evidence, index) in questionForm.evidence"
              :key="evidence.evidence_id ?? index"
              class="evidence-row"
            >
              <input v-model="evidence.page_label" placeholder="印刷页码" />
              <input
                v-model.number="evidence.pdf_page_index"
                type="number"
                min="1"
                placeholder="PDF 页"
              />
              <input v-model="evidence.section" placeholder="章节" />
              <input v-model="evidence.figure" placeholder="图号" />
              <input v-model="evidence.table" placeholder="表号" />
              <input v-model="evidence.locator_note" placeholder="定位说明" />
              <button
                class="icon-button icon-button--danger"
                type="button"
                aria-label="删除证据"
                @click="questionForm.evidence.splice(index, 1)"
              >
                <Trash2 :size="15" />
              </button>
            </div>
          </section>
        </div>
        <footer>
          <span>问题将保存到独立 YAML，不写入 Excel。</span>
          <div>
            <button class="button button--secondary" type="button" @click="closeQuestion">
              取消
            </button>
            <button
              class="button button--primary"
              type="button"
              :disabled="busy || !questionForm.question.trim()"
              @click="saveQuestion"
            >
              {{ busy ? '保存中…' : '保存问题' }}
            </button>
          </div>
        </footer>
      </section>
    </div>
  </template>
  <section v-else class="empty-state">
    <h2>无法读取论文详情</h2>
    <p>{{ errorMessage || '请返回论文矩阵并刷新。' }}</p>
  </section>
</template>
