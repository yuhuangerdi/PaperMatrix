import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useMatrixStore } from '@/stores/matrices'

describe('matrix store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads the project matrix for an explicit reproducible scope', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          project_id: 'project-id',
          scope_id: 'scope-id',
          scope_name: '核心',
          rows: [],
          missing_paper_ids: [],
          total: 0,
        }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useMatrixStore()

    await store.literature('project-id', 'scope-id')

    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      '/projects/project-id/matrices/literature?scope_id=scope-id',
    )
  })
})
