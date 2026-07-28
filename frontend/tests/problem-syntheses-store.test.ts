import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useProblemSynthesisStore } from '@/stores/problemSyntheses'

describe('problem synthesis store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('sends method and resolution judgment as separate contribution fields', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: () => Promise.resolve({}),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useProblemSynthesisStore()

    await store.createContribution(
      'project-id',
      {
        problem_id: 'problem-id',
        paper_id: 'paper-id',
        research_problem_item_id: 'research-item',
        method_item_id: 'method-item',
        experiment_item_id: null,
        resolution_level: 'not_resolved',
        rationale: '论文尝试了该问题, 但未解决。',
        supporting_evidence_ids: [],
        counter_evidence: '',
        conditions: '',
        user_judgment: '人工判断',
      },
      4,
    )

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(request.method).toBe('POST')
    expect(JSON.parse(String(request.body))).toMatchObject({
      method_item_id: 'method-item',
      resolution_level: 'not_resolved',
      rationale: '论文尝试了该问题, 但未解决。',
      expected_revision: 4,
    })
  })
})
