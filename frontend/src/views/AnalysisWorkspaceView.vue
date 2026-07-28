<script setup lang="ts">
import {
  AlertTriangle,
  ArrowLeft,
  ExternalLink,
  Grid3X3,
  ListTree,
  Network,
  Pencil,
  Plus,
  Settings2,
  Trash2,
  X,
} from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { ApiError } from '@/api/client'
import { useAnalysisScopeStore } from '@/stores/analysisScopes'
import { useItemLinkStore } from '@/stores/itemLinks'
import { usePaperStore } from '@/stores/papers'
import {
  type FieldProblemInput,
  type PaperContributionInput,
  type ProblemBoardInput,
  useProblemSynthesisStore,
} from '@/stores/problemSyntheses'
import { useProjectStore } from '@/stores/projects'
import type {
  AnalysisScopeView,
  EvidenceReference,
  FieldProblem,
  Paper,
  PaperContribution,
  ProblemMatrixCell,
  ProblemSynthesesViewDocument,
  ProblemSynthesisMatrix,
  ProjectAnalysisItem,
  ProjectAnalysisItemCatalog,
  ResolutionLevel,
} from '@/types/api'

type EditorKind = 'board' | 'problem' | 'contribution'

const route = useRoute()
const projectStore = useProjectStore()
const scopeStore = useAnalysisScopeStore()
const itemStore = useItemLinkStore()
const paperStore = usePaperStore()
const synthesisStore = useProblemSynthesisStore()

const projectId = computed(() => String(route.params.projectId))
const project = computed(() => projectStore.current)
const syntheses = ref<ProblemSynthesesViewDocument | null>(null)
const matrix = ref<ProblemSynthesisMatrix | null>(null)
const scopes = ref<AnalysisScopeView[]>([])
const catalog = ref<ProjectAnalysisItemCatalog | null>(null)
const selectedBoardId = ref('')
const loading = ref(true)
const busy = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const editor = ref<EditorKind | null>(null)
const editingId = ref<string | null>(null)
const editorHeading = ref<HTMLElement | null>(null)
const activePaper = ref<Paper | null>(null)

const boardForm = ref<ProblemBoardInput>({
  name: '',
  purpose: '',
  scope_id: '',
  problem_ids: [],
  paper_ids: [],
})
const problemForm = ref<FieldProblemInput>({
  name: '',
  definition: '',
  scope_note: '',
  aliases: [],
  tags: [],
  status: 'active',
  source_problem_refs: [],
})
const problemAliases = ref('')
const problemTags = ref('')
const problemSources = ref<string[]>([])
const contributionForm = ref<PaperContributionInput>({
  problem_id: '',
  paper_id: '',
  research_problem_item_id: '',
  method_item_id: null,
  experiment_item_id: null,
  resolution_level: 'unknown',
  rationale: '',
  supporting_evidence_ids: [],
  counter_evidence: '',
  conditions: '',
  user_judgment: '',
})

const resolutionOptions: Array<{ value: ResolutionLevel; label: string; note: string }> = [
  { value: 'resolved', label: '已解决', note: '问题在声明范围内得到解决' },
  { value: 'partially_resolved', label: '部分解决', note: '只覆盖问题的一部分' },
  { value: 'indirectly_mitigated', label: '间接缓解', note: '降低影响但未直接解决' },
  { value: 'not_resolved', label: '尝试但未解决', note: '论文涉及并尝试, 结果仍未解决' },
  { value: 'not_addressed', label: '未涉及', note: '论文没有处理该问题' },
  { value: 'not_applicable', label: '不适用', note: '该问题不适用于论文范围' },
  { value: 'unknown', label: '未知', note: '尚未形成用户判断' },
]

