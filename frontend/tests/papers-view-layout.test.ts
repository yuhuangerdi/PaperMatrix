/// <reference types="node" />

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const stylesheet = readFileSync(resolve(process.cwd(), 'src/styles/main.css'), 'utf8')
const papersView = readFileSync(resolve(process.cwd(), 'src/views/PapersView.vue'), 'utf8')

describe('papers view layout', () => {
  it('keeps the analysis matrix focused on paper-level introductory metadata', () => {
    for (const heading of [
      '一句话总结',
      '背景',
      '研究问题',
      '经典工作',
      '方法',
      '挑战',
      '创新',
      '实验',
      '发现',
      '局限',
      '条件',
      '证据',
    ]) {
      expect(papersView).not.toContain(`<th>${heading}</th>`)
    }

    expect(papersView).toContain('<th>论文简介</th>')
    expect(papersView).toContain('<th>主题关键词</th>')
    expect(papersView).toContain('<th>整理进度</th>')
  })

  it('gives the catalog selection, paper, and action columns independent widths', () => {
    expect(papersView).toContain('class="paper-table catalog-table"')
    expect(papersView).toContain('class="catalog-paper-cell"')
    expect(stylesheet).toMatch(
      /\.paper-table\.catalog-table \.selection-cell\s*\{[^}]*width:\s*40px;/s,
    )
    expect(stylesheet).toMatch(
      /\.catalog-paper-cell \.paper-title-link,\s*\.catalog-paper-cell > span\s*\{[^}]*text-overflow:\s*ellipsis;[^}]*white-space:\s*nowrap;/s,
    )
    expect(stylesheet).toMatch(/\.catalog-actions-column\s*\{[^}]*width:\s*124px;/s)
  })
})
