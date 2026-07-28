import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'

import { useAnalysisScopeStore } from '@/stores/analysisScopes'
import { useItemLinkStore } from '@/stores/itemLinks'
import { usePaperStore } from '@/stores/papers'
import { useProblemSynthesisStore } from '@/stores/problemSyntheses'
import { useProjectStore } from '@/stores/projects'
import type {
  AnalysisItem,
  AnalysisScopesViewDocument,
  Paper,
  ProblemSynthesesViewDocument,
  ProblemSynthesisMatrix,
  Project,
  ProjectAnalysisItemCatalog,
} from '@/types/api'
import AnalysisWorkspaceView from '@/views/AnalysisWorkspaceView.vue'

const projectId = '11111111-1111-4111-8111-111111111111'
const paperId = '22222222-2222-4222-8222-222222222222'
const scopeId = '33333333-3333-4333-8333-333333333333'
const boardId = '44444444-4444-4444-8444-444444444444'
const problemId = '55555555-5555-4555-8555-555555555555'
const researchItemId = '66666666-6666-4666-8666-666666666666'
const methodItemId = '77777777-7777-4777-8777-777777777777'
const experimentItemId = '88888888-8888-4888-8888-888888888888'
const contributionId = '99999999-9999-4999-8999-999999999999'
const now = '2026-07-28T00:00:00Z'

function item(itemId: string, kind: AnalysisItem['kind'], title: string): AnalysisItem {
  return {
    item_id: itemId,
    kind,
    display_label: null,
    title,
    summary: '',
    section_key: '3.1',
    section_title: title,
    section_order: 1,
    source_anchor: `item-${itemId}`,
    source_note_revision: 1,
    source_fingerprint: 'a'.repeat(64),
    attributes: {},
    evidence_ids: [],
    tags: [],
    writing_uses: [],
    is_favorite: false,
    created_at: now,
    updated_at: now,
  }
}

function projectFixture(): Project {
  return {
    schema_version: 1,
    project_id: projectId,
    name: 'Agent Reliability',
    slug: 'agent-reliability',
    topic: '',
    description: '',
    tags: [],
    status: 'active',
    created_at: now,
    updated_at: now,
    revision: 1,
  }
}

function scopeFixture(): AnalysisScopesViewDocument {
  const scope = {
    scope_id: scopeId,
    name: '核心集合',
    purpose: '比较恢复方法',
    paper_ids: [paperId],
    source_filter_snapshot: {},
    created_at: now,
    updated_at: now,
  }
  return {
    document: {
      schema_version: 1,
      project_id: projectId,
      revision: 1,
      updated_at: now,
      scopes: [scope],
    },
    scopes: [{ scope, available_paper_ids: [paperId], missing_paper_ids: [] }],
  }
}

function synthesisFixture(): ProblemSynthesesViewDocument {
  const board = {
    board_id: boardId,
    name: '失败恢复归纳',
    purpose: '比较长程任务失败后的恢复能力。',
    scope_id: scopeId,
    problem_ids: [problemId],
    paper_ids: [paperId],
    created_at: now,
    updated_at: now,
  }
  const problem = {
    problem_id: problemId,
    name: '长程任务失败恢复',
    definition: '执行失败后能否恢复状态并继续完成目标。',
    scope_note: '',
    aliases: [],
    tags: [],
    status: 'active' as const,
    source_problem_refs: [{ paper_id: paperId, item_id: researchItemId }],
    created_at: now,
    updated_at: now,
  }
  const contribution = {
    contribution_id: contributionId,
    problem_id: problemId,
    paper_id: paperId,
    research_problem_item_id: researchItemId,
    method_item_id: methodItemId,
    experiment_item_id: experimentItemId,
    resolution_level: 'partially_resolved' as const,
    rationale: '只覆盖工具调用失败。',
    supporting_evidence_ids: [],
    counter_evidence: '',
    conditions: '',
    user_judgment: '',
    created_at: now,
    updated_at: now,
  }
  return {
    document: {
      schema_version: 1,
      project_id: projectId,
      revision: 3,
      updated_at: now,
      boards: [board],
      field_problems: [problem],
      paper_contributions: [contribution],
    },
    boards: [
      {
        board,
        scope_status: 'available',
        missing_problem_ids: [],
        missing_paper_ids: [],
      },
    ],
    field_problems: [
      {
        problem,
        source_items: [
          {
            paper_id: paperId,
            item_id: researchItemId,
            status: 'available',
            paper_title: 'Recovery Agent',
            item_title: 'Failure recovery',
          },
        ],
      },
    ],
    dangling_reference_count: 0,
  }
}