const selectedBoard = computed(() =>
  syntheses.value?.document.boards.find((board) => board.board_id === selectedBoardId.value),
)
const currentScope = computed(() =>
  scopes.value.find((view) => view.scope.scope_id === boardForm.value.scope_id),
)
const researchProblemItems = computed(() =>
  (catalog.value?.items ?? []).filter((entry) => entry.item.kind === 'research_problem'),
)
const activePaperItems = computed(() =>
  (catalog.value?.items ?? []).filter(
    (entry) => entry.paper_id === contributionForm.value.paper_id,
  ),
)
const activeResearchItems = computed(() =>
  activePaperItems.value.filter((entry) => entry.item.kind === 'research_problem'),
)
const activeMethodItems = computed(() =>
  activePaperItems.value.filter((entry) =>
    ['method', 'method_component', 'mechanism', 'innovation'].includes(entry.item.kind),
  ),
)
const activeExperimentItems = computed(() =>
  activePaperItems.value.filter((entry) => ['experiment', 'finding'].includes(entry.item.kind)),
)
const evidenceOptions = computed(
  () => (activePaper.value?.structured_summary.evidence_catalog ?? []) as EvidenceReference[],
)
const canSaveBoard = computed(
  () =>
    boardForm.value.name.trim() &&
    boardForm.value.scope_id &&
    boardForm.value.paper_ids.length > 0 &&
    !busy.value,
)
const canSaveProblem = computed(
  () => problemForm.value.name.trim() && problemForm.value.definition.trim() && !busy.value,
)
const canSaveContribution = computed(
  () =>
    contributionForm.value.problem_id &&
    contributionForm.value.paper_id &&
    contributionForm.value.research_problem_item_id &&
    !busy.value,
)

function referenceKey(entry: Pick<ProjectAnalysisItem, 'paper_id' | 'item'>) {
  return `${entry.paper_id}:${entry.item.item_id}`
}

function parseReference(value: string) {
  const [paper_id = '', item_id = ''] = value.split(':')
  return { paper_id, item_id }
}

function resolutionLabel(level: ResolutionLevel) {
  return resolutionOptions.find((option) => option.value === level)?.label ?? level
}

function paperTitle(paperId: string) {
  return (
    matrix.value?.papers.find((paper) => paper.paper_id === paperId)?.title ??
    paperStore.items.find((paper) => paper.paper_id === paperId)?.title ??
    '论文'
  )
}

function itemLocation(item: { paper_id: string; item_id: string } | null) {
  if (!item) return {}
  return {
    path: `/projects/${projectId.value}/papers/${item.paper_id}`,
    query: { tab: 'note', mode: 'items', item: item.item_id },
  }
}

async function loadAll() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [projectResult, synthesisResult, scopeResult, catalogResult] = await Promise.all([
      projectStore.load(projectId.value),
      synthesisStore.get(projectId.value),
      scopeStore.list(projectId.value),
      itemStore.listItems(projectId.value),
      paperStore.load(projectId.value),
    ])
    void projectResult
    syntheses.value = synthesisResult
    scopes.value = scopeResult.scopes
    catalog.value = catalogResult
    if (
      !selectedBoardId.value ||
      !synthesisResult.document.boards.some((board) => board.board_id === selectedBoardId.value)
    ) {
      selectedBoardId.value = synthesisResult.document.boards[0]?.board_id ?? ''
    }
    await loadMatrix()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '无法加载问题归纳工作台。'
  } finally {
    loading.value = false
  }
}

async function loadMatrix() {
  if (!selectedBoardId.value) {
    matrix.value = null
    return
  }
  matrix.value = await synthesisStore.matrix(projectId.value, selectedBoardId.value)
}

function openEditor(kind: EditorKind) {
  editor.value = kind
  void nextTick(() => editorHeading.value?.focus())
}

function closeEditor() {
  if (busy.value) return
  editor.value = null
  editingId.value = null
  activePaper.value = null
}

function newBoard() {
  editingId.value = null
  const scope = scopes.value[0]
  boardForm.value = {
    name: '',
    purpose: '',
    scope_id: scope?.scope.scope_id ?? '',
    problem_ids: [],
    paper_ids: [...(scope?.available_paper_ids ?? [])],
  }
  openEditor('board')
}

