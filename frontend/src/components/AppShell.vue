<script setup lang="ts">
import {
  Activity,
  BookOpenText,
  FileSpreadsheet,
  FolderKanban,
  LayoutDashboard,
  Menu,
  Network,
  Search,
  Settings,
  X,
} from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const route = useRoute()
const mobileOpen = ref(false)

const connectionLabel = computed(() => {
  if (appStore.connection === 'online') return '后端已连接'
  if (appStore.connection === 'offline') return '后端未连接'
  return '正在检查'
})

const navItems = computed(() => [
  { label: '概览', to: '/', icon: LayoutDashboard, disabled: false, activeNames: ['home'] },
  {
    label: '项目',
    to: '/projects',
    icon: FolderKanban,
    disabled: !appStore.health?.workspace_initialized,
    activeNames: [
      'projects',
      'project-new',
      'project-detail',
      'project-edit',
      'project-item-links',
    ],
  },
  {
    label: '论文矩阵',
    to: '/papers',
    icon: FileSpreadsheet,
    disabled: !appStore.health?.workspace_initialized,
    activeNames: ['papers-hub', 'project-papers', 'paper-detail'],
  },
  { label: '研究关系', to: '/relations', icon: Network, disabled: true, activeNames: [] },
])

const isNavItemActive = (activeNames: string[]) => activeNames.includes(String(route.name ?? ''))
</script>

<template>
  <a class="skip-link" href="#main-content">跳到主要内容</a>
  <div class="app-shell">
    <aside class="sidebar" :class="{ 'sidebar--open': mobileOpen }" aria-label="主导航">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">PM</div>
        <div>
          <strong>PaperMatrix</strong>
          <span>研究工作台</span>
        </div>
        <button
          class="icon-button mobile-close"
          type="button"
          aria-label="关闭菜单"
          @click="mobileOpen = false"
        >
          <X :size="19" />
        </button>
      </div>

      <nav class="primary-nav">
        <template v-for="item in navItems" :key="item.label">
          <RouterLink
            v-if="!item.disabled"
            :to="item.to"
            class="nav-item"
            :class="{ 'nav-item--active': isNavItemActive(item.activeNames) }"
            :aria-current="isNavItemActive(item.activeNames) ? 'page' : undefined"
            @click="mobileOpen = false"
          >
            <component :is="item.icon" :size="18" />
            <span>{{ item.label }}</span>
          </RouterLink>
          <span v-else class="nav-item nav-item--disabled" :title="`${item.label}将在下一阶段开放`">
            <component :is="item.icon" :size="18" />
            <span>{{ item.label }}</span>
            <span class="soon">稍后</span>
          </span>
        </template>
      </nav>

      <div class="sidebar-footer">
        <RouterLink
          to="/settings"
          class="nav-item"
          :class="{ 'nav-item--active': route.name === 'settings' }"
          :aria-current="route.name === 'settings' ? 'page' : undefined"
          @click="mobileOpen = false"
        >
          <Settings :size="18" />
          <span>设置</span>
        </RouterLink>
        <RouterLink
          to="/diagnostics"
          class="nav-item"
          :class="{ 'nav-item--active': route.name === 'diagnostics' }"
          :aria-current="route.name === 'diagnostics' ? 'page' : undefined"
          @click="mobileOpen = false"
        >
          <Activity :size="18" />
          <span>诊断</span>
        </RouterLink>
        <div class="connection-pill" :class="`connection-pill--${appStore.connection}`">
          <span class="status-dot" aria-hidden="true" />
          <span>{{ connectionLabel }}</span>
        </div>
      </div>
    </aside>

    <div v-if="mobileOpen" class="sidebar-scrim" @click="mobileOpen = false" />

    <section class="workspace">
      <header class="topbar">
        <button
          class="icon-button mobile-menu"
          type="button"
          aria-label="打开菜单"
          @click="mobileOpen = true"
        >
          <Menu :size="20" />
        </button>
        <div class="workspace-context">
          <BookOpenText :size="18" />
          <span>本地工作区</span>
          <span class="context-separator">/</span>
          <strong>{{ route.meta.title }}</strong>
        </div>
        <button class="search-button" type="button" disabled title="搜索将在论文导入后开放">
          <Search :size="17" />
          <span>搜索论文、项目与笔记</span>
          <kbd>⌘ K</kbd>
        </button>
      </header>

      <main id="main-content" class="main-content" tabindex="-1">
        <slot />
      </main>
    </section>
  </div>
</template>
