<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  markdown: string
  compact?: boolean
}>()

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function safeHref(value: string) {
  try {
    const url = new URL(value)
    return ['http:', 'https:', 'mailto:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

function renderInline(value: string) {
  let html = escapeHtml(value)
  html = html.replace(/\[([^\]]+)]\(([^)\s]+)\)/g, (_match, label: string, href: string) => {
    const safe = safeHref(href)
    return safe
      ? `<a href="${escapeHtml(safe)}" target="_blank" rel="noopener noreferrer">${label}</a>`
      : label
  })
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  html = html.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>')
  return html
}

function isTableDivider(line: string) {
  return /^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(line)
}

function tableCells(line: string) {
  return line
    .trim()
    .replace(/^\||\|$/g, '')
    .split('|')
    .map((cell) => cell.trim())
}

function renderTable(lines: string[]) {
  const headers = tableCells(lines[0] ?? '')
  const rows = lines.slice(2).map(tableCells)
  const headerHtml = headers.map((cell) => `<th>${renderInline(cell)}</th>`).join('')
  const rowHtml = rows
    .map(
      (cells) =>
        `<tr>${headers
          .map((_, index) => `<td>${renderInline(cells[index] ?? '')}</td>`)
          .join('')}</tr>`,
    )
    .join('')
  return `<div class="markdown-table-wrap"><table><thead><tr>${headerHtml}</tr></thead><tbody>${rowHtml}</tbody></table></div>`
}

function renderMarkdown(markdown: string) {
  const lines = markdown
    .replace(/<!--\s*papermatrix:item:[\w-]+\s*-->\s*\n?/g, '')
    .replace(/\r\n/g, '\n')
    .split('\n')
  const blocks: string[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index] ?? ''
    if (!line.trim()) {
      index += 1
      continue
    }

    if (/^\s*(?:---+|\*\*\*+|___+)\s*$/.test(line)) {
      blocks.push('<hr>')
      index += 1
      continue
    }

    const codeFence = line.match(/^```([^`]*)$/)
    if (codeFence) {
      const code: string[] = []
      index += 1
      while (index < lines.length && !/^```/.test(lines[index] ?? '')) {
        code.push(lines[index] ?? '')
        index += 1
      }
      if (index < lines.length) index += 1
      blocks.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`)
      continue
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      const level = (heading[1] ?? '').length
      blocks.push(`<h${level}>${renderInline(heading[2] ?? '')}</h${level}>`)
      index += 1
      continue
    }

    if (line.includes('|') && isTableDivider(lines[index + 1] ?? '')) {
      const tableLines = [line, lines[index + 1] ?? '']
      index += 2
      while (index < lines.length && (lines[index] ?? '').includes('|')) {
        tableLines.push(lines[index] ?? '')
        index += 1
      }
      blocks.push(renderTable(tableLines))
      continue
    }

    const unordered = line.match(/^\s*[-*+]\s+(.+)$/)
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/)
    if (unordered || ordered) {
      const pattern = unordered ? /^\s*[-*+]\s+(.+)$/ : /^\s*\d+[.)]\s+(.+)$/
      const items: string[] = []
      while (index < lines.length) {
        const item = (lines[index] ?? '').match(pattern)
        if (!item) break
        items.push(`<li>${renderInline(item[1] ?? '')}</li>`)
        index += 1
      }
      blocks.push(`<${unordered ? 'ul' : 'ol'}>${items.join('')}</${unordered ? 'ul' : 'ol'}>`)
      continue
    }

    const quote = line.match(/^>\s?(.*)$/)
    if (quote) {
      const quoteLines: string[] = []
      while (index < lines.length) {
        const current = (lines[index] ?? '').match(/^>\s?(.*)$/)
        if (!current) break
        quoteLines.push(current[1] ?? '')
        index += 1
      }
      blocks.push(`<blockquote>${quoteLines.map(renderInline).join('<br>')}</blockquote>`)
      continue
    }

    const paragraph: string[] = []
    while (index < lines.length) {
      const current = lines[index] ?? ''
      if (
        !current.trim() ||
        /^#{1,6}\s+/.test(current) ||
        /^```/.test(current) ||
        /^\s*[-*+]\s+/.test(current) ||
        /^\s*\d+[.)]\s+/.test(current) ||
        /^>\s?/.test(current) ||
        (current.includes('|') && isTableDivider(lines[index + 1] ?? ''))
      ) {
        break
      }
      paragraph.push(current)
      index += 1
    }
    blocks.push(`<p>${paragraph.map(renderInline).join('<br>')}</p>`)
  }

  return blocks.join('')
}

const html = computed(() => renderMarkdown(props.markdown))
</script>

<template>
  <!-- Markdown text is escaped before renderMarkdown() adds this component's controlled HTML tags. -->
  <article
    class="markdown-document"
    :class="{ 'markdown-document--compact': compact }"
    :innerHTML="html"
  />
</template>
