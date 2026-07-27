import { defineStore } from 'pinia'

import { apiGet, apiRequest } from '@/api/client'
import type { Project, ProjectList, ProjectSummary } from '@/types/api'

export interface ProjectInput {
  name: string
  topic: string
  description: string
  tags: string[]
}

export const useProjectStore = defineStore('projects', {
  state: () => ({
    items: [] as ProjectSummary[],
    current: null as Project | null,
    loading: false,
  }),
  actions: {
    async loadList(includeArchived = false) {
      this.loading = true
      try {
        const result = await apiGet<ProjectList>(`/projects?include_archived=${includeArchived}`)
        this.items = result.items
        return result
      } finally {
        this.loading = false
      }
    },
    async load(projectId: string) {
      this.loading = true
      try {
        this.current = await apiGet<Project>(`/projects/${projectId}`)
        return this.current
      } finally {
        this.loading = false
      }
    },
    async create(input: ProjectInput) {
      return apiRequest<Project>('/projects', { method: 'POST', body: input })
    },
    async update(
      projectId: string,
      input: ProjectInput & { status: 'active' | 'archived'; expected_revision: number },
    ) {
      this.current = await apiRequest<Project>(`/projects/${projectId}`, {
        method: 'PATCH',
        body: input,
      })
      return this.current
    },
    async remove(projectId: string) {
      await apiRequest<void>(`/projects/${projectId}?confirm=true`, {
        method: 'DELETE',
      })
      this.items = this.items.filter((item) => item.project_id !== projectId)
      if (this.current?.project_id === projectId) this.current = null
    },
  },
})