function editBoard() {
  if (!selectedBoard.value) return
  editingId.value = selectedBoard.value.board_id
  boardForm.value = {
    name: selectedBoard.value.name,
    purpose: selectedBoard.value.purpose,
    scope_id: selectedBoard.value.scope_id,
    problem_ids: [...selectedBoard.value.problem_ids],
    paper_ids: [...selectedBoard.value.paper_ids],
  }
  openEditor('board')
}

function newProblem() {
  editingId.value = null
  problemForm.value = {
    name: '',
    definition: '',
    scope_note: '',
    aliases: [],
    tags: [],
    status: 'active',
    source_problem_refs: [],
  }
  problemAliases.value = ''
  problemTags.value = ''
  problemSources.value = []
  openEditor('problem')
}

function editProblem(problem: FieldProblem) {
  editingId.value = problem.problem_id
  problemForm.value = {
    name: problem.name,
    definition: problem.definition,
    scope_note: problem.scope_note,
    aliases: [...problem.aliases],
    tags: [...problem.tags],
    status: problem.status,
    source_problem_refs: [...problem.source_problem_refs],
  }
  problemAliases.value = problem.aliases.join('、')
  problemTags.value = problem.tags.join('、')
  problemSources.value = problem.source_problem_refs.map(
    (reference) => `${reference.paper_id}:${reference.item_id}`,
  )
  openEditor('problem')
}

async function openContribution(problemId: string, paperId: string, cell: ProblemMatrixCell) {
  editingId.value = cell.contribution?.contribution_id ?? null
  const contribution = cell.contribution
  contributionForm.value = contribution
    ? contributionInput(contribution)
    : {
        problem_id: problemId,
        paper_id: paperId,
        research_problem_item_id: '',
        method_item_id: null,
        experiment_item_id: null,
        resolution_level: 'unknown',
        rationale: '',
        supporting_evidence_ids: [],
        counter_evidence: '',
        conditions: '',
        user_judgment: '',
      }
  openEditor('contribution')
  try {
    activePaper.value = await paperStore.get(projectId.value, paperId)
  } catch {
    activePaper.value = null
  }
}

function contributionInput(contribution: PaperContribution): PaperContributionInput {
  return {
    problem_id: contribution.problem_id,
    paper_id: contribution.paper_id,
    research_problem_item_id: contribution.research_problem_item_id,
    method_item_id: contribution.method_item_id,
    experiment_item_id: contribution.experiment_item_id,
    resolution_level: contribution.resolution_level,
    rationale: contribution.rationale,
    supporting_evidence_ids: [...contribution.supporting_evidence_ids],
    counter_evidence: contribution.counter_evidence,
    conditions: contribution.conditions,
    user_judgment: contribution.user_judgment,
  }
}

function updateBoardScope() {
  boardForm.value.paper_ids = [...(currentScope.value?.available_paper_ids ?? [])]
}

async function saveBoard() {
  if (!syntheses.value || !canSaveBoard.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    syntheses.value = editingId.value
      ? await synthesisStore.updateBoard(
          projectId.value,
          editingId.value,
          boardForm.value,
          syntheses.value.document.revision,
        )
      : await synthesisStore.createBoard(
          projectId.value,
          boardForm.value,
          syntheses.value.document.revision,
        )
    selectedBoardId.value =
      editingId.value ??
      syntheses.value.document.boards[syntheses.value.document.boards.length - 1]?.board_id ??
      ''
    successMessage.value = editingId.value ? '归纳板已更新。' : '归纳板已创建。'
    closeEditor()
    await loadMatrix()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '保存归纳板失败。'
  } finally {
    busy.value = false
  }
}

async function saveProblem() {
  if (!syntheses.value || !canSaveProblem.value) return
  busy.value = true
  errorMessage.value = ''
  const input: FieldProblemInput = {
    ...problemForm.value,
    aliases: problemAliases.value
      .split(/[、,，]/)
      .map((value) => value.trim())
      .filter(Boolean),
    tags: problemTags.value
      .split(/[、,，]/)
      .map((value) => value.trim())
      .filter(Boolean),
    source_problem_refs: problemSources.value.map(parseReference),
  }
  try {
    syntheses.value = editingId.value
      ? await synthesisStore.updateProblem(
          projectId.value,
          editingId.value,
          input,
          syntheses.value.document.revision,
        )
      : await synthesisStore.createProblem(
          projectId.value,
          input,
          syntheses.value.document.revision,
        )
    successMessage.value = editingId.value ? '领域问题已更新。' : '领域问题已创建。'
    closeEditor()
    await loadMatrix()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '保存领域问题失败。'
  } finally {
    busy.value = false
  }
}

