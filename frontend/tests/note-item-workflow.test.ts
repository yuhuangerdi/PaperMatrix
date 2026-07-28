import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { usePaperStore } from '@/stores/papers'
import { useItemLinkStore } from '@/stores/itemLinks'
import type {
  NoteItemDocument,
  NoteItemSlot,
  Paper,
  PaperAnalysisDocument,
  PaperNote,
  QuestionsDocument,
} from '@/types/api'
import PaperDetailView from '@/views/PaperDetailView.vue'

const paperId = '11111111-1111-4111-8111-111111111111'
const projectId = '22222222-2222-4222-8222-222222222222'
const updatedAt = '2026-07-28T00:00:00Z'

function paperFixture(): Paper {
  return {
    schema_version: 11,
    paper_id: paperId,
    project_id: projectId,
    title: 'AgentCyberRange',
    short_title: 'AgentCyberRange',
    authors: ['Example Author'],
    affiliations: [],
    year: 2026,
    venue: null,
    publication_date: null,
    reading_date: null,
    citation_count: null,
    language: 'en',
    keywords: [],
    group: null,
    topics: [],
    tags: [],
    reading_status: 'unread',
    importance_score: null,
    writing_uses: [],
    one_sentence_summary: '',
    updated_at: updatedAt,
    revision: 1,
    source: {
      path: null,
      path_mode: null,
      original_filename: null,
      size_bytes: null,
      modified_at: null,
      fingerprint: null,
      sha256: null,
      page_count: null,
      status: 'unlinked',
    },
    bibliography: {
      title: 'AgentCyberRange',
      short_title: 'AgentCyberRange',
      authors: ['Example Author'],
      affiliations: [],
      year: 2026,
      venue: null,
      publication_date: null,
      citation_count: null,
      language: 'en',
      keywords: [],
      abstract_text: '',
      publication_type: '',
      urls: [],
      code_url: null,
      data_url: null,
    },
    organization: {
      topics: [],
      tags: [],
      group: null,
      reading_date: null,
      reading_status: 'unread',
      importance_score: null,
      writing_uses: [],
      one_sentence_summary: '',
    },
    structured_summary: { items: [] },
    created_at: updatedAt,
  }
}

function fixedSlot(overrides: Partial<NoteItemSlot> = {}): NoteItemSlot {
  return {
    slot_key: '1.1',
    template_key: '1.1',
    kind: 'background',
    label: '研究背景',
    description: '研究方向的背景与发展脉络。',
    section_title: '1. 背景：解决什么问题？为什么重要？',
    markdown: '',
    item_id: null,
    source_fingerprint: null,
    sync_status: 'empty',
    is_favorite: false,
    repeatable: false,
    repeatable_template_key: null,
    can_delete: false,
    ...overrides,
  }
}

function noteItemsFixture(slots: NoteItemSlot[]): NoteItemDocument {
  return {
    paper_id: paperId,
    note_revision: 1,
    paper_revision: 1,
    item_templates: [
      {
        template_key: '2.2',
        chapter: 2,
        kind: 'related_work',
        label: '代表性顶会顶刊文献',
        description: '经典工作的思路、缺点及与本文关系。',
        heading: '2.2 代表性顶会顶刊文献（3–5篇）',
        heading_level: 3,
        repeatable: true,
        child_heading_prefix: '',
        insert_before_heading: null,
        body_template: '- 主要思路：\n- 主要缺点：\n- 与本文关系：',
      },
    ],
    slots,
    evidence_catalog: [
      {
        evidence_id: '33333333-3333-4333-8333-333333333333',
        evidence_code: 'E-001',
        paper_id: paperId,
        page_label: '4',
        pdf_page_index: 5,
        section: '2.1',
        figure: null,
        table: null,
        locator_note: '作者给出问题定义。',
      },
    ],
    items: [],
    candidates: [],
    removals: [],
    warnings: [],
    pending_candidate_count: 0,
  }
}

