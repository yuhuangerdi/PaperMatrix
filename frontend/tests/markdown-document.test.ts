import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import MarkdownDocument from '@/components/MarkdownDocument.vue'

describe('MarkdownDocument', () => {
  it('renders headings, lists, tables and safe links instead of Markdown source', () => {
    const wrapper = mount(MarkdownDocument, {
      props: {
        markdown: `## 方法

- **输入**：目标
- 输出：建议

| 条目 | 优点 |
| --- | --- |
| Agent | 可扩展 |

[论文页面](https://example.com)`,
      },
    })

    expect(wrapper.find('h2').text()).toBe('方法')
    expect(wrapper.findAll('li')).toHaveLength(2)
    expect(wrapper.find('table').text()).toContain('Agent')
    expect(wrapper.find('a').attributes('href')).toBe('https://example.com/')
    expect(wrapper.text()).not.toContain('| --- | --- |')
  })

  it('renders Markdown separators as rules', () => {
    const wrapper = mount(MarkdownDocument, {
      props: { markdown: '上文\n\n---\n\n下文' },
    })

    expect(wrapper.find('hr').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('---')
  })

  it('escapes raw HTML from a note', () => {
    const wrapper = mount(MarkdownDocument, {
      props: { markdown: '<script>alert("unsafe")</script>' },
    })

    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.html()).toContain('&lt;script&gt;')
  })
})
