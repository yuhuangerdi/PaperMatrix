<script setup lang="ts">
import { Archive, ArrowRight, FolderKanban, Plus, Search } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { ApiError } from '@/api/client'
import { usePreferencesStore } from '@/stores/preferences'
import { useProjectStore } from '@/stores/projects'

const projectStore = useProjectStore()
const preferencesStore = usePreferencesStore()
const includeArchived = ref(false)
const query = ref('')
const errorMessage = ref('')

const filteredProjects = computed(() => {
  const normalized = query.value.trim().toLowerCase()
  const matches = normalized
    ? projectStore.items.filter((project) =>
        [project.name, project.topic, ...project.tags].some((value) =>
          value.toLowerCase().includes(normalized),
        ),
      )
    : [...projectStore.items]
  return matches.sort((left, right) => {
    const leftOpened = preferencesStore.lastOpenedAt(left.project_id) ?? ''
    const rightOpened = preferencesStore.lastOpenedAt(right.project_id) ?? ''
    return rightOpened.localeCompare(leftOpened) || right.updated_at.localeCompare(left.updated_at)
  })
})

function recentLabel(projectId: string) {
  const openedAt = preferencesStore.lastOpenedAt(projectId)
  if (!openedAt) return '尚未打开'
  return `最近访问 ${new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(openedAt))}`
}

async function load() {
  errorMessage.value = ''
  try {
    await projectStore.loadList(includeArchived.value)
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '无法加载项目。'
  }
}

watch(includeArchived, () => void load())
onMounted(() => void load())
</script>

<template>
  <section class="page-heading page-heading--compact">
    <div>
      <p class="eyebrow">研究组织</p>
      <h1>项目</h1>
      <p>每个项目拥有独立的论文记录、笔记和分析文件。</p>
    </div>
    <RouterLink class="button button--primary" to="/projects/new">
      <Plus :size="17" />
      新建项目
    </RouterLink>
  </section>

  <div class="list-toolbar">
    <label class="search-field">
      <Search :size="17" />
      <span class="sr-only">搜索项目</span>
      <input v-model="query" type="search" placeholder="搜索名称、主题或标签" />
    </label>
    <label class="checkbox-field">
      <input v-model="includeArchived" type="checkbox" />
      显示已归档
    </label>
  </div>

  <div v-if="errorMessage" class="form-message form-message--error" role="alert">
    {{ errorMessage }}
  </div>

  <section v-if="!projectStore.loading && filteredProjects.length === 0" class="empty-state">
    <div class="empty-icon"><FolderKanban :size="26" /></div>
    <h2>{{ query ? '没有匹配的项目' : '还没有研究项目' }}</h2>
    <p>{{ query ? '尝试更换关键词。' : '创建一个项目，开始组织论文、笔记和研究问题。' }}</p>
    <RouterLink v-if="!query" class="button button--primary" to="/projects/new">
      <Plus :size="17" />
      创建第一个项目
    </RouterLink>
  </section>

  <section v-else class="project-list" aria-label="项目列表">
    <article v-for="project in filteredProjects" :key="project.project_id" class="project-row">
      <div class="project-main">
        <div class="project-title-line">
          <h2>{{ project.name }}</h2>
          <span v-if="project.status === 'archived'" class="status-chip">
            <Archive :size="13" /> 已归档
          </span>
        </div>
        <p>{{ project.topic || '尚未填写研究主题' }}</p>
        <small class="recent-label">{{ recentLabel(project.project_id) }}</small>
        <div v-if="project.tags.length" class="tag-list">
          <span v-for="tag in project.tags" :key="tag">{{ tag }}</span>
        </div>
      </div>
      <dl class="project-stats">
        <div>
          <dt>论文</dt>
          <dd>{{ project.paper_count }}</dd>
        </div>
        <div>
          <dt>精读</dt>
          <dd>{{ project.deep_read_count }}</dd>
        </div>
        <div>
          <dt>已汇报</dt>
          <dd>{{ project.reported_count }}</dd>
        </div>
      </dl>
      <RouterLink
        class="icon-button row-action"
        :to="`/projects/${project.project_id}`"
        :aria-label="`打开项目 ${project.name}`"
      >
        <ArrowRight :size="19" />
      </RouterLink>
    </article>
  </section>
</template>
