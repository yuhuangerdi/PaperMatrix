import { defineStore } from 'pinia'

import { apiGet, apiRequest } from '@/api/client'
import type { PathValidation, Workspace } from '@/types/api'

export interface WorkspaceInput {
  root_path: string
  name: string
  allowed_paper_roots: string[]
}

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    workspace: null as Workspace | null,
    loading: false,
  }),
  actions: {
    async load() {
      this.loading = true
      try {
        this.workspace = await apiGet<Workspace>('/workspace')
        return this.workspace
      } finally {
        this.loading = false
      }
    },
    async initialize(input: WorkspaceInput) {
      this.loading = true
      try {
        this.workspace = await apiRequest<Workspace>('/workspace/initialize', {
          method: 'POST',
          body: input,
          timeoutMs: 10_000,
        })
        return this.workspace
      } finally {
        this.loading = false
      }
    },
    async update(input: Omit<WorkspaceInput, 'root_path'>) {
      if (!this.workspace) throw new Error('Workspace is not loaded')
      this.loading = true
      try {
        this.workspace = await apiRequest<Workspace>('/workspace', {
          method: 'PATCH',
          body: {
            ...input,
            expected_revision: this.workspace.revision,
          },
        })
        return this.workspace
      } finally {
        this.loading = false
      }
    },
    validatePath(path: string, purpose: 'workspace' | 'paper_root') {
      return apiRequest<PathValidation>('/workspace/validate-path', {
        method: 'POST',
        body: { path, purpose },
      })
    },
  },
})
