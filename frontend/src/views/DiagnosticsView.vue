<script setup lang="ts">
import { RefreshCw, Server } from 'lucide-vue-next'
import { onMounted } from 'vue'

import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
onMounted(() => void appStore.checkHealth())
</script>

<template>
  <section class="page-heading">
    <div>
      <p class="eyebrow">本机服务</p>
      <h1>诊断</h1>
      <p>这里只显示运行状态和脱敏信息，不显示论文标题、笔记正文或完整文件路径。</p>
    </div>
    <button class="button button--secondary" type="button" @click="appStore.checkHealth">
      <RefreshCw :size="17" />
      刷新
    </button>
  </section>
  <dl class="diagnostics-list">
    <div>
      <dt>连接状态</dt>
      <dd>{{ appStore.connection }}</dd>
    </div>
    <div>
      <dt>API 版本</dt>
      <dd>{{ appStore.health?.version ?? '—' }}</dd>
    </div>
    <div>
      <dt>工作区</dt>
      <dd>{{ appStore.health?.workspace_initialized ? '已初始化' : '未初始化' }}</dd>
    </div>
    <div>
      <dt>服务地址</dt>
      <dd><Server :size="16" /> 127.0.0.1</dd>
    </div>
  </dl>
</template>
