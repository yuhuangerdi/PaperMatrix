<script setup lang="ts">
import { ArrowRight, FileText } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { ApiError } from '@/api/client'
import { useProjectStore } from '@/stores/projects'

const projectStore = useProjectStore()
const errorMessage = ref('')

onMounted(() => {
  void projectStore.loadList().catch((error: unknown) => {
    errorMessage.value = error instanceof ApiError ? error.message : '无法加载项目。'
  })
})
</script>

<template>
  <section class="page-heading page-heading--compact">
    <div>
      <p class="eyebrow">文献入口</p>
      <h1>论文矩阵</h1>
      <p>论文记录按项目维护。选择一个项目进入检索、导入和来源状态管理。</p>
    </div>
  </section>

  <div v-if="errorMessage" class="form-message form-message--error" role="alert">
    {{ errorMessage }}
  </div>

  <section v-if="!projectStore.loading && projectStore.items.length === 0" class="empty-state">
    <div class="empty-icon"><FileText :size="26" /></div>
    <h2>还没有可用项目</h2>
    <p>先创建项目，再把论文记录组织到明确的研究主题下。</p>
    <RouterLink class="button button--primary" to="/projects/new">新建项目</RouterLink>
  </section>

  <section v-else class="project-list paper-hub-list" aria-label="项目论文入口">
    <article v-for="project in projectStore.items" :key="project.project_id" class="project-row">
      <div class="project-main">
        <div class="project-title-line">
          <h2>{{ project.name }}</h2>
        </div>
        <p>{{ project.topic || '尚未填写研究主题' }}</p>
      </div>
      <dl class="project-stats project-stats--single">
        <div>
          <dt>论文记录</dt>
          <dd>{{ project.paper_count }}</dd>
        </div>
      </dl>
      <RouterLink
        class="icon-button row-action"
        :to="`/projects/${project.project_id}/papers`"
        :aria-label="`打开 ${project.name} 的论文列表`"
      >
        <ArrowRight :size="19" />
      </RouterLink>
    </article>
  </section>
</template>
