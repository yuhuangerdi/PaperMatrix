import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'

import HomeView from '@/views/HomeView.vue'

describe('HomeView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows backend status returned by the health endpoint', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            version: '0.1.0',
            workspace_initialized: false,
          }),
      }),
    )

    const wrapper = mount(HomeView, {
      global: {
        plugins: [createPinia()],
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('本机后端运行正常')
    })
    expect(wrapper.text()).toContain('API 0.1.0')
    expect(wrapper.text()).toContain('尚未设置')
  })

  it('shows a recoverable offline state', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))

    const wrapper = mount(HomeView, {
      global: {
        plugins: [createPinia()],
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
    })
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('暂时无法连接本机后端')
    })
    expect(wrapper.text()).toContain('请启动后端并重试')
  })
})
