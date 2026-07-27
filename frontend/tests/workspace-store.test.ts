import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useWorkspaceStore } from '@/stores/workspace'

describe('workspace store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes a workspace through the API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        json: () =>
          Promise.resolve({
            workspace_id: '11111111-1111-4111-8111-111111111111',
            name: 'Research',
            root_path: '/tmp/research',
            allowed_paper_roots: [],
            revision: 1,
          }),
      }),
    )
    const store = useWorkspaceStore()

    await store.initialize({
      root_path: '/tmp/research',
      name: 'Research',
      allowed_paper_roots: [],
    })

    expect(store.workspace?.name).toBe('Research')
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/workspace/initialize',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
