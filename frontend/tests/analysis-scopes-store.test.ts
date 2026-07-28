import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAnalysisScopeStore } from '@/stores/analysisScopes'

describe('analysis scope store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('creates a fixed paper scope with its filter snapshot and expected revision', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({
          document: {
            schema_version: 1,
            project_id: 'project-id',
            revision: 1,
            updated_at: '2026-07-28T00:00:00Z',
            scopes: [],
          },
          scopes: [],
        }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useAnalysisScopeStore()

    await store.create(
      'project-id',
      {
        name: '核心方法',
        purpose: '比较方法',
        paper_ids: ['paper-a', 'paper-b'],
        source_filter_snapshot: { q: 'agent', group: '核心', sort: '-year' },
      },
      0,
    )

    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/analysis-scopes')
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(request.method).toBe('POST')
    expect(JSON.parse(String(request.body))).toEqual({
      name: '核心方法',
      purpose: '比较方法',
      paper_ids: ['paper-a', 'paper-b'],
      source_filter_snapshot: { q: 'agent', group: '核心', sort: '-year' },
      expected_revision: 0,
    })
  })
})
