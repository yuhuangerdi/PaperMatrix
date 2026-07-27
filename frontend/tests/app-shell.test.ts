import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { describe, expect, it } from 'vitest'

import AppShell from '@/components/AppShell.vue'
import { useAppStore } from '@/stores/app'

const TestView = { template: '<div />' }

const mountShellAt = async (path: string) => {
  const pinia = createPinia()
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: TestView },
      { path: '/projects', name: 'projects', component: TestView },
      { path: '/projects/:projectId', name: 'project-detail', component: TestView },
      { path: '/projects/:projectId/papers', name: 'project-papers', component: TestView },
      { path: '/projects/:projectId/papers/:paperId', name: 'paper-detail', component: TestView },
      { path: '/papers', name: 'papers-hub', component: TestView },
      { path: '/settings', name: 'settings', component: TestView },
      { path: '/diagnostics', name: 'diagnostics', component: TestView },
    ],
  })

  await router.push(path)
  await router.isReady()

  const wrapper = mount(AppShell, {
    global: {
      plugins: [pinia, router],
    },
  })

  const appStore = useAppStore()
  appStore.connection = 'online'
  appStore.health = { status: 'ok', version: '0.1.0', workspace_initialized: true }
  await wrapper.vm.$nextTick()

  return wrapper
}

describe('AppShell', () => {
  it('highlights the paper matrix nav item on paper detail routes', async () => {
    const wrapper = await mountShellAt('/projects/demo/papers/paper-1')
    const activeItem = wrapper.find('.nav-item--active')

    expect(activeItem.text()).toContain('论文矩阵')
    expect(activeItem.attributes('aria-current')).toBe('page')
  })

  it('highlights the project nav item on project overview routes', async () => {
    const wrapper = await mountShellAt('/projects/demo')

    expect(wrapper.find('.nav-item--active').text()).toContain('项目')
  })
})
