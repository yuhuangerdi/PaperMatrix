<script setup lang="ts">
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Link2,
  Pencil,
  Plus,
  Trash2,
  X,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { ApiError } from '@/api/client'
import { useItemLinkStore } from '@/stores/itemLinks'
import { useProjectStore } from '@/stores/projects'
import type {
  ItemLinksViewDocument,
  ItemLinkType,
  ItemLinkView,
  ProjectAnalysisItem,
  ProjectAnalysisItemCatalog,
} from '@/types/api'

const route = useRoute()
const projectStore = useProjectStore()
const itemLinkStore = useItemLinkStore()
const projectId = computed(() => String(route.params.projectId))
const project = computed(() => projectStore.current)
const document = ref<ItemLinksViewDocument | null>(null)
const catalog = ref<ProjectAnalysisItemCatalog | null>(null)
const loading = ref(true)
const busy = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const editingLinkId = ref<string | null>(null)
const filterReference = ref('')
const form = ref({
  source: '',
  target: '',
  type: 'related_to' as ItemLinkType,
  description: '',
})

const relationTypes: Array<{ value: ItemLinkType; label: string }> = [
  { value: 'addresses', label: '解决' },
  { value: 'partially_addresses', label: '部分解决' },
  { value: 'depends_on', label: '依赖' },
  { value: 'enables', label: '支撑或促成' },
  { value: 'evaluates', label: '验证' },
  { value: 'supports', label: '支持结论' },
  { value: 'contradicts', label: '结论冲突' },
  { value: 'extends', label: '扩展' },
  { value: 'related_to', label: '一般相关' },
]

const groupedItems = computed(() => {
  const groups = new Map<string, ProjectAnalysisItem[]>()
  for (const entry of catalog.value?.items ?? []) {
    groups.set(entry.paper_title, [...(groups.get(entry.paper_title) ?? []), entry])
  }
  return [...groups.entries()].map(([paperTitle, items]) => ({ paperTitle, items }))
})

const visibleLinks = computed(() => {
  if (!filterReference.value) return document.value?.links ?? []
  return (document.value?.links ?? []).filter(
    (view) =>
      referenceKey(view.link.source.paper_id, view.link.source.item_id) === filterReference.value ||
      referenceKey(view.link.target.paper_id, view.link.target.item_id) === filterReference.value,
  )
})

const canSave = computed(
  () =>
    Boolean(form.value.source) &&
    Boolean(form.value.target) &&
    form.value.source !== form.value.target &&
    !busy.value,
)

function referenceKey(paperId: string, itemId: string) {
  return `${paperId}:${itemId}`
}

function parseReference(value: string) {
  const [paper_id, item_id] = value.split(':')
  return { paper_id: paper_id ?? '', item_id: item_id ?? '' }
}

function relationLabel(type: ItemLinkType) {
  return relationTypes.find((item) => item.value === type)?.label ?? type
}

function endpointLabel(view: ItemLinkView['source']) {
  if (view.status === 'missing_paper') return '论文记录已缺失'
  if (view.status === 'missing_item') return `${view.paper_title ?? '论文'} · 条目已缺失`
  return `${view.paper_title} · ${view.item_title}`
}

function itemLocation(view: ItemLinkView['source']) {
  return {
    path: `/projects/${projectId.value}/papers/${view.reference.paper_id}`,
    query: { tab: 'note', mode: 'items', item: view.reference.item_id },
  }
}

async function loadAll() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [projectResult, linksResult, catalogResult] = await Promise.all([
      projectStore.load(projectId.value),
      itemLinkStore.list(projectId.value),
      itemLinkStore.listItems(projectId.value),
    ])
    void projectResult
    document.value = linksResult
    catalog.value = catalogResult
    const queryPaper = typeof route.query.paper === 'string' ? route.query.paper : ''
    const queryItem = typeof route.query.item === 'string' ? route.query.item : ''
    if (queryPaper && queryItem) filterReference.value = referenceKey(queryPaper, queryItem)
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '无法加载条目关系。'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingLinkId.value = null
  form.value = { source: '', target: '', type: 'related_to', description: '' }
}

function editLink(view: ItemLinkView) {
  editingLinkId.value = view.link.link_id
  form.value = {
    source: referenceKey(view.link.source.paper_id, view.link.source.item_id),
    target: referenceKey(view.link.target.paper_id, view.link.target.item_id),
    type: view.link.type,
    description: view.link.description,
  }
}

async function saveLink() {
  if (!document.value || !canSave.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    if (editingLinkId.value) {
      document.value = await itemLinkStore.update(
        projectId.value,
        editingLinkId.value,
        { type: form.value.type, description: form.value.description },
        document.value.document.revision,
      )
      successMessage.value = '关系已更新。'
    } else {
      document.value = await itemLinkStore.create(
        projectId.value,
        {
          source: parseReference(form.value.source),
          target: parseReference(form.value.target),
          type: form.value.type,
          description: form.value.description,
        },
        document.value.document.revision,
      )
      successMessage.value = '关系已建立。'
    }
    resetForm()
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '保存关系失败。'
  } finally {
    busy.value = false
  }
}

async function removeLink(view: ItemLinkView) {
  if (!document.value || !window.confirm('删除这条关系吗？不会删除任何论文条目或 PDF。')) return
  busy.value = true
  try {
    document.value = await itemLinkStore.remove(
      projectId.value,
      view.link.link_id,
      document.value.document.revision,
    )
    successMessage.value = '关系已删除。'
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '删除关系失败。'
  } finally {
    busy.value = false
  }
}

onMounted(() => void loadAll())
</script>