function matrixFixture(): ProblemSynthesisMatrix {
  const synthesis = synthesisFixture()
  const problem = synthesis.document.field_problems[0]!
  const contribution = synthesis.document.paper_contributions[0]!
  return {
    project_id: projectId,
    source_revision: 3,
    board: synthesis.document.boards[0]!,
    papers: [{ paper_id: paperId, title: 'Recovery Agent' }],
    rows: [
      {
        problem,
        cells: [
          {
            paper_id: paperId,
            contribution,
            research_problem: {
              paper_id: paperId,
              item_id: researchItemId,
              status: 'available',
              paper_title: 'Recovery Agent',
              item_title: 'Failure recovery',
            },
            method: {
              paper_id: paperId,
              item_id: methodItemId,
              status: 'available',
              paper_title: 'Recovery Agent',
              item_title: 'Checkpoint rollback',
            },
            experiment: {
              paper_id: paperId,
              item_id: experimentItemId,
              status: 'available',
              paper_title: 'Recovery Agent',
              item_title: 'Tool failure evaluation',
            },
            missing_evidence_ids: [],
          },
        ],
      },
    ],
    warnings: [],
  }
}

function catalogFixture(): ProjectAnalysisItemCatalog {
  return {
    project_id: projectId,
    items: [
      {
        paper_id: paperId,
        paper_title: 'Recovery Agent',
        item: item(researchItemId, 'research_problem', 'Failure recovery'),
      },
      {
        paper_id: paperId,
        paper_title: 'Recovery Agent',
        item: item(methodItemId, 'method', 'Checkpoint rollback'),
      },
      {
        paper_id: paperId,
        paper_title: 'Recovery Agent',
        item: item(experimentItemId, 'experiment', 'Tool failure evaluation'),
      },
    ],
  }
}

async function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  vi.spyOn(useProjectStore(), 'load').mockResolvedValue(projectFixture())
  vi.spyOn(useProblemSynthesisStore(), 'get').mockResolvedValue(synthesisFixture())
  vi.spyOn(useProblemSynthesisStore(), 'matrix').mockResolvedValue(matrixFixture())
  vi.spyOn(useAnalysisScopeStore(), 'list').mockResolvedValue(scopeFixture())
  vi.spyOn(useItemLinkStore(), 'listItems').mockResolvedValue(catalogFixture())
  vi.spyOn(usePaperStore(), 'load').mockResolvedValue({
    items: [],
    invalid_items: [],
    total: 0,
    invalid_total: 0,
    page: 1,
    page_size: 200,
  })
  vi.spyOn(usePaperStore(), 'get').mockResolvedValue({
    structured_summary: { evidence_catalog: [], items: [] },
  } as unknown as Paper)

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/projects/:projectId/analysis', component: AnalysisWorkspaceView },
      { path: '/projects/:projectId', component: { template: '<div />' } },
      { path: '/projects/:projectId/item-links', component: { template: '<div />' } },
      { path: '/projects/:projectId/papers', component: { template: '<div />' } },
      { path: '/projects/:projectId/papers/:paperId', component: { template: '<div />' } },
    ],
  })
  await router.push(`/projects/${projectId}/analysis`)
  await router.isReady()
  const wrapper = mount(AnalysisWorkspaceView, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return wrapper
}

describe('problem synthesis workflow', () => {
  it('renders method and resolution as separate columns with an equivalent mobile list', async () => {
    const wrapper = await mountView()

    expect(wrapper.text()).toContain('失败恢复归纳')
    expect(wrapper.get('.method-heading').text()).toBe('方法')
    expect(wrapper.get('.resolution-heading').text()).toBe('解决程度')
    expect(wrapper.get('.method-cell').text()).toContain('Checkpoint rollback')
    expect(wrapper.get('.resolution-cell').text()).toContain('部分解决')
    expect(wrapper.get('.resolution-cell').text()).toContain('只覆盖工具调用失败')
    expect(wrapper.get('.problem-mobile-list').text()).toContain('Checkpoint rollback')
    expect(wrapper.get('.problem-mobile-list').text()).toContain('部分解决')
  })

  it('opens one contribution inspector without inferring resolution from the method', async () => {
    const wrapper = await mountView()

    await wrapper.get('.method-cell button').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="dialog"]').text()).toContain('方法存在 ≠ 问题已解决')
    expect(wrapper.get('.contribution-columns').text()).toContain('Checkpoint rollback')
    expect(wrapper.get('.contribution-columns').text()).toContain('部分解决')
    expect(wrapper.get('.source-jumps').findAll('a')).toHaveLength(3)
  })
})
