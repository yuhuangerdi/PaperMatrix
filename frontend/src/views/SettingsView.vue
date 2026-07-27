<script setup lang="ts">
import { CheckCircle2, FolderCheck, LoaderCircle, Save, ShieldCheck } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { useAppStore } from '@/stores/app'
import { useWorkspaceStore } from '@/stores/workspace'
import type { PathValidation } from '@/types/api'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const router = useRouter()
const form = reactive({
  name: '我的研究工作区',
  rootPath: '',
  paperRoots: '',
})
const pathResult = ref<PathValidation | null>(null)
const errorMessage = ref('')
const successMessage = ref('')

const initialized = computed(() => Boolean(workspaceStore.workspace))
const roots = computed(() =>
  form.paperRoots
    .split('\n')
    .map((value) => value.trim())
    .filter(Boolean),
)

async function validateWorkspacePath() {
  errorMessage.value = ''
  pathResult.value = await workspaceStore.validatePath(form.rootPath, 'workspace')
}

async function submit() {
  errorMessage.value = ''
  successMessage.value = ''
  try {
    if (initialized.value) {
      await workspaceStore.update({
        name: form.name,
        allowed_paper_roots: roots.value,
      })
      successMessage.value = '工作区设置已保存。'
    } else {
      await workspaceStore.initialize({
        root_path: form.rootPath,
        name: form.name,
        allowed_paper_roots: roots.value,
      })
      await appStore.checkHealth()
      await router.push('/projects')
    }
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError
        ? `${error.message}${error.action ? ` ${error.action}` : ''}`
        : '保存工作区时发生未知错误。'
  }
}

onMounted(async () => {
  try {
    if (!appStore.health) await appStore.checkHealth()
    if (appStore.health?.workspace_initialized) {
      const workspace = await workspaceStore.load()
      form.name = workspace.name
      form.rootPath = workspace.root_path
      form.paperRoots = workspace.allowed_paper_roots.join('\n')
    }
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof ApiError
        ? `${error.message}${error.action ? ` ${error.action}` : ''}`
        : '无法读取工作区设置。'
  }
})
</script>

<template>
  <section class="page-heading">
    <div>
      <p class="eyebrow">本地配置</p>
      <h1>{{ initialized ? '工作区设置' : '创建你的研究工作区' }}</h1>
      <p>工作区保存 PaperMatrix 元数据；论文根目录仅用于读取你已有的 PDF，不会复制或移动文件。</p>
    </div>
    <span v-if="initialized" class="quiet-badge"><CheckCircle2 :size="15" /> 已初始化</span>
  </section>

  <form class="settings-form" @submit.prevent="submit">
    <section class="form-section" aria-labelledby="workspace-section">
      <div class="form-section-heading">
        <FolderCheck :size="20" />
        <div>
          <h2 id="workspace-section">工作区</h2>
          <p>选择后端所在机器上的可写目录。</p>
        </div>
      </div>

      <label class="field">
        <span>工作区名称</span>
        <input v-model.trim="form.name" required maxlength="120" autocomplete="off" />
      </label>

      <label class="field">
        <span>工作区路径</span>
        <div class="input-action">
          <input
            v-model.trim="form.rootPath"
            required
            :disabled="initialized"
            placeholder="/Users/你的用户名/Documents/PaperMatrixWorkspace"
            autocomplete="off"
          />
          <button
            class="button button--secondary"
            type="button"
            :disabled="initialized || !form.rootPath"
            @click="validateWorkspacePath"
          >
            检查路径
          </button>
        </div>
        <small v-if="initialized">初始化后不能在此直接迁移工作区目录。</small>
        <small v-else-if="pathResult" :class="pathResult.valid ? 'field-success' : 'field-error'">
          {{ pathResult.valid ? `路径可用：${pathResult.normalized_path}` : pathResult.reason }}
        </small>
      </label>
    </section>

    <section class="form-section" aria-labelledby="paper-root-section">
      <div class="form-section-heading">
        <ShieldCheck :size="20" />
        <div>
          <h2 id="paper-root-section">只读论文目录</h2>
          <p>每行填写一个已存在的绝对路径，也可以稍后添加。</p>
        </div>
      </div>
      <label class="field">
        <span>允许读取的根目录</span>
        <textarea
          v-model="form.paperRoots"
          rows="4"
          placeholder="/Users/你的用户名/Documents/Papers"
        ></textarea>
      </label>
    </section>

    <div v-if="errorMessage" class="form-message form-message--error" role="alert">
      {{ errorMessage }}
    </div>
    <div v-if="successMessage" class="form-message form-message--success" role="status">
      {{ successMessage }}
    </div>

    <div class="form-actions">
      <p><ShieldCheck :size="15" /> PDF 始终保持原位且只读</p>
      <button class="button button--primary" type="submit" :disabled="workspaceStore.loading">
        <LoaderCircle v-if="workspaceStore.loading" class="spin" :size="17" />
        <Save v-else :size="17" />
        {{ initialized ? '保存设置' : '创建工作区' }}
      </button>
    </div>
  </form>
</template>