async function saveContribution() {
  if (!syntheses.value || !canSaveContribution.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    syntheses.value = editingId.value
      ? await synthesisStore.updateContribution(
          projectId.value,
          editingId.value,
          contributionForm.value,
          syntheses.value.document.revision,
        )
      : await synthesisStore.createContribution(
          projectId.value,
          contributionForm.value,
          syntheses.value.document.revision,
        )
    successMessage.value = editingId.value ? '论文贡献已更新。' : '论文贡献已记录。'
    closeEditor()
    await loadMatrix()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '保存论文贡献失败。'
  } finally {
    busy.value = false
  }
}

async function removeBoard() {
  if (
    !syntheses.value ||
    !editingId.value ||
    !window.confirm('删除这张归纳板吗？领域问题和贡献记录会保留。')
  )
    return
  busy.value = true
  try {
    syntheses.value = await synthesisStore.removeBoard(
      projectId.value,
      editingId.value,
      syntheses.value.document.revision,
    )
    selectedBoardId.value = syntheses.value.document.boards[0]?.board_id ?? ''
    successMessage.value = '归纳板已删除。'
    closeEditor()
    await loadMatrix()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '删除归纳板失败。'
  } finally {
    busy.value = false
  }
}

async function removeProblem() {
  if (
    !syntheses.value ||
    !editingId.value ||
    !window.confirm('删除这个领域问题吗？被归纳板或贡献引用时不会删除。')
  )
    return
  busy.value = true
  try {
    syntheses.value = await synthesisStore.removeProblem(
      projectId.value,
      editingId.value,
      syntheses.value.document.revision,
    )
    successMessage.value = '领域问题已删除。'
    closeEditor()
    await loadMatrix()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '删除领域问题失败。'
  } finally {
    busy.value = false
  }
}

async function removeContribution() {
  if (!syntheses.value || !editingId.value || !window.confirm('删除这条论文贡献判断吗？')) return
  busy.value = true
  try {
    syntheses.value = await synthesisStore.removeContribution(
      projectId.value,
      editingId.value,
      syntheses.value.document.revision,
    )
    successMessage.value = '论文贡献已删除。'
    closeEditor()
    await loadMatrix()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '删除论文贡献失败。'
  } finally {
    busy.value = false
  }
}

watch(selectedBoardId, () => {
  if (!loading.value) void loadMatrix()
})

onMounted(() => void loadAll())
</script>

