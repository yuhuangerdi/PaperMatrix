<script setup lang="ts">
import { CheckSquare2, RefreshCw, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import type { AnalysisItemKind, NoteParsePreview } from '@/types/api'

const props = defineProps<{
  preview: NoteParsePreview
  busy: boolean
}>()
const emit = defineEmits<{
  close: []
  refresh: []
  import: [candidateIds: string[]]
}>()

const selectedIds = ref<string[]>([])
const eligibleIds = computed(() =>
  props.preview.candidates
    .filter((candidate) => !candidate.duplicate_item_id)
    .map((candidate) => candidate.candidate_id),
)
const allSelected = computed(
  () => eligibleIds.value.length > 0 && selectedIds.value.length === eligibleIds.value.length,
)

watch(
  () => props.preview,
  () => {
    selectedIds.value = [...eligibleIds.value]
  },
  { immediate: true },
)

function toggleAll() {
  selectedIds.value = allSelected.value ? [] : [...eligibleIds.value]
}

function kindLabel(kind: AnalysisItemKind) {
  return {
    research_problem: '研究问题',
    scenario: '适用场景',
    method: '方法路线',
    method_component: '方法组件',
    mechanism: '关键机制',
    challenge: '挑战',
    innovation: '创新点',
    contribution: '附加贡献',
    experiment: '实验',
    finding: '关键发现',
    author_limitation: '作者局限',
    reviewer_limitation: '我的评价',
    condition: '成立条件',
  }[kind]
}
</script>

<template>
  <div class="modal-backdrop">
    <section
      class="question-dialog candidate-review-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="candidate-review-title"
    >
      <header>
        <div>
          <p class="eyebrow">结构化笔记</p>
          <h2 id="candidate-review-title">审阅解析候选</h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="candidate-review-body">
        <div v-if="preview.warnings.length" class="candidate-warnings" role="status">
          <p v-for="warning in preview.warnings" :key="warning">{{ warning }}</p>
        </div>

        <div class="candidate-review-toolbar">
          <span>
            笔记版本 {{ preview.note_revision }} · 论文版本 {{ preview.paper_revision }}
          </span>
          <button
            class="button button--secondary button--compact"
            type="button"
            :disabled="busy"
            @click="toggleAll"
          >
            <CheckSquare2 :size="15" /> {{ allSelected ? '取消全选' : '选择全部' }}
          </button>
        </div>

        <div v-if="preview.candidates.length === 0" class="empty-state empty-state--compact">
          <h2>没有可审阅的候选</h2>
          <p>填写模板中的结构化标题、列表或表格后保存笔记，再重新解析。</p>
        </div>
        <div v-else class="candidate-review-list">
          <label
            v-for="candidate in preview.candidates"
            :key="candidate.candidate_id"
            :class="{ 'candidate-review-item--duplicate': candidate.duplicate_item_id }"
          >
            <input
              v-model="selectedIds"
              type="checkbox"
              :value="candidate.candidate_id"
              :disabled="busy || !!candidate.duplicate_item_id"
            />
            <span class="candidate-review-content">
              <span class="candidate-review-meta">
                <span class="analysis-kind">{{ kindLabel(candidate.kind) }}</span>
                <span v-if="candidate.duplicate_item_id" class="duplicate-state">已存在</span>
                <span v-else-if="candidate.evidence_refs.length" class="evidence-state">
                  {{ candidate.evidence_refs.length }} 条证据
                </span>
              </span>
              <strong>{{ candidate.title }}</strong>
              <span class="candidate-summary">{{ candidate.summary || '无补充摘要' }}</span>
              <small>
                {{ candidate.section_title }} · 第 {{ candidate.section_order }} 条 ·
                {{ candidate.source_section }} · 第 {{ candidate.source_line_start }}-{{
                  candidate.source_line_end
                }}
                行
              </small>
            </span>
          </label>
        </div>
      </div>

      <footer>
        <span>确认后写入稳定定位标记与论文 YAML；已有人工条目不会被覆盖。</span>
        <div>
          <button
            class="button button--secondary"
            type="button"
            :disabled="busy"
            @click="emit('refresh')"
          >
            <RefreshCw :size="16" /> 重新解析
          </button>
          <button
            class="button button--primary"
            type="button"
            :disabled="busy || selectedIds.length === 0"
            @click="emit('import', selectedIds)"
          >
            确认导入 {{ selectedIds.length }} 条
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>
