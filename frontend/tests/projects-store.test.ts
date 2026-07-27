import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useProjectStore } from '@/stores/projects'

describe('project store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads project summaries', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            total: 1,
            items: [
              {
                schema_version: 1,
                project_id: '22222222-2222-4222-8222-222222222222',
                name: 'Agent Safety',
                slug: 'agent-safety',
                topic: '',
                description: '',
                tags: [],
                status: 'active',
                created_at: '2026-07-27T00:00:00Z',
                updated_at: '2026-07-27T00:00:00Z',
                revision: 1,
                paper_count: 0,
                deep_read_count: 0,
                reported_count: 0,
              },
            ],
          }),
      }),
    )
    const store = useProjectStore()

    const result = await store.loadList()

    expect(result.total).toBe(1)
    expect(store.items[0]?.name).toBe('Agent Safety')
  })
})