<template>
  <section class="page-heading page-heading--compact analysis-heading">
    <div>
      <RouterLink class="back-link" :to="`/projects/${projectId}`">
        <ArrowLeft :size="16" /> 项目概览
      </RouterLink>
      <p class="eyebrow">分析工作台 · 4B</p>
      <h1>{{ project?.name ?? '跨论文分析' }}</h1>
      <p>把论文自己的研究问题归一到领域问题，再分别判断方法与解决程度。</p>
    </div>
    <div v-if="syntheses" class="analysis-revision">
      <span>归纳版本</span>
      <strong>r{{ syntheses.document.revision }}</strong>
    </div>
  </section>

  <nav class="analysis-tabs" aria-label="分析工作台">
    <RouterLink :to="`/projects/${projectId}/analysis`" aria-current="page">
      <ListTree :size="16" /> 问题归纳
    </RouterLink>
    <span aria-disabled="true">方法与挑战</span>
    <span aria-disabled="true">实验</span>
    <RouterLink :to="`/projects/${projectId}/item-links`"> <Network :size="16" /> 关系 </RouterLink>
    <span aria-disabled="true">主张与空白</span>
    <span aria-disabled="true">综合分析</span>
  </nav>

  <div v-if="errorMessage" class="form-message form-message--error" role="alert">
    {{ errorMessage }}
  </div>
  <div v-if="successMessage" class="form-message form-message--success" role="status">
    {{ successMessage }}
  </div>

  <section v-if="!loading" class="problem-workspace">
    <div class="problem-toolbar">
      <label>
        <span>问题归纳板</span>
        <select v-model="selectedBoardId" :disabled="!syntheses?.document.boards.length">
          <option value="">尚未创建</option>
          <option
            v-for="board in syntheses?.document.boards"
            :key="board.board_id"
            :value="board.board_id"
          >
            {{ board.name }}
          </option>
        </select>
      </label>
      <button
        class="button button--secondary"
        type="button"
        :disabled="!selectedBoard"
        @click="editBoard"
      >
        <Settings2 :size="16" /> 设置归纳板
      </button>
      <button
        class="button button--primary"
        type="button"
        :disabled="!scopes.length"
        @click="newBoard"
      >
        <Plus :size="16" /> 新建归纳板
      </button>
      <button class="button button--secondary" type="button" @click="newProblem">
        <Plus :size="16" /> 定义领域问题
      </button>
    </div>

    <div v-if="!scopes.length" class="analysis-empty">
      <Grid3X3 :size="28" />
      <div>
        <h2>先建立一个分析集合</h2>
        <p>归纳板必须绑定明确的论文集合，避免筛选变化悄悄改变比较范围。</p>
      </div>
      <RouterLink class="button button--primary" :to="`/projects/${projectId}/papers`">
        前往论文矩阵
      </RouterLink>
    </div>

    <template v-else-if="selectedBoard && matrix">
      <section class="problem-board-intro">
        <div>
          <p class="eyebrow">当前归纳范围</p>
          <h2>{{ selectedBoard.name }}</h2>
          <p>{{ selectedBoard.purpose || '尚未填写归纳目的。' }}</p>
        </div>
        <dl>
          <div>
            <dt>领域问题</dt>
            <dd>{{ matrix.rows.length }}</dd>
          </div>
          <div>
            <dt>论文列组</dt>
            <dd>{{ matrix.papers.length }}</dd>
          </div>
          <div>
            <dt>已有判断</dt>
            <dd>
              {{
                matrix.rows.flatMap((row) => row.cells).filter((cell) => cell.contribution).length
              }}
            </dd>
          </div>
        </dl>
      </section>

      <div v-if="matrix.warnings.length" class="matrix-warning" role="status">
        <AlertTriangle :size="17" />
        <span>{{ matrix.warnings.join(' ') }}</span>
      </div>

      <div v-if="!matrix.rows.length" class="analysis-empty analysis-empty--compact">
        <ListTree :size="26" />
        <div>
          <h2>这张归纳板还没有领域问题</h2>
          <p>先定义领域问题，再在归纳板设置中把它加入问题顺序。</p>
        </div>
        <button class="button button--primary" type="button" @click="newProblem">
          定义领域问题
        </button>
      </div>

      <div v-else class="problem-matrix-wrap">
        <table class="problem-matrix">
          <thead>
            <tr>
              <th rowspan="2" scope="col">领域问题</th>
              <th
                v-for="paper in matrix.papers"
                :key="paper.paper_id"
                class="paper-group-heading"
                colspan="2"
                scope="colgroup"
              >
                {{ paper.title }}
              </th>
            </tr>
            <tr>
              <template v-for="paper in matrix.papers" :key="`${paper.paper_id}-subcolumns`">
                <th class="method-heading" scope="col">方法</th>
                <th class="resolution-heading" scope="col">解决程度</th>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in matrix.rows" :key="row.problem.problem_id">
              <th class="problem-name-cell" scope="row">
                <button type="button" @click="editProblem(row.problem)">
                  <strong>{{ row.problem.name }}</strong>
                  <span>{{ row.problem.definition }}</span>
                  <Pencil :size="14" />
                </button>
              </th>
              <template
                v-for="cell in row.cells"
                :key="`${row.problem.problem_id}-${cell.paper_id}`"
              >
                <td class="method-cell">
                  <button
                    type="button"
                    @click="openContribution(row.problem.problem_id, cell.paper_id, cell)"
                  >
                    <span v-if="cell.method?.status === 'available'">{{
                      cell.method.item_title
                    }}</span>
                    <span v-else-if="cell.contribution" class="cell-missing">方法待补或已缺失</span>
                    <span v-else class="cell-empty">记录方法</span>
                  </button>
                </td>
                <td class="resolution-cell">
                  <button
                    type="button"
                    @click="openContribution(row.problem.problem_id, cell.paper_id, cell)"
                  >
                    <span
                      v-if="cell.contribution"
                      class="resolution-chip"
                      :data-level="cell.contribution.resolution_level"
                    >
                      {{ resolutionLabel(cell.contribution.resolution_level) }}
                    </span>
                    <span v-else class="cell-empty">作出判断</span>
                    <small v-if="cell.contribution?.rationale">{{
                      cell.contribution.rationale
                    }}</small>
                  </button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="problem-mobile-list" aria-label="按领域问题展开列表">
        <article v-for="row in matrix.rows" :key="`${row.problem.problem_id}-mobile`">
          <header>
            <div>
              <span>领域问题</span>
              <h2>{{ row.problem.name }}</h2>
              <p>{{ row.problem.definition }}</p>
            </div>
            <button
              class="icon-button"
              type="button"
              aria-label="编辑领域问题"
              @click="editProblem(row.problem)"
            >
              <Pencil :size="16" />
            </button>
          </header>
          <div
            v-for="cell in row.cells"
            :key="`${row.problem.problem_id}-${cell.paper_id}-mobile`"
            class="problem-mobile-paper"
          >
            <h3>{{ paperTitle(cell.paper_id) }}</h3>
            <button
              type="button"
              @click="openContribution(row.problem.problem_id, cell.paper_id, cell)"
            >
              <span>方法</span>
              <strong>{{ cell.method?.item_title ?? '待记录' }}</strong>
            </button>
            <button
              type="button"
              @click="openContribution(row.problem.problem_id, cell.paper_id, cell)"
            >
              <span>解决程度</span>
              <strong>{{
                cell.contribution ? resolutionLabel(cell.contribution.resolution_level) : '待判断'
              }}</strong>
              <small>{{ cell.contribution?.rationale }}</small>
            </button>
          </div>
        </article>
      </div>
    </template>

    <div v-else-if="scopes.length" class="analysis-empty">
      <ListTree :size="28" />
      <div>
        <h2>建立第一张问题归纳板</h2>
        <p>选择分析集合并固定论文顺序，然后加入要跨论文比较的领域问题。</p>
      </div>
      <button class="button button--primary" type="button" @click="newBoard">新建归纳板</button>
    </div>
  </section>

  <div v-if="editor" class="analysis-dialog-backdrop" @mousedown.self="closeEditor">
    <section
      class="analysis-dialog"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="`${editor}-editor-title`"
    >
      <header>
        <div>
          <p class="eyebrow">
            {{ editor === 'board' ? '归纳范围' : editor === 'problem' ? '领域问题' : '贡献检查器' }}
          </p>
          <h2 :id="`${editor}-editor-title`" ref="editorHeading" tabindex="-1">
            {{
              editor === 'board'
                ? editingId
                  ? '设置归纳板'
                  : '新建归纳板'
                : editor === 'problem'
                  ? editingId
                    ? '编辑领域问题'
                    : '定义领域问题'
                  : `${paperTitle(contributionForm.paper_id)}的贡献`
            }}
          </h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="closeEditor">
          <X :size="19" />
        </button>
      </header>

      <form v-if="editor === 'board'" class="analysis-editor-form" @submit.prevent="saveBoard">
        <label>
          <span>归纳板名称</span>
          <input
            v-model="boardForm.name"
            required
            maxlength="120"
            placeholder="例如：失败恢复问题归纳"
          />
        </label>
        <label>
          <span>绑定分析集合</span>
          <select v-model="boardForm.scope_id" required @change="updateBoardScope">
            <option v-for="view in scopes" :key="view.scope.scope_id" :value="view.scope.scope_id">
              {{ view.scope.name }} · {{ view.available_paper_ids.length }} 篇
            </option>
          </select>
          <small>保存的是明确论文 ID；之后筛选变化不会改变本板。</small>
        </label>
        <label>
          <span>归纳目的</span>
          <textarea
            v-model="boardForm.purpose"
            rows="3"
            maxlength="5000"
            placeholder="这张表要回答什么问题？"
          />
        </label>
        <fieldset>
          <legend>领域问题及显示顺序</legend>
          <p v-if="!syntheses?.document.field_problems.length">
            尚未定义领域问题，可先保存空归纳板。
          </p>
          <label
            v-for="problem in syntheses?.document.field_problems"
            :key="problem.problem_id"
            class="check-row"
          >
            <input v-model="boardForm.problem_ids" type="checkbox" :value="problem.problem_id" />
            <span>
              <strong>{{ problem.name }}</strong>
              <small>{{ problem.definition }}</small>
            </span>
          </label>
        </fieldset>
        <footer>
          <button v-if="editingId" class="button button--danger" type="button" @click="removeBoard">
            <Trash2 :size="16" /> 删除
          </button>
          <span />
          <button class="button button--secondary" type="button" @click="closeEditor">取消</button>
          <button class="button button--primary" type="submit" :disabled="!canSaveBoard">
            {{ busy ? '保存中…' : '保存归纳板' }}
          </button>
        </footer>
      </form>

      <form
        v-else-if="editor === 'problem'"
        class="analysis-editor-form"
        @submit.prevent="saveProblem"
      >
        <label>
          <span>领域问题名称</span>
          <input
            v-model="problemForm.name"
            required
            maxlength="300"
            placeholder="用领域语言命名，不照抄单篇标题"
          />
        </label>
        <label>
          <span>定义</span>
          <textarea
            v-model="problemForm.definition"
            required
            rows="4"
            maxlength="20000"
            placeholder="这个问题具体指什么？"
          />
        </label>
        <label>
          <span>范围与边界</span>
          <textarea
            v-model="problemForm.scope_note"
            rows="3"
            maxlength="10000"
            placeholder="纳入和排除哪些场景？"
          />
        </label>
        <div class="analysis-form-grid">
          <label>
            <span>别名</span>
            <input v-model="problemAliases" placeholder="用顿号分隔" />
          </label>
          <label>
            <span>标签</span>
            <input v-model="problemTags" placeholder="用顿号分隔" />
          </label>
        </div>
        <fieldset>
          <legend>映射论文研究问题</legend>
          <p>这里只列出已确认的 research_problem 条目，阅读问题不会混入。</p>
          <label v-for="entry in researchProblemItems" :key="referenceKey(entry)" class="check-row">
            <input v-model="problemSources" type="checkbox" :value="referenceKey(entry)" />
            <span>
              <strong>{{ entry.item.title }}</strong>
              <small>{{ entry.paper_title }}</small>
            </span>
          </label>
        </fieldset>
        <footer>
          <button
            v-if="editingId"
            class="button button--danger"
            type="button"
            @click="removeProblem"
          >
            <Trash2 :size="16" /> 删除
          </button>
          <span />
          <button class="button button--secondary" type="button" @click="closeEditor">取消</button>
          <button class="button button--primary" type="submit" :disabled="!canSaveProblem">
            {{ busy ? '保存中…' : '保存领域问题' }}
          </button>
        </footer>
      </form>

      <form
        v-else
        class="analysis-editor-form contribution-form"
        @submit.prevent="saveContribution"
      >
        <div class="contribution-principle">
          <strong>方法存在 ≠ 问题已解决</strong>
          <span>方法条目和解决程度分别填写，系统不会自动推断。</span>
        </div>
        <label>
          <span>论文对问题的表述</span>
          <select v-model="contributionForm.research_problem_item_id" required>
            <option value="">选择 research_problem 条目</option>
            <option
              v-for="entry in activeResearchItems"
              :key="entry.item.item_id"
              :value="entry.item.item_id"
            >
              {{ entry.item.title }}
            </option>
          </select>
        </label>
        <div class="contribution-columns">
          <section>
            <p class="eyebrow">方法单元格</p>
            <label>
              <span>方法、组件或机制</span>
              <select v-model="contributionForm.method_item_id">
                <option :value="null">尚未关联方法</option>
                <option
                  v-for="entry in activeMethodItems"
                  :key="entry.item.item_id"
                  :value="entry.item.item_id"
                >
                  {{ entry.item.title }}
                </option>
              </select>
            </label>
            <label>
              <span>实验或发现</span>
              <select v-model="contributionForm.experiment_item_id">
                <option :value="null">尚未关联实验</option>
                <option
                  v-for="entry in activeExperimentItems"
                  :key="entry.item.item_id"
                  :value="entry.item.item_id"
                >
                  {{ entry.item.title }}
                </option>
              </select>
            </label>
          </section>
          <section>
            <p class="eyebrow">解决程度单元格</p>
            <label>
              <span>用户判断</span>
              <select v-model="contributionForm.resolution_level">
                <option
                  v-for="option in resolutionOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }} — {{ option.note }}
                </option>
              </select>
            </label>
            <label>
              <span>判断理由</span>
              <textarea
                v-model="contributionForm.rationale"
                rows="4"
                maxlength="20000"
                placeholder="为什么是这个程度？"
              />
            </label>
          </section>
        </div>
        <fieldset v-if="evidenceOptions.length">
          <legend>支持证据</legend>
          <label v-for="evidence in evidenceOptions" :key="evidence.evidence_id" class="check-row">
            <input
              v-model="contributionForm.supporting_evidence_ids"
              type="checkbox"
              :value="evidence.evidence_id"
            />
            <span>
              <strong>{{ evidence.evidence_code ?? '未编号证据' }}</strong>
              <small>{{
                evidence.page_label || evidence.section || evidence.locator_note || '未填写定位'
              }}</small>
            </span>
          </label>
        </fieldset>
        <div v-else class="contribution-no-evidence">
          <AlertTriangle :size="16" /> 这篇论文还没有证据目录，可以先保存判断并稍后补证据。
        </div>
        <label>
          <span>反证或失败案例</span>
          <textarea v-model="contributionForm.counter_evidence" rows="3" maxlength="20000" />
        </label>
        <label>
          <span>成立条件</span>
          <textarea v-model="contributionForm.conditions" rows="3" maxlength="20000" />
        </label>
        <label>
          <span>补充判断</span>
          <textarea
            v-model="contributionForm.user_judgment"
            rows="3"
            maxlength="20000"
            placeholder="记录人工复核后的补充说明。"
          />
        </label>
        <div v-if="editingId" class="source-jumps">
          <RouterLink
            v-if="contributionForm.research_problem_item_id"
            :to="
              itemLocation({
                paper_id: contributionForm.paper_id,
                item_id: contributionForm.research_problem_item_id,
              })
            "
          >
            问题来源 <ExternalLink :size="14" />
          </RouterLink>
          <RouterLink
            v-if="contributionForm.method_item_id"
            :to="
              itemLocation({
                paper_id: contributionForm.paper_id,
                item_id: contributionForm.method_item_id,
              })
            "
          >
            方法来源 <ExternalLink :size="14" />
          </RouterLink>
          <RouterLink
            v-if="contributionForm.experiment_item_id"
            :to="
              itemLocation({
                paper_id: contributionForm.paper_id,
                item_id: contributionForm.experiment_item_id,
              })
            "
          >
            实验来源 <ExternalLink :size="14" />
          </RouterLink>
        </div>
        <footer>
          <button
            v-if="editingId"
            class="button button--danger"
            type="button"
            @click="removeContribution"
          >
            <Trash2 :size="16" /> 删除
          </button>
          <span />
          <button class="button button--secondary" type="button" @click="closeEditor">取消</button>
          <button class="button button--primary" type="submit" :disabled="!canSaveContribution">
            {{ busy ? '保存中…' : '保存论文贡献' }}
          </button>
        </footer>
      </form>
    </section>
  </div>
</template>
