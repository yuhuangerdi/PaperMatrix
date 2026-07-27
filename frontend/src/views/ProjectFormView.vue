<script setup lang="ts">
import { ArrowLeft, LoaderCircle, Save } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { useProjectStore } from '@/stores/projects'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const errorMessage = ref('')
const saving = ref(false)
const form = reactive({
  name: '',
  topic: '',
  description: '',
  tags: '',
})

const projectId = computed(() =>
  typeof route.params.projectId === 'string' ? route.params.projectId : null,
)
const editing = computed(() => Boolean(projectId.value))

async function submit() {
  saving.value = true
  errorMessage.value = ''
  const input = {
    name: form.name,
    topic: form.topic,
    description: form.description,
    tags: form.tags
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean),
  }
  try {
    const project =
      editing.value && projectId.value && projectStore.current
        ? await projectStore.update(projectId.value, {
            ...input,
            status: projectStore.current.status,
            expected_revision: projectStore.current.revision,
          })
        : await projectStore.create(input)
    await router.push(`/projects/${project.project_id}`)
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError
        ? `${error.message}${error.action ? ` ${error.action}` : ''}`
        : '保存项目时发生未知错误。'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!projectId.value) return
  try {
    const project = await projectStore.load(projectId.value)
    form.name = project.name
    form.topic = project.topic
    form.description = project.description
    form.tags = project.tags.join(', ')
  } catch (error: unknown) {
    errorMessage.value = error instanceof ApiError ? error.message : '无法读取项目。'
  }
})
</script>

<template>
  <section class="page-heading page-heading--compact">
    <div>
      <RouterLink class="back-link" :to="projectId ? `/projects/${projectId}` : '/projects'">
        <ArrowLeft :size="16" /> 返回
      </RouterLink>
      <p class="eyebrow">项目资料</p>
      <h1>{{ editing ? '编辑项目' : '新建研究项目' }}</h1>
      <p>先记录研究主题与范围，论文可以在下一阶段导入。</p>
    </div>
  </section>

  <form class="project-form" @submit.prevent="submit">
    <label class="field">
      <span>项目名称</span>
      <input v-model.trim="form.name" required maxlength="120" autofocus />
    </label>
    <label class="field">
      <span>研究主题</span>
      <input v-model.trim="form.topic" maxlength="200" placeholder="例如：LLM Agent 安全评估" />
    </label>
    <label class="field">
      <span>项目说明</span>
      <textarea
        v-model="form.description"
        rows="6"
        maxlength="5000"
        placeholder="记录研究范围、目标和当前问题"
      ></textarea>
    </label>
    <label class="field">
      <span>标签</span>
      <input v-model="form.tags" placeholder="用英文逗号分隔，例如：agent, security" />
      <small>标签用于项目列表筛选。</small>
    </label>
    <div v-if="errorMessage" class="form-message form-message--error" role="alert">
      {{ errorMessage }}
    </div>
    <div class="form-actions">
      <span></span>
      <button class="button button--primary" type="submit" :disabled="saving">
        <LoaderCircle v-if="saving" class="spin" :size="17" />
        <Save v-else :size="17" />
        {{ editing ? '保存修改' : '创建项目' }}
      </button>
    </div>
  </form>
</template>