<template>
  <section class="page-heading page-heading--compact">
    <div>
      <RouterLink class="back-link" :to="`/projects/${projectId}`">
        <ArrowLeft :size="16" /> 项目概览
      </RouterLink>
      <p class="eyebrow">条目关系</p>
      <h1>{{ project?.name ?? '研究关系' }}</h1>
      <p>把方法、问题、实验和发现连接成可回到原始笔记的有向证据链。</p>
    </div>
  </section>

  <div v-if="errorMessage" class="form-message form-message--error" role="alert">
    {{ errorMessage }}
  </div>
  <div v-if="successMessage" class="form-message form-message--success" role="status">
    {{ successMessage }}
  </div>

  <section v-if="!loading" class="item-link-layout">
    <form class="item-link-composer" @submit.prevent="saveLink">
      <header>
        <div>
          <p class="eyebrow">{{ editingLinkId ? '编辑关系' : '建立关系' }}</p>
          <h2>来源 → 关系 → 目标</h2>
        </div>
        <button
          v-if="editingLinkId"
          class="icon-button"
          type="button"
          aria-label="取消编辑"
          @click="resetForm"
        >
          <X :size="17" />
        </button>
      </header>
      <label>
        <span>来源条目</span>
        <select v-model="form.source" :disabled="Boolean(editingLinkId)">
          <option value="">选择来源</option>
          <optgroup v-for="group in groupedItems" :key="group.paperTitle" :label="group.paperTitle">
            <option
              v-for="entry in group.items"
              :key="entry.item.item_id"
              :value="referenceKey(entry.paper_id, entry.item.item_id)"
            >
              {{ entry.item.title }}
            </option>
          </optgroup>
        </select>
      </label>
      <label>
        <span>关系类型</span>
        <select v-model="form.type">
          <option v-for="type in relationTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </option>
        </select>
      </label>
      <label>
        <span>目标条目</span>
        <select v-model="form.target" :disabled="Boolean(editingLinkId)">
          <option value="">选择目标</option>
          <optgroup v-for="group in groupedItems" :key="group.paperTitle" :label="group.paperTitle">
            <option
              v-for="entry in group.items"
              :key="entry.item.item_id"
              :value="referenceKey(entry.paper_id, entry.item.item_id)"
            >
              {{ entry.item.title }}
            </option>
          </optgroup>
        </select>
      </label>
      <label class="item-link-description">
        <span>判断说明</span>
        <textarea
          v-model="form.description"
          rows="2"
          maxlength="5000"
          placeholder="说明这条关系成立的范围或依据。"
        />
      </label>
      <button class="button button--primary" type="submit" :disabled="!canSave">
        <Pencil v-if="editingLinkId" :size="16" />
        <Plus v-else :size="16" />
        {{ editingLinkId ? '保存关系' : '建立关系' }}
      </button>
    </form>

    <section class="item-link-register">
      <header class="questions-header">
        <div>
          <h2>关系登记簿</h2>
          <p>
            {{ document?.links.length ?? 0 }} 条关系；
            <span v-if="document?.dangling_count">
              {{ document.dangling_count }} 条包含缺失引用。
            </span>
            <span v-else>全部端点可定位。</span>
          </p>
        </div>
        <label class="compact-filter">
          <span>查看某条目的出向与反向引用</span>
          <select v-model="filterReference">
            <option value="">全部关系</option>
            <optgroup
              v-for="group in groupedItems"
              :key="group.paperTitle"
              :label="group.paperTitle"
            >
              <option
                v-for="entry in group.items"
                :key="entry.item.item_id"
                :value="referenceKey(entry.paper_id, entry.item.item_id)"
              >
                {{ entry.item.title }}
              </option>
            </optgroup>
          </select>
        </label>
      </header>

      <div v-if="visibleLinks.length === 0" class="empty-state empty-state--compact">
        <Link2 :size="27" />
        <h3>还没有匹配的关系</h3>
        <p>选择两个已确认条目，明确记录它们之间的方向和含义。</p>
      </div>
      <div v-else class="item-link-list">
        <article v-for="view in visibleLinks" :key="view.link.link_id" class="item-link-row">
          <RouterLink
            v-if="view.source.status === 'available'"
            class="item-link-endpoint"
            :to="itemLocation(view.source)"
          >
            <small>来源</small><strong>{{ endpointLabel(view.source) }}</strong>
          </RouterLink>
          <div v-else class="item-link-endpoint item-link-endpoint--missing">
            <AlertTriangle :size="15" /><small>来源</small
            ><strong>{{ endpointLabel(view.source) }}</strong>
          </div>
          <div class="item-link-relation">
            <span>{{ relationLabel(view.link.type) }}</span>
            <ArrowRight :size="18" />
          </div>
          <RouterLink
            v-if="view.target.status === 'available'"
            class="item-link-endpoint"
            :to="itemLocation(view.target)"
          >
            <small>目标</small><strong>{{ endpointLabel(view.target) }}</strong>
          </RouterLink>
          <div v-else class="item-link-endpoint item-link-endpoint--missing">
            <AlertTriangle :size="15" /><small>目标</small
            ><strong>{{ endpointLabel(view.target) }}</strong>
          </div>
          <p>{{ view.link.description || '尚未补充关系说明。' }}</p>
          <div class="table-actions">
            <button class="icon-button" type="button" aria-label="编辑关系" @click="editLink(view)">
              <Pencil :size="15" />
            </button>
            <button
              class="icon-button icon-button--danger"
              type="button"
              aria-label="删除关系"
              @click="removeLink(view)"
            >
              <Trash2 :size="15" />
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>
