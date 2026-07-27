import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { usePreferencesStore } from '@/stores/preferences'

describe('preferences store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('stores only recent project identifiers and timestamps', () => {
    const store = usePreferencesStore()

    store.markProjectOpened('project-id')

    const persisted = JSON.parse(
      localStorage.getItem('papermatrix.preferences.recent-projects') ?? '{}',
    )
    expect(Object.keys(persisted)).toEqual(['project-id'])
    expect(Date.parse(persisted['project-id'])).not.toBeNaN()
  })
})