async function mountDetail(initialItems: NoteItemDocument, query = '') {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = usePaperStore()
  const itemLinkStore = useItemLinkStore()
  const note: PaperNote = {
    paper_id: paperId,
    markdown: '# AgentCyberRange',
    revision: 1,
    updated_at: updatedAt,
  }
  const questions: QuestionsDocument = {
    schema_version: 2,
    paper_id: paperId,
    revision: 1,
    updated_at: updatedAt,
    questions: [],
  }
  const analysis: PaperAnalysisDocument = {
    paper_id: paperId,
    revision: 1,
    updated_at: updatedAt,
    evidence_catalog: initialItems.evidence_catalog,
    items: [],
  }
  vi.spyOn(store, 'get').mockResolvedValue(paperFixture())
  vi.spyOn(store, 'getNote').mockResolvedValue(note)
  vi.spyOn(store, 'getSupplement').mockResolvedValue(note)
  vi.spyOn(store, 'getQuestions').mockResolvedValue(questions)
  vi.spyOn(store, 'getAnalysis').mockResolvedValue(analysis)
  vi.spyOn(store, 'getNoteItems').mockResolvedValue(initialItems)
  vi.spyOn(itemLinkStore, 'inspectImpacts').mockResolvedValue({
    references: [],
    affected_links: [],
  })

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/projects/:projectId/papers/:paperId',
        component: PaperDetailView,
      },
    ],
  })
  await router.push(`/projects/${projectId}/papers/${paperId}${query}`)
  await router.isReady()
  const wrapper = mount(PaperDetailView, {
    global: {
      plugins: [pinia, router],
      stubs: {
        MarkdownDocument: { props: ['markdown'], template: '<div>{{ markdown }}</div>' },
        NoteCandidateReviewDialog: true,
      },
    },
  })
  await flushPromises()
  return { wrapper, store, note, analysis }
}

async function openItemMode(wrapper: Awaited<ReturnType<typeof mountDetail>>['wrapper']) {
  const tabs = wrapper.findAll('.detail-tabs button')
  await tabs.find((button) => button.text().includes('结构化笔记'))!.trigger('click')
  const modes = wrapper.findAll('.note-mode-switch button')
  await modes.find((button) => button.text().includes('条目模式'))!.trigger('click')
}

