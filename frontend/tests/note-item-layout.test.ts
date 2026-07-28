/// <reference types="node" />

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const stylesheet = readFileSync(resolve(process.cwd(), 'src/styles/main.css'), 'utf8')
const detailView = readFileSync(resolve(process.cwd(), 'src/views/PaperDetailView.vue'), 'utf8')

describe('note item layout', () => {
  it('keeps every template slot inside a bounded, independently scrollable workspace', () => {
    expect(detailView).toContain("'note-workspace--items': noteMode === 'items'")
    expect(detailView).toContain('<strong>模板目录</strong>')
    expect(detailView).toContain('v-for="group in noteSlotGroups"')
    expect(detailView).toContain("item.sync_status === 'empty'")
    expect(detailView).toContain('paperStore.updateNoteSlot')
    expect(detailView).toContain('添加可拓展条目')
    expect(detailView).toContain('添加同类条目')
    expect(stylesheet).toMatch(
      /\.note-workspace--items\s*\{[^}]*height:\s*min\(780px, calc\(100dvh - 260px\)\);[^}]*overflow:\s*hidden;/s,
    )
    expect(stylesheet).toMatch(
      /\.note-item-list-scroll\s*\{[^}]*min-height:\s*0;[^}]*overflow-y:\s*auto;/s,
    )
    expect(stylesheet).toMatch(
      /\.note-item-editor-pane\s*\{[^}]*min-height:\s*0;[^}]*grid-template-rows:\s*auto auto minmax\(0, 1fr\) auto;[^}]*overflow:\s*hidden;/s,
    )
  })

  it('keeps evidence in a separate rail with an inline add action', () => {
    expect(detailView).toContain('class="note-evidence-panel"')
    expect(detailView).toContain('@click="openEvidenceCreate"')
    expect(detailView).toContain('同时关联当前条目')
    expect(stylesheet).toMatch(
      /\.note-evidence-panel\s*\{[^}]*grid-template-rows:\s*auto auto minmax\(0, 1fr\);[^}]*overflow:\s*hidden;/s,
    )
    expect(stylesheet).toMatch(/\.note-evidence-list\s*\{[^}]*overflow-y:\s*auto;/s)
  })
})
