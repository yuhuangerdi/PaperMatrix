import { defineStore } from 'pinia'

import { apiGet, apiRequest } from '@/api/client'
import type {
  ItemLinkImpact,
  ItemLinksViewDocument,
  ItemLinkType,
  ItemReference,
  ProjectAnalysisItemCatalog,
} from '@/types/api'

export const useItemLinkStore = defineStore('item-links', {
  actions: {
    list(projectId: string) {
      return apiGet<ItemLinksViewDocument>(`/projects/${projectId}/item-links`)
    },
    listItems(projectId: string) {
      return apiGet<ProjectAnalysisItemCatalog>(`/projects/${projectId}/analysis/items`)
    },
    create(
      projectId: string,
      input: {
        source: ItemReference
        target: ItemReference
        type: ItemLinkType
        description: string
      },
      expectedRevision: number,
    ) {
      return apiRequest<ItemLinksViewDocument>(`/projects/${projectId}/item-links`, {
        method: 'POST',
        body: { ...input, expected_revision: expectedRevision },
      })
    },
    update(
      projectId: string,
      linkId: string,
      input: { type: ItemLinkType; description: string },
      expectedRevision: number,
    ) {
      return apiRequest<ItemLinksViewDocument>(`/projects/${projectId}/item-links/${linkId}`, {
        method: 'PATCH',
        body: { ...input, expected_revision: expectedRevision },
      })
    },
    remove(projectId: string, linkId: string, expectedRevision: number) {
      return apiRequest<ItemLinksViewDocument>(`/projects/${projectId}/item-links/${linkId}`, {
        method: 'DELETE',
        body: { expected_revision: expectedRevision },
      })
    },
    inspectImpacts(projectId: string, references: ItemReference[]) {
      return apiRequest<ItemLinkImpact>(`/projects/${projectId}/item-links/impacts`, {
        method: 'POST',
        body: { references },
      })
    },
  },
})