describe('paper note item workflow', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('shows empty template slots, excludes section 0, and edits the selected slot in place', async () => {
    const related = fixedSlot({
      slot_key: '2.2:related-id',
      template_key: '2.2',
      kind: 'related_work',
      label: 'PentestGPT',
      description: '单篇代表性工作的思路、缺点及与本文关系。',
      section_title: '2. 现有方案分类和经典文献',
      markdown: '- 主要思路：分层推理。',
      item_id: '44444444-4444-4444-8444-444444444444',
      source_fingerprint: 'a'.repeat(64),
      sync_status: 'synced',
      repeatable: true,
      repeatable_template_key: '2.2',
      can_delete: true,
    })
    const { wrapper } = await mountDetail(noteItemsFixture([fixedSlot(), related]))

    await openItemMode(wrapper)

    expect(wrapper.findAll('.note-item-list-row')).toHaveLength(2)
    expect(wrapper.text()).toContain('1.1 · 研究背景')
    expect(wrapper.text()).toContain('待填写')
    expect(wrapper.text()).not.toContain('0. 基本信息')
    expect(wrapper.find('.note-evidence-panel').text()).toContain('E-001')

    const relatedEntry = wrapper
      .findAll('.note-item-list-entry')
      .find((entry) => entry.text().includes('PentestGPT'))!
    await relatedEntry.trigger('click')
    const editButton = wrapper
      .findAll('.note-item-editor-actions button')
      .find((button) => button.text().includes('编辑'))!
    await editButton.trigger('click')

    expect(
      wrapper.get<HTMLTextAreaElement>('textarea[aria-label="结构化笔记条目正文"]').element.value,
    ).toBe('- 主要思路：分层推理。')
    expect(wrapper.get('.note-item-editor-pane h2').text()).toContain('2.2 · PentestGPT')
  })

  it('opens a stable item target from project-level navigation without exposing a file path', async () => {
    const targetItemId = '77777777-7777-4777-8777-777777777777'
    const target = fixedSlot({
      slot_key: `3.1:${targetItemId}`,
      template_key: '3.1',
      kind: 'method',
      label: '规划方法',
      section_title: '3. 本文方法',
      markdown: '使用任务树。',
      item_id: targetItemId,
      source_fingerprint: 'b'.repeat(64),
      sync_status: 'synced',
      can_delete: true,
    })
    const { wrapper } = await mountDetail(
      noteItemsFixture([fixedSlot(), target]),
      `?tab=note&mode=items&item=${targetItemId}`,
    )

    expect(wrapper.get('.detail-tabs button.active').text()).toContain('结构化笔记')
    expect(wrapper.get('.note-mode-switch button.active').text()).toContain('条目模式')
    expect(wrapper.get('.note-item-editor-pane h2').text()).toContain('规划方法')
    expect(wrapper.text()).not.toContain('/notes/')
  })

  it('deletes an empty repeatable slot by slot key while leaving the final placeholder', async () => {
    const seed = fixedSlot({
      slot_key: '4.1',
      template_key: '4.1',
      kind: 'challenge',
      label: '挑战 1',
      section_title: '4. 需要克服的挑战或难点',
      repeatable: true,
      repeatable_template_key: '4',
      can_delete: true,
    })
    const added = fixedSlot({
      slot_key: '4:66666666-6666-4666-8666-666666666666',
      template_key: '4',
      kind: 'challenge',
      label: '状态污染',
      section_title: '4. 需要克服的挑战或难点',
      markdown: '- 为什么困难：上下文持续累积。',
      item_id: '66666666-6666-4666-8666-666666666666',
      source_fingerprint: 'c'.repeat(64),
      sync_status: 'synced',
      repeatable: true,
      repeatable_template_key: '4',
      can_delete: true,
    })
    const initial = noteItemsFixture([seed, added])
    const refreshed = noteItemsFixture([{ ...added, can_delete: false }])
    refreshed.note_revision = 2
    refreshed.paper_revision = 2
    const { wrapper, store, note, analysis } = await mountDetail(initial)
    vi.mocked(store.getNoteItems).mockResolvedValueOnce(refreshed)
    const deleteSpy = vi.spyOn(store, 'deleteNoteItems').mockResolvedValue({
      note: { ...note, revision: 2 },
      analysis: { ...analysis, revision: 2 },
      deleted_item_ids: [],
      deleted_slot_keys: ['4.1'],
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    await openItemMode(wrapper)
    await wrapper.get('button[aria-label="删除当前条目"]').trigger('click')
    await flushPromises()

    expect(deleteSpy).toHaveBeenCalledWith(projectId, paperId, [], ['4.1'], 1, 1)
    expect(wrapper.text()).not.toContain('4.1 · 挑战 1')
    expect(wrapper.text()).toContain('4 · 状态污染')
    expect(wrapper.find('button[aria-label="删除当前条目"]').exists()).toBe(false)
  })

  it('selects a newly added repeatable item after the refreshed document arrives', async () => {
    const initial = noteItemsFixture([fixedSlot()])
    const createdSlot = fixedSlot({
      slot_key: '2.2:new-id',
      template_key: '2.2',
      kind: 'related_work',
      label: 'AutoPentester',
      description: '单篇代表性工作的思路、缺点及与本文关系。',
      section_title: '2. 现有方案分类和经典文献',
      markdown: '- 主要思路：自动规划。',
      item_id: '55555555-5555-4555-8555-555555555555',
      source_fingerprint: 'b'.repeat(64),
      sync_status: 'synced',
      repeatable: true,
      repeatable_template_key: '2.2',
      can_delete: true,
    })
    const refreshed = noteItemsFixture([fixedSlot(), createdSlot])
    refreshed.note_revision = 2
    refreshed.paper_revision = 2
    const { wrapper, store, note, analysis } = await mountDetail(initial)
    vi.mocked(store.getNoteItems).mockResolvedValueOnce(refreshed)
    vi.spyOn(store, 'createNoteItem').mockResolvedValue({
      note: { ...note, revision: 2 },
      analysis: { ...analysis, revision: 2 },
      item: {
        item_id: createdSlot.item_id!,
        kind: 'related_work',
        display_label: '代表性文献',
        title: 'AutoPentester',
        summary: '自动规划。',
        section_key: 'section-2',
        section_title: createdSlot.section_title,
        section_order: 4,
        source_anchor: `papermatrix:item:${createdSlot.item_id}`,
        source_note_revision: 2,
        source_fingerprint: createdSlot.source_fingerprint,
        attributes: {},
        evidence_ids: [],
        tags: [],
        writing_uses: [],
        is_favorite: false,
        created_at: updatedAt,
        updated_at: updatedAt,
      },
    })

    await openItemMode(wrapper)
    const addButton = wrapper
      .findAll('.note-item-list > header button')
      .find((button) => button.text().includes('添加'))!
    await addButton.trigger('click')
    const dialog = wrapper.get('.note-item-create-dialog')
    await dialog.get('input').setValue('AutoPentester')
    await dialog.get('textarea').setValue('- 主要思路：自动规划。')
    await dialog.find('.button--primary').trigger('click')
    await flushPromises()

    expect(store.createNoteItem).toHaveBeenCalledWith(
      projectId,
      paperId,
      {
        template_key: '2.2',
        title: 'AutoPentester',
        markdown: '- 主要思路：自动规划。',
      },
      1,
      1,
    )
    expect(wrapper.get('.note-item-editor-pane h2').text()).toContain('2.2 · AutoPentester')
    expect(wrapper.find('.note-item-create-dialog').exists()).toBe(false)
  })

  it('offers literature, challenge, and innovation as distinct repeatable groups', async () => {
    const items = noteItemsFixture([fixedSlot()])
    items.item_templates = [
      items.item_templates[0]!,
      {
        template_key: '4',
        chapter: 4,
        kind: 'challenge',
        label: '挑战',
        description: '每个挑战保留完整分析字段。',
        heading: '4. 需要克服的挑战或难点',
        heading_level: 2,
        repeatable: true,
        child_heading_prefix: '挑战',
        insert_before_heading: null,
        body_template:
          '- 为什么困难：\n- 现有方案为什么解决不好：\n- 本文如何处理：\n- 是否真正解决：',
      },
      {
        template_key: '5.innovation',
        chapter: 5,
        kind: 'innovation',
        label: '创新点',
        description: '每个创新点保留完整分析字段。',
        heading: '5. 大致流程和创新点',
        heading_level: 2,
        repeatable: true,
        child_heading_prefix: '创新点',
        insert_before_heading: '5.5 附加贡献',
        body_template:
          '- 针对的挑战：\n- 做了什么：\n- 与已有工作的区别：\n- 为什么有效：\n- 哪个实验验证：',
      },
    ]
    const { wrapper } = await mountDetail(items)

    await openItemMode(wrapper)
    const addButton = wrapper
      .findAll('.note-item-list > header button')
      .find((button) => button.text().includes('添加可拓展条目'))!
    await addButton.trigger('click')

    const dialog = wrapper.get('.note-item-create-dialog')
    expect(dialog.findAll('option').map((option) => option.text())).toEqual([
      '2.2 · 代表性顶会顶刊文献',
      '4 · 挑战',
      '5.innovation · 创新点',
    ])
    await dialog.get('select').setValue('4')
    expect(dialog.get<HTMLTextAreaElement>('textarea').element.value).toContain('为什么困难')
    expect(dialog.get('h2').text()).toBe('添加挑战')
  })

  it('adds evidence from the separate evidence rail and links the selected saved item', async () => {
    const related = fixedSlot({
      slot_key: '2.2:related-id',
      template_key: '2.2',
      kind: 'related_work',
      label: 'PentestGPT',
      description: '单篇代表性工作的思路、缺点及与本文关系。',
      section_title: '2. 现有方案分类和经典文献',
      markdown: '- 主要思路：分层推理。',
      item_id: '44444444-4444-4444-8444-444444444444',
      source_fingerprint: 'a'.repeat(64),
      sync_status: 'synced',
      repeatable: true,
      repeatable_template_key: '2.2',
      can_delete: true,
    })
    const items = noteItemsFixture([fixedSlot(), related])
    const { wrapper, store, note, analysis } = await mountDetail(items)
    vi.spyOn(store, 'createEvidence').mockResolvedValue({
      note: { ...note, revision: 2 },
      analysis: { ...analysis, revision: 2 },
      evidence: {
        evidence_id: '66666666-6666-4666-8666-666666666666',
        evidence_code: 'E-002',
        paper_id: paperId,
        page_label: '8',
        pdf_page_index: null,
        section: null,
        figure: null,
        table: 'Table 2',
        locator_note: '成功率相对基线提升 18%。',
      },
      item: null,
    })

    await openItemMode(wrapper)
    const relatedEntry = wrapper
      .findAll('.note-item-list-entry')
      .find((entry) => entry.text().includes('PentestGPT'))!
    await relatedEntry.trigger('click')
    await wrapper.get('.note-evidence-panel > header button').trigger('click')

    const dialog = wrapper.get('.evidence-create-dialog')
    await dialog.get('textarea').setValue('成功率相对基线提升 18%。')
    const fields = dialog.findAll('input')
    await fields.find((input) => input.attributes('placeholder') === '例如 12')!.setValue('8')
    await fields[5]!.setValue('Table 2')
    await dialog.find('.button--primary').trigger('click')
    await flushPromises()

    expect(store.createEvidence).toHaveBeenCalledWith(
      projectId,
      paperId,
      {
        item_id: related.item_id,
        evidence_type: '',
        page_label: '8',
        pdf_page_index: null,
        section: null,
        figure: null,
        table: 'Table 2',
        locator_note: '成功率相对基线提升 18%。',
      },
      1,
      1,
    )
    expect(wrapper.find('.evidence-create-dialog').exists()).toBe(false)
  })
})
