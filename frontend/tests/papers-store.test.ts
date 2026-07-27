import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { usePaperStore } from '@/stores/papers'

describe('paper store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads a filtered paper list', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          items: [
            {
              paper_id: '33333333-3333-4333-8333-333333333333',
              project_id: '22222222-2222-4222-8222-222222222222',
              title: 'Reliable Agents',
              short_title: '',
              authors: [],
              year: null,
              venue: null,
              topics: [],
              tags: [],
              reading_status: 'unread',
              importance_score: null,
              writing_uses: [],
              source_status: 'unlinked',
              source_filename: 'agent.pdf',
              page_count: 1,
              one_sentence_summary: '',
              updated_at: '2026-07-27T00:00:00Z',
              revision: 1,
            },
          ],
          total: 1,
          page: 1,
          page_size: 200,
        }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = usePaperStore()

    await store.load('project-id', { q: 'agent', sourceStatus: 'unlinked', sort: 'title' })

    expect(store.total).toBe(1)
    expect(store.items[0]?.source_status).toBe('unlinked')
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('source_status=unlinked')
  })

  it('keeps incompatible records visible and removes them separately', async () => {
    const invalidRecord = {
      paper_id: '44444444-4444-4444-8444-444444444444',
      title: 'Legacy incompatible record',
      schema_version: 5,
      reason: '记录内容不符合当前 Paper Schema',
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            items: [],
            invalid_items: [invalidRecord],
            total: 0,
            invalid_total: 1,
            page: 1,
            page_size: 200,
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            source_pdf_untouched: true,
            removed_files: [`${invalidRecord.paper_id}.yaml`],
          }),
      })
    vi.stubGlobal('fetch', fetchMock)
    const store = usePaperStore()

    await store.load('project-id')
    expect(store.invalidItems).toEqual([invalidRecord])
    expect(store.invalidTotal).toBe(1)

    await store.remove('project-id', invalidRecord.paper_id)

    expect(store.invalidItems).toEqual([])
    expect(store.invalidTotal).toBe(0)
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain('confirm_metadata_only=true')
  })

  it('uploads a PDF as multipart form data', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: () => Promise.resolve({ paper_id: 'paper-id' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = usePaperStore()
    const file = new File(['%PDF-1.4'], 'paper.pdf', { type: 'application/pdf' })

    await store.upload('project-id', file)

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(request.body).toBeInstanceOf(FormData)
    expect((request.headers as Record<string, string>)['Content-Type']).toBeUndefined()
  })

  it('saves a note with its expected revision', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          paper_id: 'paper-id',
          markdown: '# Updated',
          revision: 2,
          updated_at: '2026-07-27T00:00:00Z',
        }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = usePaperStore()

    await store.saveNote('project-id', 'paper-id', '# Updated', 1)

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(request.method).toBe('PUT')
    expect(JSON.parse(String(request.body))).toEqual({
      markdown: '# Updated',
      expected_revision: 1,
    })
  })

  it('saves a supplement with an independent expected revision', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          paper_id: 'paper-id',
          markdown: '补充记录',
          revision: 1,
          updated_at: '2026-07-27T00:00:00Z',
        }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = usePaperStore()

    await store.saveSupplement('project-id', 'paper-id', '补充记录', 0)

    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/note/supplement')
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(JSON.parse(String(request.body))).toEqual({
      markdown: '补充记录',
      expected_revision: 0,
    })
  })

  it('creates a question in the current document revision', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({
          schema_version: 1,
          paper_id: 'paper-id',
          revision: 1,
          updated_at: '2026-07-27T00:00:00Z',
          questions: [],
        }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = usePaperStore()

    await store.createQuestion(
      'project-id',
      'paper-id',
      {
        question: 'Which experiment supports the claim?',
        status: 'open',
        answer: '',
        evidence: [],
        tags: ['experiment'],
      },
      0,
    )

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(JSON.parse(String(request.body))).toMatchObject({
      question: 'Which experiment supports the claim?',
      expected_revision: 0,
    })
  })

  it('creates an analysis item in the paper revision', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({
          paper_id: 'paper-id',
          revision: 2,
          updated_at: '2026-07-27T00:00:00Z',
          items: [],
        }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = usePaperStore()

    await store.createAnalysisItem(
      'project-id',
      'paper-id',
      {
        kind: 'method',
        title: 'Evidence-guided planning',
        summary: 'Links decisions to observations.',
        attributes: { architecture: 'planner-executor' },
        evidence_refs: [],
        tags: ['agent'],
        writing_uses: ['METHOD'],
      },
      1,
    )

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(request.method).toBe('POST')
    expect(JSON.parse(String(request.body))).toMatchObject({
      kind: 'method',
      expected_revision: 1,
    })
  })

  it('previews and imports selected note candidates with both revisions', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            paper_id: 'paper-id',
            note_revision: 3,
            paper_revision: 2,
            candidates: [],
            warnings: [],
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            analysis: {
              paper_id: 'paper-id',
              revision: 3,
              updated_at: '2026-07-27T00:00:00Z',
              items: [],
            },
            note: {
              paper_id: 'paper-id',
              markdown: '# Note',
              revision: 3,
              updated_at: '2026-07-27T00:00:00Z',
            },
            imported_items: [],
            synchronized_items: [],
            skipped_candidate_ids: [],
            superseded_item_ids: ['legacy-row-id'],
          }),
      })
    vi.stubGlobal('fetch', fetchMock)
    const store = usePaperStore()

    await store.previewNoteAnalysis('project-id', 'paper-id')
    const result = await store.importNoteCandidates(
      'project-id',
      'paper-id',
      ['candidate-id'],
      3,
      2,
    )

    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ method: 'POST' })
    expect(result.superseded_item_ids).toEqual(['legacy-row-id'])
    const request = fetchMock.mock.calls[1]?.[1] as RequestInit
    expect(JSON.parse(String(request.body))).toEqual({
      candidate_ids: ['candidate-id'],
      expected_note_revision: 3,
      expected_paper_revision: 2,
    })
  })

  it('loads and updates an anchored note item with both revisions and fingerprint', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            paper_id: 'paper-id',
            note_revision: 4,
            paper_revision: 3,
            items: [],
            candidates: [
              {
                candidate_id: 'candidate-id',
                kind: 'method',
                title: '核心思路',
              },
            ],
            warnings: [],
            pending_candidate_count: 1,
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      })
    vi.stubGlobal('fetch', fetchMock)
    const store = usePaperStore()

    const document = await store.getNoteItems('project-id', 'paper-id')
    await store.updateNoteItem(
      'project-id',
      'paper-id',
      'item-id',
      '### 核心思路\n更新后的正文',
      4,
      3,
      'a'.repeat(64),
    )

    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/note/items')
    expect(document.pending_candidate_count).toBe(1)
    expect(document.candidates[0]?.title).toBe('核心思路')
    const request = fetchMock.mock.calls[1]?.[1] as RequestInit
    expect(request.method).toBe('PUT')
    expect(JSON.parse(String(request.body))).toEqual({
      markdown: '### 核心思路\n更新后的正文',
      expected_note_revision: 4,
      expected_paper_revision: 3,
      expected_source_fingerprint: 'a'.repeat(64),
    })
  })
})
