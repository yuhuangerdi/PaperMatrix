import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import NoteCandidateReviewDialog from '@/components/NoteCandidateReviewDialog.vue'
import type { NoteParsePreview } from '@/types/api'

const preview: NoteParsePreview = {
  paper_id: '11111111-1111-4111-8111-111111111111',
  note_revision: 4,
  paper_revision: 3,
  candidates: [],
  removals: [
    {
      item_id: '22222222-2222-4222-8222-222222222222',
      kind: 'method',
      title: '核心思路',
      section_key: 'section-3',
      section_title: '3. 本文解决思路和整体框架',
      section_order: 1,
    },
  ],
  warnings: [],
}

describe('NoteCandidateReviewDialog', () => {
  it('requires explicit selection before confirming a removed source item', async () => {
    const wrapper = mount(NoteCandidateReviewDialog, {
      props: { preview, busy: false },
    })
    const checkbox = wrapper.get('.candidate-review-item--removal input')
    const confirm = wrapper.get('.candidate-review-dialog footer .button--primary')

    expect((checkbox.element as HTMLInputElement).checked).toBe(false)
    expect((confirm.element as HTMLButtonElement).disabled).toBe(true)

    await checkbox.setValue(true)
    await confirm.trigger('click')

    expect(wrapper.emitted('import')).toEqual([[[], ['22222222-2222-4222-8222-222222222222']]])
  })
})
