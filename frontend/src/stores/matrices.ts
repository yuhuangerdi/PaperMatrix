import { defineStore } from 'pinia'

import { apiGet } from '@/api/client'
import type { LiteratureMatrix } from '@/types/api'

export const useMatrixStore = defineStore('matrices', {
  actions: {
    literature(projectId: string, scopeId: string | null = null) {
      const query = scopeId ? `?scope_id=${encodeURIComponent(scopeId)}` : ''
      return apiGet<LiteratureMatrix>(`/projects/${projectId}/matrices/literature${query}`)
    },
  },
})
