<script setup lang="ts">
import { Plus, Trash2, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import type { AnalysisItem, AnalysisItemInput, AnalysisItemKind, WritingUse } from '@/types/api'

const props = defineProps<{
  item: AnalysisItem | null
  busy: boolean
}>()
const emit = defineEmits<{
  close: []
  save: [input: AnalysisItemInput]
}>()

const kindOptions: Array<{ value: AnalysisItemKind; label: string }> = [
  { value: 'background', label: '研究背景' },
  { value: 'research_problem', label: '研究问题' },
  { value: 'scenario', label: '适用场景' },
  { value: 'related_work', label: '经典文献' },
  { value: 'method', label: '方法路线' },
  { value: 'method_component', label: '方法组件' },
  { value: 'mechanism', label: '关键机制' },
  { value: 'challenge', label: '挑战' },
  { value: 'innovation', label: '创新点' },
  { value: 'contribution', label: '附加贡献' },
  { value: 'experiment', label: '实验' },
  { value: 'finding', label: '关键发现' },
  { value: 'author_limitation', label: '作者局限' },
  { value: 'reviewer_limitation', label: '我的评价' },
  { value: 'condition', label: '成立条件' },
]
const writingUseOptions: Array<{ value: WritingUse; label: string }> = [
  { value: 'INTRO', label: '引言' },
  { value: 'RELATED', label: '相关工作' },
  { value: 'METHOD', label: '方法' },
  { value: 'BASELINE', label: '基线' },
  { value: 'DATASET', label: '数据集' },
  { value: 'METRIC', label: '指标' },
  { value: 'LIMITATION', label: '局限' },
  { value: 'DISCUSSION', label: '讨论' },
  { value: 'FUTURE', label: '未来工作' },
]

function splitValues(value: string) {
  return value
    .split(/[,，]/)
    .map((entry) => entry.trim())
    .filter(Boolean)
}

const form = ref({
  kind: props.item?.kind ?? ('research_problem' as AnalysisItemKind),
  displayLabel: props.item?.display_label ?? '',
  title: props.item?.title ?? '',
  summary: props.item?.summary ?? '',
  tags: props.item?.tags.join(', ') ?? '',
  writingUses: [...(props.item?.writing_uses ?? [])] as WritingUse[],
  attributes: Object.entries(props.item?.attributes ?? {}).map(([key, value]) => ({
    key,
    value,
  })),
})
const initial = JSON.stringify(form.value)
const dirty = computed(() => JSON.stringify(form.value) !== initial)

function requestClose() {
  if (dirty.value && !window.confirm('放弃尚未保存的分析条目修改吗？')) return
  emit('close')
}

function submit() {
  const attributes = Object.fromEntries(
    form.value.attributes
      .map((entry) => [entry.key.trim(), entry.value.trim()])
      .filter(([key, value]) => key && value),
  )
  emit('save', {
    kind: form.value.kind,
    display_label: form.value.displayLabel.trim() || null,
    title: form.value.title.trim(),
    summary: form.value.summary.trim(),
    attributes,
    tags: splitValues(form.value.tags),
    writing_uses: form.value.writingUses,
  })
}
</script>

<template>
  <div class="modal-backdrop">
    <section
      class="question-dialog analysis-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="analysis-item-title"
    >
      <header>
        <div>
          <p class="eyebrow">单篇分析</p>
          <h2 id="analysis-item-title">{{ item ? '编辑分析条目' : '添加分析条目' }}</h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="requestClose">
          <X :size="20" />
        </button>
      </header>

      <div class="question-form analysis-form">
        <div class="question-form-row">
          <label class="field">
            <span>条目类型</span>
            <select v-model="form.kind" class="select-control">
              <option v-for="option in kindOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>自定义标签</span>
            <input v-model="form.tags" placeholder="用逗号分隔" />
          </label>
        </div>
        <label class="field">
          <span>显示标签（可留空）</span>
          <input v-model="form.displayLabel" maxlength="80" placeholder="默认使用条目类型" />
        </label>
        <label class="field">
          <span>标题</span>
          <input v-model="form.title" maxlength="300" />
        </label>
        <label class="field">
          <span>分析摘要</span>
          <textarea v-model="form.summary" class="answer-input" />
        </label>

        <fieldset class="writing-use-fieldset">
          <legend>写作用途</legend>
          <label v-for="option in writingUseOptions" :key="option.value">
            <input v-model="form.writingUses" type="checkbox" :value="option.value" />
            <span>{{ option.label }}</span>
          </label>
        </fieldset>

        <section class="evidence-editor">
          <header>
            <strong>结构化属性</strong>
            <button
              class="button button--secondary button--compact"
              type="button"
              @click="form.attributes.push({ key: '', value: '' })"
            >
              <Plus :size="15" /> 添加属性
            </button>
          </header>
          <div v-for="(attribute, index) in form.attributes" :key="index" class="attribute-row">
            <input
              v-model="attribute.key"
              :aria-label="`属性 ${index + 1} 名称`"
              placeholder="名称"
            />
            <input
              v-model="attribute.value"
              :aria-label="`属性 ${index + 1} 内容`"
              placeholder="内容"
            />
            <button
              class="icon-button icon-button--danger"
              type="button"
              :aria-label="`删除属性 ${index + 1}`"
              @click="form.attributes.splice(index, 1)"
            >
              <Trash2 :size="15" />
            </button>
          </div>
        </section>
      </div>

      <footer>
        <span>证据引用只在笔记正文以“证据：E-001”维护。</span>
        <div>
          <button class="button button--secondary" type="button" @click="requestClose">取消</button>
          <button
            class="button button--primary"
            type="button"
            :disabled="busy || !form.title.trim()"
            @click="submit"
          >
            {{ busy ? '保存中…' : '保存条目' }}
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>
