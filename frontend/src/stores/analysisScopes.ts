import { defineStore } from 'pinia'

import { apiGet, apiRequest } from '@/api/client'
import type { AnalysisScopesViewDocument } from '@/types/api'

export interface AnalysisScopeInput {
  name: string
  purpose: string
  paper_ids: string[]
  source_filter_snapshot: Record<string, string>
}

export const useAnalysisScopeStore = defineStore('analysis-scopes', {
  actions: {
    list(projectId: string) {
      return apiGet<AnalysisScopesViewDocument>(`/projects/${projectId}/analysis-scopes`)
    },
    create(projectId: string, input: AnalysisScopeInput, expectedRevision: number) {
      return apiRequest<AnalysisScopesViewDocument>(`/projects/${projectId}/analysis-scopes`, {
        method: 'POST',
        body: { ...input, expected_revision: expectedRevision },
      })
    },
    update(
      projectId: string,
      scopeId: string,
      input: AnalysisScopeInput,
      expectedRevision: number,
    ) {
      return apiRequest<AnalysisScopesViewDocument>(
        `/projects/${projectId}/analysis-scopes/${scopeId}`,
        {
          method: 'PATCH',
          body: { ...input, expected_revision: expectedRevision },
        },
      )
    },
    remove(projectId: string, scopeId: string, expectedRevision: number) {
      return apiRequest<AnalysisScopesViewDocument>(
        `/projects/${projectId}/analysis-scopes/${scopeId}`,
        {
          method: 'DELETE',
          body: { expected_revision: expectedRevision },
        },
      )
    },
  },
})
