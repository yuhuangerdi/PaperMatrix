import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'

import { useItemLinkStore } from '@/stores/itemLinks'
import { useProjectStore } from '@/stores/projects'
import type {
  AnalysisItem,
  ItemLinksViewDocument,
  Project,
  ProjectAnalysisItemCatalog,
} from '@/types/api'
import ItemLinksView from '@/views/ItemLinksView.vue'

const projectId = '11111111-1111-4111-8111-111111111111'
const sourcePaper = '22222222-2222-4222-8222-222222222222'
const targetPaper = '33333333-3333-4333-8333-333333333333'
const sourceItem = '44444444-4444-4444-8444-444444444444'
const targetItem = '55555555-5555-4555-8555-555555555555'
const now = '2026-07-28T00:00:00Z'

function analysisItem(itemId: string, kind: AnalysisItem['kind'], title: string): AnalysisItem {
  return {
    item_id: itemId,
    kind,
    display_label: null,
    title,
    summary: '',
    section_key: '3.1',
    section_title: '方法',
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
    name: 'Agent Security',
    slug: 'agent-security',
    topic: '',
    description: '',
    tags: [],
    status: 'active',
    created_at: now,
    updated_at: now,
    revision: 1,
  }
}

function catalogFixture(): ProjectAnalysisItemCatalog {
  return {
    project_id: projectId,
    items: [
      {
        paper_id: sourcePaper,
        paper_title: 'Method Paper',
        item: analysisItem(sourceItem, 'method', 'Planning method'),
      },
      {
        paper_id: targetPaper,
        paper_title: 'Problem Paper',
        item: analysisItem(targetItem, 'research_problem', 'Long-horizon failure'),
      },
    ],
  }
}

function linksFixture(): ItemLinksViewDocument {
  const link = {
    link_id: '66666666-6666-4666-8666-666666666666',
    source: { paper_id: sourcePaper, item_id: sourceItem },
    target: { paper_id: targetPaper, item_id: targetItem },
    type: 'addresses' as const,
    description: '方法解决该问题。',
    created_at: now,
    updated_at: now,
  }
  return {
    document: {
      schema_version: 1,
      project_id: projectId,
      revision: 1,
      updated_at: now,
      links: [link],
    },
    links: [
      {
        link,
        source: {
          reference: link.source,
          status: 'available',
          paper_title: 'Method Paper',
          item_title: 'Planning method',
          item_kind: 'method',
        },
        target: {
          reference: link.target,
          status: 'available',
          paper_title: 'Problem Paper',
          item_title: 'Long-horizon failure',
          item_kind: 'research_problem',
        },
      },
    ],
    dangling_count: 0,
  }
}

async function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const projectStore = useProjectStore()
  const itemLinkStore = useItemLinkStore()
  vi.spyOn(projectStore, 'load').mockResolvedValue(projectFixture())
  vi.spyOn(itemLinkStore, 'list').mockResolvedValue(linksFixture())
  vi.spyOn(itemLinkStore, 'listItems').mockResolvedValue(catalogFixture())

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/projects/:projectId/item-links', component: ItemLinksView },
      { path: '/projects/:projectId/papers/:paperId', component: { template: '<div />' } },
    ],
  })
  await router.push(`/projects/${projectId}/item-links`)
  await router.isReady()
  const wrapper = mount(ItemLinksView, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return { wrapper, itemLinkStore }
}

describe('item link workflow', () => {
  it('shows directed endpoints, reverse-reference filter, and stable item links', async () => {
    const { wrapper } = await mountView()

    expect(wrapper.text()).toContain('来源 → 关系 → 目标')
    expect(wrapper.text()).toContain('Method Paper · Planning method')
    expect(wrapper.text()).toContain('解决')
    expect(wrapper.text()).toContain('Problem Paper · Long-horizon failure')
    expect(wrapper.findAll('.item-link-endpoint')).toHaveLength(2)
    expect(wrapper.findAll('.item-link-endpoint')[1]!.attributes('href')).toContain(
      `item=${targetItem}`,
    )

    const filter = wrapper.get<HTMLSelectElement>('.compact-filter select')
    await filter.setValue(`${targetPaper}:${targetItem}`)
    expect(wrapper.findAll('.item-link-row')).toHaveLength(1)
  })

  it('creates a relationship using the current document revision', async () => {
    const { wrapper, itemLinkStore } = await mountView()
    const create = vi.spyOn(itemLinkStore, 'create').mockResolvedValue(linksFixture())
    const selects = wrapper.findAll<HTMLSelectElement>('.item-link-composer select')
    await selects[0]!.setValue(`${sourcePaper}:${sourceItem}`)
    await selects[1]!.setValue('supports')
    await selects[2]!.setValue(`${targetPaper}:${targetItem}`)
    await wrapper.get('.item-link-composer textarea').setValue('证据方向明确。')
    await wrapper.get('.item-link-composer').trigger('submit')
    await flushPromises()

    expect(create).toHaveBeenCalledWith(
      projectId,
      {
        source: { paper_id: sourcePaper, item_id: sourceItem },
        target: { paper_id: targetPaper, item_id: targetItem },
        type: 'supports',
        description: '证据方向明确。',
      },
      1,
    )
  })
})
