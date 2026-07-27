import { defineStore } from 'pinia'

const STORAGE_KEY = 'papermatrix.preferences.recent-projects'

function loadRecentProjects(): Record<string, string> {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')
    if (typeof parsed !== 'object' || parsed === null) return {}
    return Object.fromEntries(
      Object.entries(parsed).filter(
        ([projectId, value]) =>
          typeof projectId === 'string' &&
          typeof value === 'string' &&
          !Number.isNaN(Date.parse(value)),
      ),
    )
  } catch {
    return {}
  }
}

export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    recentProjects: loadRecentProjects(),
  }),
  actions: {
    markProjectOpened(projectId: string) {
      this.recentProjects = {
        ...this.recentProjects,
        [projectId]: new Date().toISOString(),
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.recentProjects))
    },
    lastOpenedAt(projectId: string) {
      return this.recentProjects[projectId] ?? null
    },
  },
})
