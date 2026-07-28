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
  Quote,
  RefreshCw,
  Save,
  ScanText,
  Star,
  Trash2,
  X,
} from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, RouterLink, useRoute } from 'vue-router'

import { ApiError } from '@/api/client'
import MarkdownDocument from '@/components/MarkdownDocument.vue'
import NoteCandidateReviewDialog from '@/components/NoteCandidateReviewDialog.vue'
import { useItemLinkStore } from '@/stores/itemLinks'
import { usePaperStore } from '@/stores/papers'
import type {
  AnalysisItem,
  EvidenceReference,
  NoteItemDocument,
  NoteItemSlot,
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
type NoteMode = 'document' | 'items' | 'favorites'
type SupplementDraft = { markdown: string; revision: number }
type StructuredAttributeField = { key: string; value: string }
type StructuredAttributeRow = {
  key: string
  value: string
  fields: StructuredAttributeField[]
}

const route = useRoute()
const paperStore = usePaperStore()
const itemLinkStore = useItemLinkStore()
const projectId = computed(() => String(route.params.projectId))
const paperId = computed(() => String(route.params.paperId))
const requestedTab = typeof route.query.tab === 'string' ? route.query.tab : ''
const activeTab = ref<DetailTab>(
  ['overview', 'note', 'supplement', 'questions', 'analysis'].includes(requestedTab)
    ? (requestedTab as DetailTab)
    : 'overview',
)
const paper = ref<Paper | null>(null)
const note = ref<PaperNote | null>(null)
const noteDraft = ref('')
const savedDraft = ref('')
const noteState = ref<SaveState>('loading')
const supplement = ref<PaperNote | null>(null)
const supplementDraft = ref('')
const savedSupplementDraft = ref('')
const supplementState = ref<SaveState>('loading')
const requestedMode = typeof route.query.mode === 'string' ? route.query.mode : ''
const noteMode = ref<NoteMode>(
  ['document', 'items', 'favorites'].includes(requestedMode)
    ? (requestedMode as NoteMode)
    : 'document',
)
const noteDocumentEditing = ref(false)
const noteItems = ref<NoteItemDocument | null>(null)
const selectedNoteItemId = ref<string | null>(null)
const selectedNoteSlotKeys = ref<string[]>([])
const noteItemDraft = ref('')
const savedNoteItemDraft = ref('')
const noteItemEditing = ref(false)
const questions = ref<QuestionsDocument | null>(null)
const analysis = ref<PaperAnalysisDocument | null>(null)
const loading = ref(true)
const busy = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const editOpen = ref(false)
const noteItemCreateOpen = ref(false)
const evidenceOpen = ref(false)
const questionOpen = ref(false)
const candidateReviewOpen = ref(false)
const candidatePreview = ref<NoteParsePreview | null>(null)
const editingQuestionId = ref<string | null>(null)
const questionInitial = ref('')
const editForm = ref({
  title: '',
  shortTitle: '',
  authors: '',
  affiliations: '',
  venue: '',
  publicationDate: '',
  readingDate: '',
  citationCount: '',
  language: '',
  keywords: '',
  abstractText: '',
  paperUrl: '',
  codeUrl: '',
  dataUrl: '',
  group: '',
  readingStatus: 'unread' as Paper['organization']['reading_status'],
  importanceScore: '',
  oneSentenceSummary: '',
})
const noteItemCreateForm = ref({
  templateKey: '',
  title: '',
  markdown: '',
})
const evidenceForm = ref({
  evidenceType: '',
  locatorNote: '',
  pageLabel: '',
  pdfPageIndex: '',
  section: '',
  figure: '',
  table: '',
  attachToCurrentItem: true,
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
  () => noteItems.value?.slots.find((item) => item.slot_key === selectedNoteItemId.value) ?? null,
)
const selectedAnalysisItem = computed(
  () =>
    analysis.value?.items.find((item) => item.item_id === selectedNoteItem.value?.item_id) ?? null,
)
const selectedEvidenceIds = computed(() => new Set(selectedAnalysisItem.value?.evidence_ids ?? []))
const favoriteNoteItems = computed(
  () => noteItems.value?.items.filter((item) => item.is_favorite) ?? [],
)
const noteSlotGroups = computed(() => {
  const groups = new Map<string, NoteItemSlot[]>()
  for (const slot of noteItems.value?.slots ?? []) {
    groups.set(slot.section_title, [...(groups.get(slot.section_title) ?? []), slot])
  }
  return [...groups.entries()].map(([title, slots]) => ({ title, slots }))
})
const canSaveNoteItem = computed(
  () => noteItemDirty.value && selectedNoteItem.value?.sync_status !== 'missing' && !busy.value,
)
const selectedNoteItemNeedsAttention = computed(
  () =>
    selectedNoteItem.value?.sync_status === 'review_required' ||
    selectedNoteItem.value?.sync_status === 'missing',
)
const canCreateNoteItem = computed(
  () =>
    !busy.value &&
    Boolean(noteItemCreateForm.value.templateKey) &&
    Boolean(noteItemCreateForm.value.title.trim()),
)
const selectedCreateTemplate = computed(
  () =>
    noteItems.value?.item_templates.find(
      (template) => template.template_key === noteItemCreateForm.value.templateKey,
    ) ?? null,
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
  () => analysis.value?.items.filter((item) => resolvedEvidence(item).length > 0).length ?? 0,
)

function emptyEvidence(): EvidenceReference {
  return {
    evidence_code: null,
    paper_id: paperId.value,
    page_label: null,
    pdf_page_index: null,
    section: null,
    figure: null,
    table: null,
    locator_note: '',
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

function isPlaceholder(value: string | null) {
  const normalized = value?.trim().toLocaleLowerCase('zh-CN') ?? ''
  return (
    !normalized ||
    ['待补充', '待填写', '待查询', '待核对', '待回看 pdf'].includes(normalized) ||
    ['待补充', '待填写', '待查询', '待核对', '待回看'].some((prefix) =>
      normalized.startsWith(prefix),
    )
  )
}

function evidenceLabel(evidence: EvidenceReference) {
  const parts: string[] = []
  if (!isPlaceholder(evidence.page_label)) parts.push(`第 ${evidence.page_label?.trim()} 页`)
  for (const value of [evidence.figure, evidence.table, evidence.section]) {
    if (!isPlaceholder(value)) parts.push(value!.trim())
  }
  if (parts.length === 0 && !isPlaceholder(evidence.locator_note)) {
    parts.push(evidence.locator_note.trim())
  }
  return parts.join(' · ')
}

function evidenceLocation(evidence: EvidenceReference) {
  return evidenceLabel({ ...evidence, locator_note: '' }) || '未填写页码或图表位置'
}

function displayableEvidence(evidence: EvidenceReference[]) {
  return evidence
    .map((item) => ({ item, label: evidenceLabel(item) }))
    .filter((entry) => entry.label.length > 0)
}

function resolvedEvidence(item: AnalysisItem) {
  const evidenceById = new Map(
    (analysis.value?.evidence_catalog ?? [])
      .filter((evidence) => evidence.evidence_id)
      .map((evidence) => [evidence.evidence_id as string, evidence]),
  )
  return item.evidence_ids
    .map((evidenceId) => evidenceById.get(evidenceId))
    .filter((evidence): evidence is EvidenceReference => evidence !== undefined)
}

function displayAnalysisText(value: string) {
  return value.replace(/\[([^\]]+)]\((?:https?:\/\/)[^)]+\)/g, '$1')
}

function displayableAttributes(attributes: Record<string, string>) {
  return Object.entries(attributes).filter(
    ([key]) =>
      key.length <= 60 &&
      !/[。！？!?()[\]]/.test(key) &&
      !key.includes('http://') &&
      !key.includes('https://'),
  )
}

function structuredAttributeRows(attributes: Record<string, string>): StructuredAttributeRow[] {
  return displayableAttributes(attributes).map(([key, value]) => ({
    key,
    value,
    fields: value
      .split(';')
      .map((part) => part.trim())
      .flatMap((part) => {
        const separator = part.includes('：') ? '：' : part.includes(':') ? ':' : null
        if (!separator) return []
        const separatorIndex = part.indexOf(separator)
        const fieldKey = part.slice(0, separatorIndex).trim()
        const fieldValue = part.slice(separatorIndex + separator.length).trim()
        return fieldKey && fieldValue ? [{ key: fieldKey, value: fieldValue }] : []
      }),
  }))
}

function structuredTableData(attributes: Record<string, string>): {
  rows: StructuredAttributeRow[]
  columns: string[]
} {
  const rows = structuredAttributeRows(attributes)
  return {
    rows,
    columns: [...new Set(rows.flatMap((row) => row.fields.map((field) => field.key)))],
  }
}

function isStructuredAttributeTable(attributes: Record<string, string>) {
  const { rows, columns } = structuredTableData(attributes)
  return rows.length > 1 && columns.length > 0 && rows.every((row) => row.fields.length > 0)
}

function structuredAttributeValue(row: StructuredAttributeRow, column: string) {
  return row.fields.find((field) => field.key === column)?.value ?? ''
}

function isLegacyStructuredSummary(summary: string, attributes: Record<string, string>) {
  const attributeRows = structuredAttributeRows(attributes)
  if (!summary.trim() || attributeRows.length === 0) return false
  const serializedAttributes = attributeRows
    .map((row) => `${row.key}: ${row.value}`)
    .join('\n')
    .replace(/\s+/g, '')
  return summary.replace(/\s+/g, '') === serializedAttributes
}

function visibleTags(tags: string[]) {
  return tags.filter((tag) => tag !== '笔记解析')
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
      noteDocumentEditing.value = false
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
  const requestedItemId = typeof route.query.item === 'string' ? route.query.item : null
  const selected =
    document.slots.find((item) => item.item_id === requestedItemId) ??
    document.slots.find((item) => item.slot_key === selectedNoteItemId.value) ??
    document.slots[0] ??
    null
  selectedNoteItemId.value = selected?.slot_key ?? null
  noteItemDraft.value = selected?.markdown ?? ''
  savedNoteItemDraft.value = selected?.markdown ?? ''
}

function applyNoteItems(document: NoteItemDocument) {
  noteItems.value = document
  const currentKeys = new Set(
    document.slots.flatMap((item) => (item.can_delete ? [item.slot_key] : [])),
  )
  selectedNoteSlotKeys.value = selectedNoteSlotKeys.value.filter((slotKey) =>
    currentKeys.has(slotKey),
  )
  candidatePreview.value = {
    paper_id: document.paper_id,
    note_revision: document.note_revision,
    paper_revision: document.paper_revision,
    candidates: document.candidates,
    removals: document.removals,
    warnings: document.warnings,
  }
  selectInitialNoteItem(document)
}

async function reloadNoteItems() {
  const document = await paperStore.getNoteItems(projectId.value, paperId.value)
  applyNoteItems(document)
}

function selectNoteItem(item: NoteItemSlot) {
  if (noteItemDirty.value && !window.confirm('放弃当前条目尚未保存的修改吗？')) return
  selectedNoteItemId.value = item.slot_key
  noteItemDraft.value = item.markdown
  savedNoteItemDraft.value = item.markdown
  noteItemEditing.value = false
}

function switchNoteMode(mode: NoteMode) {
  if (mode === noteMode.value) return
  if (mode !== 'document' && noteState.value !== 'saved') {
    errorMessage.value = '请先保存完整文档，再切换到条目模式或收藏。'
    return
  }
  if (mode !== 'items' && noteItemDirty.value) {
    if (!window.confirm('放弃当前条目尚未保存的修改吗？')) return
    noteItemDraft.value = savedNoteItemDraft.value
  }
  noteMode.value = mode
  if (mode !== 'document') noteDocumentEditing.value = false
  if (mode !== 'items') noteItemEditing.value = false
}

function openFavoriteNoteItem(item: NoteItemSource) {
  const slot = noteItems.value?.slots.find((entry) => entry.item_id === item.item_id)
  if (!slot) {
    errorMessage.value = '这个收藏条目没有可编辑的模板位置。'
    return
  }
  selectedNoteItemId.value = slot.slot_key
  noteItemDraft.value = slot.markdown
  savedNoteItemDraft.value = slot.markdown
  noteItemEditing.value = false
  noteMode.value = 'items'
}

function openAnalysisSource(item?: AnalysisItem) {
  activeTab.value = 'note'
  noteMode.value = 'items'
  if (!item) {
    return
  }
  const source = noteItems.value?.slots.find((entry) => entry.item_id === item.item_id)
  if (!source) {
    errorMessage.value = '这个历史条目没有模板正文来源，不能在条目模式中编辑。'
    return
  }
  selectNoteItem(source)
}

async function saveNoteItem() {
  const slot = selectedNoteItem.value
  if (!slot || !noteItems.value || slot.sync_status === 'missing' || !noteItemDirty.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    const result =
      slot.repeatable && slot.can_delete && slot.item_id && slot.source_fingerprint
        ? await paperStore.updateNoteItem(
            projectId.value,
            paperId.value,
            slot.item_id,
            noteItemDraft.value,
            noteItems.value.note_revision,
            noteItems.value.paper_revision,
            slot.source_fingerprint,
          )
        : await paperStore.updateNoteSlot(
            projectId.value,
            paperId.value,
            slot.template_key,
            noteItemDraft.value,
            noteItems.value.note_revision,
            noteItems.value.paper_revision,
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
      successMessage.value = `${slot.label}已保存到模板原位置。`
      noteItemEditing.value = false
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

async function updateNoteItemFavorite(
  item: { item_id: string | null; is_favorite: boolean },
  isFavorite = !item.is_favorite,
) {
  if (!noteItems.value || !item.item_id) return
  busy.value = true
  errorMessage.value = ''
  try {
    const result = await paperStore.updateNoteItemFavorite(
      projectId.value,
      paperId.value,
      item.item_id,
      isFavorite,
      noteItems.value.paper_revision,
    )
    analysis.value = result.analysis
    syncPaperRevision(result.analysis)
    await reloadNoteItems()
    successMessage.value = isFavorite ? '已加入重点收藏。' : '已从重点收藏移除。'
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '更新重点收藏失败，请刷新后重试。'
  } finally {
    busy.value = false
  }
}

async function deleteNoteItems(itemIds: string[], slotKeys: string[] = []) {
  if (!noteItems.value || itemIds.length + slotKeys.length === 0) return
  const selectedCount = slotKeys.length || itemIds.length
  const noun = selectedCount === 1 ? '这个条目' : `选中的 ${selectedCount} 个条目`
  let affectedLinkCount = 0
  try {
    const impact = await itemLinkStore.inspectImpacts(
      projectId.value,
      itemIds.map((itemId) => ({ paper_id: paperId.value, item_id: itemId })),
    )
    affectedLinkCount = impact.affected_links.length
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError ? error.message : '无法检查条目关系影响，删除已取消。'
    return
  }
  const impactMessage = affectedLinkCount
    ? `\n\n该操作会留下 ${affectedLinkCount} 条可诊断的悬空关系引用，关系记录不会被静默删除。`
    : ''
  if (
    !window.confirm(
      `删除${noun}吗？对应的结构化笔记标题块和分析投影都会被删除，此操作不会修改 PDF。${impactMessage}`,
    )
  ) {
    return
  }
  busy.value = true
  errorMessage.value = ''
  try {
    const result = await paperStore.deleteNoteItems(
      projectId.value,
      paperId.value,
      itemIds,
      slotKeys,
      noteItems.value.note_revision,
      noteItems.value.paper_revision,
    )
    note.value = result.note
    noteDraft.value = result.note.markdown
    savedDraft.value = result.note.markdown
    noteState.value = 'saved'
    analysis.value = result.analysis
    syncPaperRevision(result.analysis)
    selectedNoteSlotKeys.value = []
    await reloadNoteItems()
    const deletedCount = result.deleted_slot_keys.length || result.deleted_item_ids.length
    successMessage.value = `已删除 ${deletedCount} 个条目及对应笔记内容。`
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '删除条目失败，请刷新后重试。'
  } finally {
    busy.value = false
  }
}

async function deleteNoteSlots(slotKeys: string[]) {
  const selected = (noteItems.value?.slots ?? []).filter((slot) => slotKeys.includes(slot.slot_key))
  const itemIds = selected.flatMap((slot) => (slot.item_id ? [slot.item_id] : []))
  await deleteNoteItems(itemIds, slotKeys)
}

function openNoteItemCreate(templateKey?: string | null) {
  if (!noteItems.value?.item_templates.length) return
  const selectedTemplateKey =
    templateKey ??
    selectedNoteItem.value?.repeatable_template_key ??
    noteItems.value.item_templates[0]?.template_key ??
    ''
  const template =
    noteItems.value.item_templates.find((item) => item.template_key === selectedTemplateKey) ??
    noteItems.value.item_templates[0]
  noteItemCreateForm.value = {
    templateKey: template?.template_key ?? '',
    title: '',
    markdown: template?.body_template ?? '',
  }
  noteItemCreateOpen.value = true
}

function changeNoteItemCreateTemplate() {
  noteItemCreateForm.value.markdown = selectedCreateTemplate.value?.body_template ?? ''
}

async function createNoteItem() {
  if (
    !noteItems.value ||
    !noteItemCreateForm.value.templateKey ||
    !noteItemCreateForm.value.title.trim()
  ) {
    return
  }
  busy.value = true
  errorMessage.value = ''
  try {
    const result = await paperStore.createNoteItem(
      projectId.value,
      paperId.value,
      {
        template_key: noteItemCreateForm.value.templateKey,
        title: noteItemCreateForm.value.title.trim(),
        markdown: noteItemCreateForm.value.markdown.trim(),
      },
      noteItems.value.note_revision,
      noteItems.value.paper_revision,
    )
    note.value = result.note
    noteDraft.value = result.note.markdown
    savedDraft.value = result.note.markdown
    analysis.value = result.analysis
    syncPaperRevision(result.analysis)
    await reloadNoteItems()
    const createdSlot = noteItems.value?.slots.find((slot) => slot.item_id === result.item.item_id)
    if (createdSlot) {
      selectNoteItem(createdSlot)
      noteItemEditing.value = true
    }
    noteItemCreateOpen.value = false
    successMessage.value = `${selectedCreateTemplate.value?.label ?? '条目'}已加入模板对应位置。`
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '添加条目失败，请刷新后重试。'
  } finally {
    busy.value = false
  }
}

function openEvidenceCreate() {
  if (noteItemDirty.value) {
    errorMessage.value = '请先保存当前条目，再添加证据。'
    return
  }
  evidenceForm.value = {
    evidenceType: '',
    locatorNote: '',
    pageLabel: '',
    pdfPageIndex: '',
    section: '',
    figure: '',
    table: '',
    attachToCurrentItem:
      selectedNoteItem.value?.sync_status === 'synced' && !!selectedNoteItem.value.item_id,
  }
  evidenceOpen.value = true
}

async function createEvidence() {
  if (!noteItems.value || !evidenceForm.value.locatorNote.trim()) return
  busy.value = true
  errorMessage.value = ''
  try {
    const result = await paperStore.createEvidence(
      projectId.value,
      paperId.value,
      {
        item_id:
          evidenceForm.value.attachToCurrentItem && selectedNoteItem.value?.item_id
            ? selectedNoteItem.value.item_id
            : null,
        evidence_type: evidenceForm.value.evidenceType.trim(),
        page_label: evidenceForm.value.pageLabel.trim() || null,
        pdf_page_index:
          evidenceForm.value.pdfPageIndex === '' ? null : Number(evidenceForm.value.pdfPageIndex),
        section: evidenceForm.value.section.trim() || null,
        figure: evidenceForm.value.figure.trim() || null,
        table: evidenceForm.value.table.trim() || null,
        locator_note: evidenceForm.value.locatorNote.trim(),
      },
      noteItems.value.note_revision,
      noteItems.value.paper_revision,
    )
    note.value = result.note
    noteDraft.value = result.note.markdown
    savedDraft.value = result.note.markdown
    analysis.value = result.analysis
    syncPaperRevision(result.analysis)
    await reloadNoteItems()
    evidenceOpen.value = false
    successMessage.value = result.item
      ? `${result.evidence.evidence_code} 已加入证据目录并关联当前条目。`
      : `${result.evidence.evidence_code} 已加入论文证据目录。`
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '添加证据失败，请刷新后重试。'
  } finally {
    busy.value = false
  }
}

function openPaperEdit() {
  if (!paper.value) return
  editForm.value = {
    title: paper.value.bibliography.title,
    shortTitle: paper.value.bibliography.short_title,
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
    paperUrl: paper.value.bibliography.urls[0] ?? '',
    codeUrl: paper.value.bibliography.code_url ?? '',
    dataUrl: paper.value.bibliography.data_url ?? '',
    group: paper.value.organization.group ?? '',
    readingStatus: paper.value.organization.reading_status,
    importanceScore:
      paper.value.organization.importance_score == null
        ? ''
        : String(paper.value.organization.importance_score),
    oneSentenceSummary: paper.value.organization.one_sentence_summary,
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
      short_title: editForm.value.shortTitle,
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
      urls: editForm.value.paperUrl.trim() ? [editForm.value.paperUrl.trim()] : [],
      code_url: editForm.value.codeUrl || null,
      data_url: editForm.value.dataUrl || null,
      group: editForm.value.group || null,
      reading_status: editForm.value.readingStatus,
      importance_score:
        editForm.value.importanceScore === '' ? null : Number(editForm.value.importanceScore),
      one_sentence_summary: editForm.value.oneSentenceSummary,
    })
    if (analysis.value) analysis.value.revision = paper.value.revision
    const [freshNote] = await Promise.all([
      paperStore.getNote(projectId.value, paperId.value),
      reloadNoteItems(),
    ])
    note.value = freshNote
    noteDraft.value = freshNote.markdown
    savedDraft.value = freshNote.markdown
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
    background: '研究背景',
    research_problem: '研究问题',
    scenario: '适用场景',
    related_work: '经典文献',
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

function displayItemLabel(item: { kind: AnalysisItem['kind']; display_label?: string | null }) {
  return item.display_label || analysisKindLabel(item.kind)
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

async function importNoteCandidates(candidateIds: string[], removalItemIds: string[]) {
  if (!candidatePreview.value) return
  if (removalItemIds.length) {
    try {
      const impact = await itemLinkStore.inspectImpacts(
        projectId.value,
        removalItemIds.map((itemId) => ({ paper_id: paperId.value, item_id: itemId })),
      )
      if (
        impact.affected_links.length &&
        !window.confirm(
          `确认删除会留下 ${impact.affected_links.length} 条可诊断的悬空关系引用；关系记录不会被静默删除。继续吗？`,
        )
      ) {
        return
      }
    } catch (error: unknown) {
      errorMessage.value =
        error instanceof ApiError ? error.message : '无法检查条目关系影响，候选同步已取消。'
      return
    }
  }
  busy.value = true
  errorMessage.value = ''
  try {
    const result = await paperStore.importNoteCandidates(
      projectId.value,
      paperId.value,
      candidateIds,
      removalItemIds,
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
      const consolidated = result.superseded_item_ids.length
        ? `，合并 ${result.superseded_item_ids.length} 个旧版表格行条目`
        : ''
      const removed = result.deleted_item_ids.length
        ? `，删除 ${result.deleted_item_ids.length} 个旧条目`
        : ''
      successMessage.value = `已导入 ${result.imported_items.length} 条、同步 ${result.synchronized_items.length} 条分析候选${consolidated}${removed}。`
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
        <ListTree :size="17" /> 分析
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
        <p class="overview-summary">
          {{ paper.organization.one_sentence_summary || '尚未填写一句话总结。' }}
        </p>
        <p class="abstract-text">{{ paper.bibliography.abstract_text || '尚未填写摘要。' }}</p>
        <div class="tag-list">
          <span v-for="keyword in paper.bibliography.keywords" :key="keyword">{{ keyword }}</span>
          <span v-if="paper.bibliography.keywords.length === 0">暂无关键词</span>
        </div>
      </div>
    </section>

    <section
      v-else-if="activeTab === 'note'"
      class="note-workspace"
      :class="{ 'note-workspace--items': noteMode === 'items' }"
    >
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
          <button
            type="button"
            :class="{ active: noteMode === 'favorites' }"
            @click="switchNoteMode('favorites')"
          >
            收藏
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
            class="button button--secondary button--compact"
            type="button"
            :disabled="noteState === 'saving'"
            @click="noteDocumentEditing = !noteDocumentEditing"
          >
            <Pencil :size="15" /> {{ noteDocumentEditing ? '返回阅读' : '编辑' }}
          </button>
          <button
            v-if="noteMode === 'document' && noteDocumentEditing"
            class="button button--primary button--compact"
            type="button"
            :disabled="noteState === 'saving' || noteDraft === savedDraft"
            @click="saveNote"
          >
            <Save :size="15" /> 保存
          </button>
          <button
            v-else-if="noteMode === 'items'"
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
        v-if="noteMode === 'document' && noteDocumentEditing"
        v-model="noteDraft"
        class="note-editor"
        aria-label="论文结构化笔记"
        spellcheck="false"
      />
      <MarkdownDocument
        v-else-if="noteMode === 'document'"
        class="note-document-view"
        :markdown="noteDraft"
      />
      <div v-else-if="noteMode === 'items'" class="note-item-mode">
        <aside class="note-item-list">
          <header>
            <div>
              <strong>模板目录</strong>
              <small>{{ noteItems?.slots.length ?? 0 }} 项</small>
            </div>
            <button
              class="button button--secondary button--compact"
              type="button"
              :disabled="busy || !noteItems?.item_templates.length"
              @click="openNoteItemCreate()"
            >
              <Plus :size="14" /> 添加可拓展条目
            </button>
            <button
              v-if="noteItems?.pending_candidate_count"
              class="button button--secondary button--compact"
              type="button"
              :disabled="busy"
              @click="openCandidateReview"
            >
              审阅 {{ noteItems.pending_candidate_count }} 项变化
            </button>
            <div v-if="selectedNoteSlotKeys.length" class="note-item-bulk-actions">
              <button
                class="button button--danger button--compact"
                type="button"
                :disabled="busy || selectedNoteSlotKeys.length === 0"
                @click="deleteNoteSlots(selectedNoteSlotKeys)"
              >
                <Trash2 :size="14" /> 删除 {{ selectedNoteSlotKeys.length || '' }}
              </button>
            </div>
          </header>
          <div v-if="noteSlotGroups.length" class="note-item-list-scroll" tabindex="0">
            <section v-for="group in noteSlotGroups" :key="group.title" class="note-slot-group">
              <h3>{{ group.title }}</h3>
              <div
                v-for="item in group.slots"
                :key="item.slot_key"
                class="note-item-list-row"
                :class="{ active: item.slot_key === selectedNoteItemId }"
              >
                <input
                  v-if="item.can_delete"
                  v-model="selectedNoteSlotKeys"
                  type="checkbox"
                  :value="item.slot_key"
                  :aria-label="`选择 ${item.label}`"
                  :disabled="busy"
                />
                <span v-else class="note-item-row-spacer" aria-hidden="true" />
                <button
                  v-if="item.item_id"
                  class="icon-button note-item-favorite-toggle"
                  type="button"
                  :aria-label="item.is_favorite ? `取消收藏 ${item.label}` : `收藏 ${item.label}`"
                  :title="item.is_favorite ? '取消重点收藏' : '加入重点收藏'"
                  :disabled="busy"
                  @click.stop="updateNoteItemFavorite(item)"
                >
                  <Star :size="15" :fill="item.is_favorite ? 'currentColor' : 'none'" />
                </button>
                <span v-else class="note-item-row-spacer" aria-hidden="true" />
                <button type="button" class="note-item-list-entry" @click="selectNoteItem(item)">
                  <span>
                    <strong>{{ item.template_key }} · {{ item.label }}</strong>
                    <small>{{ item.description }}</small>
                  </span>
                  <span class="note-sync-state" :class="`note-sync-state--${item.sync_status}`">
                    {{
                      item.sync_status === 'synced'
                        ? '已填写'
                        : item.sync_status === 'empty'
                          ? '待填写'
                          : item.sync_status === 'review_required'
                            ? '待同步'
                            : '位置缺失'
                    }}
                  </span>
                </button>
              </div>
            </section>
          </div>
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
                <span class="analysis-kind">{{ displayItemLabel(selectedNoteItem) }}</span>
                <h2>{{ selectedNoteItem.template_key }} · {{ selectedNoteItem.label }}</h2>
                <p>{{ selectedNoteItem.description }}</p>
              </div>
              <div class="note-item-editor-actions">
                <small>
                  {{
                    selectedNoteItem.item_id ? `条目 ID ${selectedNoteItem.item_id}` : '尚未填写'
                  }}
                </small>
                <button
                  v-if="selectedNoteItem.item_id"
                  class="icon-button note-item-favorite-toggle"
                  type="button"
                  :aria-label="
                    selectedNoteItem.is_favorite
                      ? `取消收藏 ${selectedNoteItem.label}`
                      : `收藏 ${selectedNoteItem.label}`
                  "
                  :title="selectedNoteItem.is_favorite ? '取消重点收藏' : '加入重点收藏'"
                  :disabled="busy"
                  @click="updateNoteItemFavorite(selectedNoteItem)"
                >
                  <Star :size="16" :fill="selectedNoteItem.is_favorite ? 'currentColor' : 'none'" />
                </button>
                <button
                  v-if="selectedNoteItem.can_delete"
                  class="icon-button icon-button--danger"
                  type="button"
                  aria-label="删除当前条目"
                  :disabled="busy"
                  @click="deleteNoteSlots([selectedNoteItem.slot_key])"
                >
                  <Trash2 :size="16" />
                </button>
                <button
                  v-if="selectedNoteItem.repeatable_template_key"
                  class="button button--secondary button--compact"
                  type="button"
                  :disabled="busy"
                  @click="openNoteItemCreate(selectedNoteItem.repeatable_template_key)"
                >
                  <Plus :size="14" /> 添加同类条目
                </button>
                <button
                  class="button button--secondary button--compact"
                  type="button"
                  :disabled="
                    busy || selectedNoteItem.sync_status !== 'synced' || !selectedNoteItem.item_id
                  "
                  @click="openEvidenceCreate"
                >
                  <Quote :size="14" /> 添加证据
                </button>
                <button
                  class="button button--secondary button--compact"
                  type="button"
                  :disabled="selectedNoteItem.sync_status === 'missing'"
                  @click="noteItemEditing = !noteItemEditing"
                >
                  <Pencil :size="14" /> {{ noteItemEditing ? '返回阅读' : '编辑' }}
                </button>
              </div>
            </header>
            <div v-if="selectedNoteItemNeedsAttention" class="note-review-required" role="status">
              <strong>
                {{
                  selectedNoteItem.sync_status === 'missing' ? '模板位置缺失' : '已有内容尚未同步'
                }}
              </strong>
              <p v-if="selectedNoteItem.sync_status === 'missing'">
                当前笔记缺少这个模板标题，请在完整文档中恢复模板结构。
              </p>
              <p v-else>编辑并保存此模板槽位，即可在原位置确认内容并同步分析投影。</p>
              <button
                v-if="selectedNoteItem.sync_status === 'missing'"
                class="button button--secondary button--compact"
                type="button"
                @click="openCandidateReview"
              >
                打开差异审阅
              </button>
            </div>
            <textarea
              v-if="noteItemEditing"
              v-model="noteItemDraft"
              class="note-editor note-item-editor"
              aria-label="结构化笔记条目正文"
              spellcheck="false"
              :disabled="selectedNoteItem.sync_status === 'missing'"
            />
            <div v-else-if="!noteItemDraft.trim()" class="note-slot-empty">
              <ListTree :size="24" />
              <p>这个模板项还没有内容。点击“编辑”后直接填写。</p>
            </div>
            <MarkdownDocument v-else class="note-item-document-view" :markdown="noteItemDraft" />
            <footer>
              {{
                noteItemEditing
                  ? '只更新这个模板标题下的正文；标题位置和其他章节不会移动。'
                  : '这是模板原位置的正文预览；空项也会保留在目录中等待填写。'
              }}
            </footer>
          </template>
        </main>
        <aside class="note-evidence-panel">
          <header>
            <div>
              <strong>证据目录</strong>
              <small>{{ noteItems?.evidence_catalog.length ?? 0 }} 条</small>
            </div>
            <button
              class="button button--secondary button--compact"
              type="button"
              :disabled="busy || !noteItems"
              @click="openEvidenceCreate"
            >
              <Plus :size="14" /> 添加证据
            </button>
          </header>
          <p class="note-evidence-intro">
            证据属于整篇论文；从当前条目添加时会同时写入证据编号引用。
          </p>
          <div v-if="noteItems?.evidence_catalog.length" class="note-evidence-list">
            <article
              v-for="evidence in noteItems.evidence_catalog"
              :key="evidence.evidence_id"
              :class="{
                'note-evidence-card--linked':
                  evidence.evidence_id && selectedEvidenceIds.has(evidence.evidence_id),
              }"
            >
              <header>
                <strong>{{ evidence.evidence_code }}</strong>
                <span v-if="evidence.evidence_id && selectedEvidenceIds.has(evidence.evidence_id)">
                  当前条目
                </span>
              </header>
              <p>{{ evidence.locator_note || '未填写证据内容' }}</p>
              <small>{{ evidenceLocation(evidence) }}</small>
            </article>
          </div>
          <div v-else class="note-evidence-empty">
            <Quote :size="22" />
            <p>还没有证据。阅读到关键结论、数据或局限时，可在这里登记。</p>
          </div>
        </aside>
      </div>
      <section v-else class="note-favorites-mode">
        <header>
          <div>
            <strong>重点收藏</strong>
            <small>{{ favoriteNoteItems.length }} 条已确认条目</small>
          </div>
        </header>
        <div v-if="favoriteNoteItems.length === 0" class="note-favorite-empty">
          <Star :size="24" />
          <h2>还没有重点收藏</h2>
          <p>在条目模式中点击星标，将需要反复查看的条目集中到这里。</p>
        </div>
        <div v-else class="note-favorites-grid">
          <article v-for="item in favoriteNoteItems" :key="item.item_id">
            <div class="note-favorite-content">
              <button type="button" class="note-favorite-entry" @click="openFavoriteNoteItem(item)">
                <span class="analysis-kind">{{ displayItemLabel(item) }}</span>
                <strong>{{ item.title }}</strong>
                <small>
                  {{ item.section_title || '未绑定章节' }}
                  <template v-if="item.section_order"> · 第 {{ item.section_order }} 条</template>
                </small>
              </button>
              <MarkdownDocument
                class="note-favorite-document"
                compact
                :markdown="item.markdown || item.title"
              />
            </div>
            <button
              class="icon-button note-item-favorite-toggle"
              type="button"
              :aria-label="`取消收藏 ${item.title}`"
              title="取消重点收藏"
              :disabled="busy"
              @click="updateNoteItemFavorite(item, false)"
            >
              <Star :size="16" fill="currentColor" />
            </button>
          </article>
        </div>
      </section>
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
          <div v-if="displayableEvidence(item.evidence).length" class="evidence-list">
            <span
              v-for="{ item: evidence, label } in displayableEvidence(item.evidence)"
              :key="evidence.evidence_id"
            >
              {{ label }}
            </span>
          </div>
          <div v-if="visibleTags(item.tags).length" class="tag-list">
            <span v-for="tag in visibleTags(item.tags)" :key="tag">{{ tag }}</span>
          </div>
        </article>
      </div>
    </section>

    <section v-else class="analysis-workspace">
      <header class="questions-header">
        <div>
          <h2>可比较的分析</h2>
          <p>
            {{ analysis?.items.length ?? 0 }} 条记录，{{ analysisWithEvidence }} 条已有证据；
            待补证据条目会明确标记。
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
          <button class="button button--primary" type="button" @click="openAnalysisSource()">
            <ListTree :size="17" /> 打开模板目录
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
              <span class="analysis-kind">{{ displayItemLabel(item) }}</span>
              <span
                class="evidence-state"
                :class="{
                  'evidence-state--missing': resolvedEvidence(item).length === 0,
                }"
              >
                {{
                  resolvedEvidence(item).length
                    ? `${resolvedEvidence(item).length} 条证据`
                    : '待补证据'
                }}
              </span>
            </div>
            <div class="table-actions">
              <button
                class="icon-button"
                type="button"
                :aria-label="`打开 ${item.title} 的模板正文`"
                @click="openAnalysisSource(item)"
              >
                <Pencil :size="16" />
              </button>
              <button
                class="icon-button icon-button--danger"
                type="button"
                :aria-label="`删除 ${item.title}`"
                @click="deleteNoteItems([item.item_id])"
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
          <p v-if="item.summary && !isLegacyStructuredSummary(item.summary, item.attributes)">
            {{ displayAnalysisText(item.summary) }}
          </p>
          <div
            v-if="structuredAttributeRows(item.attributes).length"
            class="analysis-structured-content"
          >
            <div
              v-if="isStructuredAttributeTable(item.attributes)"
              class="analysis-table-wrap"
              tabindex="0"
            >
              <table class="analysis-structured-table">
                <thead>
                  <tr>
                    <th>条目</th>
                    <th
                      v-for="column in structuredTableData(item.attributes).columns"
                      :key="column"
                    >
                      {{ column }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in structuredAttributeRows(item.attributes)" :key="row.key">
                    <th scope="row">{{ row.key }}</th>
                    <td
                      v-for="column in structuredTableData(item.attributes).columns"
                      :key="column"
                    >
                      {{ displayAnalysisText(structuredAttributeValue(row, column)) || '—' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <dl v-else class="analysis-attributes">
              <div v-for="row in structuredAttributeRows(item.attributes)" :key="row.key">
                <dt>{{ row.key }}</dt>
                <dd>{{ displayAnalysisText(row.value) }}</dd>
              </div>
            </dl>
          </div>
          <div v-if="displayableEvidence(resolvedEvidence(item)).length" class="evidence-list">
            <span
              v-for="{ item: evidence, label } in displayableEvidence(resolvedEvidence(item))"
              :key="evidence.evidence_id"
            >
              {{ label }}
            </span>
          </div>
          <div v-if="item.writing_uses.length || visibleTags(item.tags).length" class="tag-list">
            <span v-for="use in item.writing_uses" :key="use">{{ use }}</span>
            <span v-for="tag in visibleTags(item.tags)" :key="tag">{{ tag }}</span>
          </div>
        </article>
      </div>
    </section>

    <NoteCandidateReviewDialog
      v-if="candidateReviewOpen && candidatePreview"
      :preview="candidatePreview"
      :busy="busy"
      @close="candidateReviewOpen = false"
      @refresh="refreshNoteCandidates"
      @import="importNoteCandidates"
    />

    <div v-if="noteItemCreateOpen" class="modal-backdrop">
      <section
        class="question-dialog note-item-create-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="note-item-create-title"
      >
        <header>
          <div>
            <p class="eyebrow">可扩展模板项</p>
            <h2 id="note-item-create-title">
              添加{{ selectedCreateTemplate?.label ?? '可拓展条目' }}
            </h2>
          </div>
          <button
            class="icon-button"
            type="button"
            aria-label="关闭"
            @click="noteItemCreateOpen = false"
          >
            <X :size="20" />
          </button>
        </header>
        <div class="question-form">
          <label class="field">
            <span>扩展位置</span>
            <select
              v-model="noteItemCreateForm.templateKey"
              class="select-control"
              @change="changeNoteItemCreateTemplate"
            >
              <option
                v-for="template in noteItems?.item_templates"
                :key="template.template_key"
                :value="template.template_key"
              >
                {{ template.template_key }} · {{ template.label }}
              </option>
            </select>
            <small>
              {{ selectedCreateTemplate?.description }}
            </small>
          </label>
          <label class="field">
            <span>条目名称</span>
            <input
              v-model="noteItemCreateForm.title"
              :placeholder="`例如：${selectedCreateTemplate?.label ?? '独立分析点'}`"
            />
          </label>
          <label class="field">
            <span>条目内容</span>
            <textarea
              v-model="noteItemCreateForm.markdown"
              placeholder="可以先创建，再在条目主编辑区继续填写。"
            />
          </label>
        </div>
        <footer>
          <span>保存后会插入模板对应位置，并立即在主编辑区打开。</span>
          <div>
            <button
              class="button button--secondary"
              type="button"
              @click="noteItemCreateOpen = false"
            >
              取消
            </button>
            <button
              class="button button--primary"
              type="button"
              :disabled="!canCreateNoteItem"
              @click="createNoteItem"
            >
              {{ busy ? '保存中…' : '添加条目' }}
            </button>
          </div>
        </footer>
      </section>
    </div>

    <div v-if="evidenceOpen" class="modal-backdrop">
      <section
        class="question-dialog evidence-create-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-create-title"
      >
        <header>
          <div>
            <p class="eyebrow">论文证据目录</p>
            <h2 id="evidence-create-title">添加证据</h2>
          </div>
          <button class="icon-button" type="button" aria-label="关闭" @click="evidenceOpen = false">
            <X :size="20" />
          </button>
        </header>
        <div class="question-form">
          <label class="field">
            <span>证据内容</span>
            <textarea
              v-model="evidenceForm.locatorNote"
              placeholder="记录关键结论、数据、原文含义或限制。"
            />
          </label>
          <div class="question-form-row">
            <label class="field">
              <span>类型</span>
              <input v-model="evidenceForm.evidenceType" placeholder="背景 / 方法 / 结果 / 局限" />
            </label>
            <label class="field">
              <span>印刷页码</span>
              <input v-model="evidenceForm.pageLabel" placeholder="例如 12" />
            </label>
          </div>
          <div class="question-form-row">
            <label class="field">
              <span>PDF 页序号</span>
              <input v-model="evidenceForm.pdfPageIndex" type="number" min="1" />
            </label>
            <label class="field">
              <span>章节</span>
              <input v-model="evidenceForm.section" placeholder="例如 4.2 Evaluation" />
            </label>
          </div>
          <div class="question-form-row">
            <label class="field"><span>图号</span><input v-model="evidenceForm.figure" /></label>
            <label class="field"><span>表号</span><input v-model="evidenceForm.table" /></label>
          </div>
          <label v-if="selectedNoteItem?.sync_status === 'synced'" class="checkbox-row">
            <input v-model="evidenceForm.attachToCurrentItem" type="checkbox" />
            <span>同时关联当前条目“{{ selectedNoteItem.label }}”</span>
          </label>
        </div>
        <footer>
          <span>系统自动分配 E-xxx 编号，并同步写入完整笔记的证据目录。</span>
          <div>
            <button class="button button--secondary" type="button" @click="evidenceOpen = false">
              取消
            </button>
            <button
              class="button button--primary"
              type="button"
              :disabled="busy || !evidenceForm.locatorNote.trim()"
              @click="createEvidence"
            >
              {{ busy ? '保存中…' : '添加证据' }}
            </button>
          </div>
        </footer>
      </section>
    </div>

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
            <span>论文简称</span>
            <input v-model="editForm.shortTitle" />
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
            <span>阅读状态</span>
            <select v-model="editForm.readingStatus" class="select-control">
              <option value="unread">未读</option>
              <option value="skimmed">粗读</option>
              <option value="deep_read">精读</option>
              <option value="summarized">已总结</option>
              <option value="reported">已汇报</option>
            </select>
          </label>
          <label class="field">
            <span>重要程度</span>
            <select v-model="editForm.importanceScore" class="select-control">
              <option value="">未设置</option>
              <option v-for="score in 5" :key="score" :value="String(score)">{{ score }}</option>
            </select>
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
            <input v-model="editForm.citationCount" type="number" min="0" />
          </label>
          <label class="field"><span>语言</span><input v-model="editForm.language" /></label>
          <label class="field metadata-field--wide">
            <span>关键词</span>
            <input v-model="editForm.keywords" placeholder="用逗号分隔" />
          </label>
          <label class="field metadata-field--wide">
            <span>论文链接</span>
            <input v-model="editForm.paperUrl" type="url" />
          </label>
          <label class="field">
            <span>代码链接</span>
            <input v-model="editForm.codeUrl" type="url" />
          </label>
          <label class="field">
            <span>数据链接</span>
            <input v-model="editForm.dataUrl" type="url" />
          </label>
          <label class="field metadata-field--wide">
            <span>一句话总结</span>
            <textarea
              v-model="editForm.oneSentenceSummary"
              placeholder="本文针对……问题，提出……方法，并在……环境中证明……"
            />
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
