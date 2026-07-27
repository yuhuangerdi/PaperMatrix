<script setup lang="ts">
import {
  ArrowRight,
  Check,
  CircleAlert,
  Database,
  FileLock2,
  FolderCog,
  RefreshCw,
  Server,
} from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const workspaceStatus = computed(() => {
  if (appStore.connection !== 'online') return '等待后端'
  return appStore.health?.workspace_initialized ? '已初始化' : '尚未设置'
})

onMounted(() => {
  void appStore.checkHealth()
})
</script>

<template>
  <section class="page-heading">
    <div>
      <p class="eyebrow">系统概览</p>
      <h1>你的研究资料，留在自己的文件系统里</h1>
      <p>
        PaperMatrix 正在建立本地工作区。论文原文件始终只读，结构化数据保存为可审查的 YAML 与
        Markdown。
      </p>
    </div>
    <button
      class="button button--secondary"
      type="button"
      :disabled="appStore.connection === 'checking'"
      @click="appStore.checkHealth"
    >
      <RefreshCw :size="17" :class="{ spin: appStore.connection === 'checking' }" />
      重新检查
    </button>
  </section>

  <section
    class="system-banner"
    :class="`system-banner--${appStore.connection}`"
    aria-live="polite"
  >
    <div class="banner-icon">
      <Server v-if="appStore.connection !== 'offline'" :size="22" />
      <CircleAlert v-else :size="22" />
    </div>
    <div>
      <strong>
        {{
          appStore.connection === 'online'
            ? '本机后端运行正常'
            : appStore.connection === 'offline'
              ? '暂时无法连接本机后端'
              : '正在检查本机服务'
        }}
      </strong>
      <p v-if="appStore.connection === 'online'">
        API {{ appStore.health?.version }} · 工作区{{ workspaceStatus }}
      </p>
      <p v-else-if="appStore.connection === 'offline'">
        {{ appStore.error?.message }} {{ appStore.error?.action }}
      </p>
      <p v-else>连接 127.0.0.1，通常只需片刻。</p>
    </div>
    <span v-if="appStore.connection === 'online'" class="status-label">
      <Check :size="15" />
      就绪
    </span>
  </section>

  <section class="readiness-section" aria-labelledby="readiness-title">
    <div class="section-heading">
      <div>
        <p class="eyebrow">基础能力</p>
        <h2 id="readiness-title">启动检查</h2>
      </div>
      <span>阶段 0</span>
    </div>

    <div class="readiness-grid">
      <article class="readiness-item">
        <div class="item-icon item-icon--green">
          <FileLock2 :size="20" />
        </div>
        <div>
          <h3>文件写入保护</h3>
          <p>文件锁、revision 检查和原子替换已启用。</p>
        </div>
        <span class="item-state">已配置</span>
      </article>
      <article class="readiness-item">
        <div class="item-icon item-icon--ink">
          <Database :size="20" />
        </div>
        <div>
          <h3>普通文件存储</h3>
          <p>YAML 与 Markdown 是权威数据，不使用数据库。</p>
        </div>
        <span class="item-state">已配置</span>
      </article>
      <article class="readiness-item">
        <div class="item-icon item-icon--amber">
          <FolderCog :size="20" />
        </div>
        <div>
          <h3>工作区设置</h3>
          <p>配置可写工作区与只读论文目录。</p>
        </div>
        <span class="item-state item-state--pending">{{ workspaceStatus }}</span>
      </article>
    </div>
  </section>

  <section class="next-step">
    <div>
      <p class="eyebrow">下一步</p>
      <h2>创建本地研究工作区</h2>
      <p>完成设置后，项目和论文矩阵会在左侧导航中开放。</p>
    </div>
    <RouterLink
      class="button button--primary"
      :to="appStore.health?.workspace_initialized ? '/projects' : '/settings'"
    >
      {{ appStore.health?.workspace_initialized ? '打开项目' : '设置工作区' }}
      <ArrowRight :size="17" />
    </RouterLink>
  </section>
</template>
