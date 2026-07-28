import { createRouter, createWebHistory } from 'vue-router'

import DiagnosticsView from '@/views/DiagnosticsView.vue'
import AnalysisWorkspaceView from '@/views/AnalysisWorkspaceView.vue'
import HomeView from '@/views/HomeView.vue'
import ItemLinksView from '@/views/ItemLinksView.vue'
import PapersHubView from '@/views/PapersHubView.vue'
import PaperDetailView from '@/views/PaperDetailView.vue'
import PapersView from '@/views/PapersView.vue'
import ProjectDetailView from '@/views/ProjectDetailView.vue'
import ProjectFormView from '@/views/ProjectFormView.vue'
import ProjectsView from '@/views/ProjectsView.vue'
import SettingsView from '@/views/SettingsView.vue'
import { useAppStore } from '@/stores/app'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { title: '概览' } },
    {
      path: '/projects',
      name: 'projects',
      component: ProjectsView,
      meta: { title: '项目', requiresWorkspace: true },
    },
    {
      path: '/projects/new',
      name: 'project-new',
      component: ProjectFormView,
      meta: { title: '新建项目', requiresWorkspace: true },
    },
    {
      path: '/projects/:projectId',
      name: 'project-detail',
      component: ProjectDetailView,
      meta: { title: '项目概览', requiresWorkspace: true },
    },
    {
      path: '/projects/:projectId/edit',
      name: 'project-edit',
      component: ProjectFormView,
      meta: { title: '编辑项目', requiresWorkspace: true },
    },
    {
      path: '/papers',
      name: 'papers-hub',
      component: PapersHubView,
      meta: { title: '论文矩阵', requiresWorkspace: true },
    },
    {
      path: '/projects/:projectId/papers',
      name: 'project-papers',
      component: PapersView,
      meta: { title: '论文矩阵', requiresWorkspace: true },
    },
    {
      path: '/projects/:projectId/papers/:paperId',
      name: 'paper-detail',
      component: PaperDetailView,
      meta: { title: '论文详情', requiresWorkspace: true },
    },
    {
      path: '/projects/:projectId/analysis',
      name: 'project-analysis',
      component: AnalysisWorkspaceView,
      meta: { title: '分析工作台', requiresWorkspace: true },
    },
    {
      path: '/projects/:projectId/item-links',
      name: 'project-item-links',
      component: ItemLinksView,
      meta: { title: '条目关系', requiresWorkspace: true },
    },
    { path: '/settings', name: 'settings', component: SettingsView, meta: { title: '设置' } },
    {
      path: '/diagnostics',
      name: 'diagnostics',
      component: DiagnosticsView,
      meta: { title: '诊断' },
    },
  ],
})

router.beforeEach(async (route) => {
  if (!route.meta.requiresWorkspace) return true
  const appStore = useAppStore()
  if (appStore.connection === 'checking') await appStore.checkHealth()
  if (!appStore.health?.workspace_initialized) {
    return { name: 'settings', query: { next: route.fullPath } }
  }
  return true
})

router.afterEach((route) => {
  document.title = `${String(route.meta.title)} · PaperMatrix`
})
