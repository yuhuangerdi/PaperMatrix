import { defineStore } from 'pinia'

import { ApiError, apiGet } from '@/api/client'
import type { HealthResponse } from '@/types/api'

export type ConnectionState = 'checking' | 'online' | 'offline'

export const useAppStore = defineStore('app', {
  state: () => ({
    connection: 'checking' as ConnectionState,
    health: null as HealthResponse | null,
    error: null as ApiError | null,
  }),
  actions: {
    async checkHealth() {
      this.connection = 'checking'
      this.error = null
      try {
        this.health = await apiGet<HealthResponse>('/health')
        this.connection = 'online'
      } catch (error: unknown) {
        this.health = null
        this.connection = 'offline'
        this.error =
          error instanceof ApiError
            ? error
            : new ApiError('无法检查后端状态。', 'PM-NETWORK-001', null, null)
      }
    },
  },
})
