<script setup lang="ts">
import {
  Archive,
  ArrowLeft,
  FileText,
  ListTree,
  Network,
  Pencil,
  RotateCcw,
  Trash2,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { usePreferencesStore } from '@/stores/preferences'
import { useProjectStore } from '@/stores/projects'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const preferencesStore = usePreferencesStore()
const errorMessage = ref('')
const projectId = computed(() => String(route.params.projectId))
const project = computed(() => projectStore.current)
const summary = computed(() =>
  projectStore.items.find((item) => item.project_id === projectId.value),
)

async function setArchived(archived: boolean) {
  if (!project.value) return
  errorMessage.value = ''
  try {
    await projectStore.update(projectId.value, {
      name: project.value.name,
      topic: project.value.topic,
      description: project.value.description,
      tags: project.value.tags,
      status: archived ? 'archived' : 'active',
      expected_revision: project.value.revision,
    })
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '更新项目失败。'
  }
}

async function removeProject() {
  if (!project.value) return
  const confirmed = window.confirm(
    `确定删除空项目“${project.value.name}”吗？只会删除 PaperMatrix 项目文件，不会删除任何原始 PDF。`,
  )
  if (!confirmed) return
  try {
    await projectStore.remove(projectId.value)
    await router.push('/projects')
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError
        ? `${error.message}${error.action ? ` ${error.action}` : ''}`
        : '删除项目失败。'
  }
}

onMounted(() => {
  preferencesStore.markProjectOpened(projectId.value)
  void Promise.all([projectStore.load(projectId.value), projectStore.loadList(true)]).catch(
    (error: unknown) => {
      errorMessage.value = error instanceof ApiError ? error.message : '无法读取项目。'
    },
  )
})
</script>

<template>
  <div v-if="errorMessage && !project" class="form-message form-message--error" role="alert">
    {{ errorMessage }}
  </div>
  <template v-if="project">
    <section class="page-heading page-heading--compact">
      <div>
        <RouterLink class="back-link" to="/projects"><ArrowLeft :size="16" /> 所有项目</RouterLink>
        <div class="project-title-line">
          <h1>{{ project.name }}</h1>
          <span v-if="project.status === 'archived'" class="status-chip">
            <Archive :size="13" /> 已归档
          </span>
        </div>
        <p>{{ project.topic || '尚未填写研究主题' }}</p>
      </div>
      <RouterLink class="button button--secondary" :to="`/projects/${projectId}/edit`">
        <Pencil :size="16" /> 编辑
      </RouterLink>
    </section>

    <div v-if="errorMessage" class="form-message form-message--error" role="alert">
      {{ errorMessage }}
    </div>

    <section class="overview-band" aria-label="项目统计">
      <div>
        <strong>{{ summary?.paper_count ?? 0 }}</strong
        ><span>论文</span>
      </div>
      <div>
        <strong>{{ summary?.deep_read_count ?? 0 }}</strong
        ><span>精读</span>
      </div>
      <div>
        <strong>{{ summary?.reported_count ?? 0 }}</strong
        ><span>已汇报</span>
      </div>
      <div>
        <strong>{{ project.revision }}</strong
        ><span>当前版本</span>
      </div>
    </section>

    <section class="project-description">
      <div>
        <p class="eyebrow">项目说明</p>
        <h2>研究范围</h2>
      </div>
      <p>{{ project.description || '尚未填写项目说明。' }}</p>
      <div v-if="project.tags.length" class="tag-list">
        <span v-for="tag in project.tags" :key="tag">{{ tag }}</span>
      </div>
    </section>

    <section class="paper-entry-band">
      <div class="empty-icon"><FileText :size="26" /></div>
      <div>
        <p class="eyebrow">论文工作区</p>
        <h2>{{ summary?.paper_count ? '继续整理论文矩阵' : '添加第一篇论文' }}</h2>
        <p>支持单个 PDF 读取、原路径引用、目录扫描和无 PDF 记录；来源异常会持续标记。</p>
      </div>
      <RouterLink class="button button--primary" :to="`/projects/${projectId}/papers`">
        打开论文矩阵
      </RouterLink>
    </section>

    <section class="paper-entry-band">
      <div class="empty-icon"><ListTree :size="26" /></div>
      <div>
        <p class="eyebrow">分析工作台</p>
        <h2>归纳领域问题与论文贡献</h2>
        <p>建立多个问题归纳板，把每篇论文的方法和解决程度分列比较并回到来源条目。</p>
      </div>
      <RouterLink class="button button--primary" :to="`/projects/${projectId}/analysis`">
        打开分析工作台
      </RouterLink>
    </section>

    <section class="paper-entry-band">
      <div class="empty-icon"><Network :size="26" /></div>
      <div>
        <p class="eyebrow">跨论文分析</p>
        <h2>维护结构化条目关系</h2>
        <p>连接同篇或跨篇的问题、方法、实验和发现，并检查反向引用与缺失目标。</p>
      </div>
      <RouterLink class="button button--secondary" :to="`/projects/${projectId}/item-links`">
        打开条目关系
      </RouterLink>
    </section>

    <section class="danger-zone">
      <div>
        <h2>项目状态</h2>
        <p>归档会隐藏项目但保留所有文件；只有空项目可以删除。</p>
      </div>
      <div class="danger-actions">
        <button
          v-if="project.status === 'active'"
          class="button button--secondary"
          type="button"
          @click="setArchived(true)"
        >
          <Archive :size="16" /> 归档
        </button>
        <button v-else class="button button--secondary" type="button" @click="setArchived(false)">
          <RotateCcw :size="16" /> 恢复
        </button>
        <button class="button button--danger" type="button" @click="removeProject">
          <Trash2 :size="16" /> 删除空项目
        </button>
      </div>
    </section>
  </template>
</template>
