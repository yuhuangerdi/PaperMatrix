import { defineStore } from 'pinia'

import { apiGet, apiRequest } from '@/api/client'
import type {
  AnalysisItemInput,
  CandidateImportResult,
  NoteItemDocument,
  NoteItemUpdateResult,
  NoteParsePreview,
  Paper,
  PaperAnalysisDocument,
  PaperList,
  PaperNote,
  PaperSourceStatus,
  PaperSummary,
  QuestionInput,
  QuestionsDocument,
  ScanResult,
} from '@/types/api'

export const usePaperStore = defineStore('papers', {
  state: () => ({
    items: [] as PaperSummary[],
    total: 0,
    loading: false,
    scanResult: null as ScanResult | null,
    availableGroups: [] as string[],
  }),
  actions: {
    async get(projectId: string, paperId: string) {
      return apiGet<Paper>(`/projects/${projectId}/papers/${paperId}`)
    },
    async load(
      projectId: string,
      options: {
        q?: string
        sourceStatus?: PaperSourceStatus | ''
        group?: string
        sort?: string
      } = {},
    ) {
      this.loading = true
      try {
        const params = new URLSearchParams({
          q: options.q ?? '',
          sort: options.sort ?? '-updated_at',
          page_size: '200',
        })
        if (options.sourceStatus) params.set('source_status', options.sourceStatus)
        if (options.group) params.set('group', options.group)
        const result = await apiGet<PaperList>(`/projects/${projectId}/papers?${params}`)
        this.items = result.items
        this.total = result.total
        if (!options.group) {
          this.availableGroups = [
            ...new Set([
              ...this.availableGroups,
              ...result.items.map((item) => item.group).filter((item): item is string => !!item),
            ]),
          ].sort((left, right) => left.localeCompare(right, 'zh-CN'))
        }
        return result
      } finally {
        this.loading = false
      }
    },
    async upload(projectId: string, file: File, title = '') {
      const body = new FormData()
      body.append('file', file)
      if (title.trim()) body.append('title', title.trim())
      return apiRequest<Paper>(`/projects/${projectId}/papers/upload`, {
        method: 'POST',
        body,
        timeoutMs: 30_000,
      })
    },
    async link(projectId: string, path: string) {
      return apiRequest<Paper>(`/projects/${projectId}/papers/link`, {
        method: 'POST',
        body: { path },
      })
    },
    async createManual(projectId: string, title: string) {
      return apiRequest<Paper>(`/projects/${projectId}/papers/manual`, {
        method: 'POST',
        body: { title },
      })
    },
    async scan(directory: string, recursive: boolean) {
      this.scanResult = await apiRequest<ScanResult>('/paper-sources/scan', {
        method: 'POST',
        body: { directory, recursive },
        timeoutMs: 30_000,
      })
      return this.scanResult
    },
    async importCandidates(projectId: string, candidateIds: string[]) {
      if (!this.scanResult) throw new Error('No active scan')
      return apiRequest<{ imported: Paper[]; skipped: Array<{ reason: string }> }>(
        `/projects/${projectId}/papers/import`,
        {
          method: 'POST',
          body: {
            scan_token: this.scanResult.scan_token,
            candidate_ids: candidateIds,
          },
          timeoutMs: 30_000,
        },
      )
    },
    async relink(projectId: string, paper: PaperSummary, newPath: string) {
      return apiRequest<Paper>(`/projects/${projectId}/papers/${paper.paper_id}/relink`, {
        method: 'POST',
        body: { new_path: newPath, expected_revision: paper.revision },
      })
    },
    async updateBasicInformation(
      projectId: string,
      paper: Pick<PaperSummary, 'paper_id' | 'revision'>,
      input: {
        title: string
        authors: string[]
        affiliations: string[]
        venue: string | null
        publication_date: string | null
        reading_date: string | null
        citation_count: number | null
        language: string | null
        keywords: string[]
        abstract_text: string
        group: string | null
      },
    ) {
      return apiRequest<Paper>(`/projects/${projectId}/papers/${paper.paper_id}`, {
        method: 'PATCH',
        body: { ...input, expected_revision: paper.revision },
      })
    },
    async getNote(projectId: string, paperId: string) {
      return apiGet<PaperNote>(`/projects/${projectId}/papers/${paperId}/note`)
    },
    async saveNote(projectId: string, paperId: string, markdown: string, expectedRevision: number) {
      return apiRequest<PaperNote>(`/projects/${projectId}/papers/${paperId}/note`, {
        method: 'PUT',
        body: { markdown, expected_revision: expectedRevision },
        timeoutMs: 15_000,
      })
    },
    async getNoteItems(projectId: string, paperId: string) {
      return apiGet<NoteItemDocument>(`/projects/${projectId}/papers/${paperId}/note/items`)
    },
    async updateNoteItem(
      projectId: string,
      paperId: string,
      itemId: string,
      markdown: string,
      expectedNoteRevision: number,
      expectedPaperRevision: number,
      expectedSourceFingerprint: string,
    ) {
      return apiRequest<NoteItemUpdateResult>(
        `/projects/${projectId}/papers/${paperId}/note/items/${itemId}`,
        {
          method: 'PUT',
          body: {
            markdown,
            expected_note_revision: expectedNoteRevision,
            expected_paper_revision: expectedPaperRevision,
            expected_source_fingerprint: expectedSourceFingerprint,
          },
        },
      )
    },
    async getQuestions(projectId: string, paperId: string) {
      return apiGet<QuestionsDocument>(`/projects/${projectId}/papers/${paperId}/questions`)
    },
    async getAnalysis(projectId: string, paperId: string) {
      return apiGet<PaperAnalysisDocument>(`/projects/${projectId}/papers/${paperId}/analysis`)
    },
    async previewNoteAnalysis(projectId: string, paperId: string) {
      return apiRequest<NoteParsePreview>(
        `/projects/${projectId}/papers/${paperId}/analysis/parse-note`,
        { method: 'POST' },
      )
    },
    async importNoteCandidates(
      projectId: string,
      paperId: string,
      candidateIds: string[],
      expectedNoteRevision: number,
      expectedPaperRevision: number,
    ) {
      return apiRequest<CandidateImportResult>(
        `/projects/${projectId}/papers/${paperId}/analysis/import-candidates`,
        {
          method: 'POST',
          body: {
            candidate_ids: candidateIds,
            expected_note_revision: expectedNoteRevision,
            expected_paper_revision: expectedPaperRevision,
          },
        },
      )
    },
    async createAnalysisItem(
      projectId: string,
      paperId: string,
      input: AnalysisItemInput,
      expectedRevision: number,
    ) {
      return apiRequest<PaperAnalysisDocument>(
        `/projects/${projectId}/papers/${paperId}/analysis/items`,
        {
          method: 'POST',
          body: { ...input, expected_revision: expectedRevision },
        },
      )
    },
    async updateAnalysisItem(
      projectId: string,
      paperId: string,
      itemId: string,
      input: AnalysisItemInput,
      expectedRevision: number,
    ) {
      return apiRequest<PaperAnalysisDocument>(
        `/projects/${projectId}/papers/${paperId}/analysis/items/${itemId}`,
        {
          method: 'PATCH',
          body: { ...input, expected_revision: expectedRevision },
        },
      )
    },
    async deleteAnalysisItem(
      projectId: string,
      paperId: string,
      itemId: string,
      expectedRevision: number,
    ) {
      return apiRequest<PaperAnalysisDocument>(
        `/projects/${projectId}/papers/${paperId}/analysis/items/${itemId}?expected_revision=${expectedRevision}`,
        { method: 'DELETE' },
      )
    },
    async createQuestion(
      projectId: string,
      paperId: string,
      input: QuestionInput,
      expectedRevision: number,
    ) {
      return apiRequest<QuestionsDocument>(`/projects/${projectId}/papers/${paperId}/questions`, {
        method: 'POST',
        body: { ...input, expected_revision: expectedRevision },
      })
    },
    async updateQuestion(
      projectId: string,
      paperId: string,
      questionId: string,
      input: QuestionInput,
      expectedRevision: number,
    ) {
      return apiRequest<QuestionsDocument>(
        `/projects/${projectId}/papers/${paperId}/questions/${questionId}`,
        {
          method: 'PATCH',
          body: { ...input, expected_revision: expectedRevision },
        },
      )
    },
    async deleteQuestion(
      projectId: string,
      paperId: string,
      questionId: string,
      expectedRevision: number,
    ) {
      return apiRequest<QuestionsDocument>(
        `/projects/${projectId}/papers/${paperId}/questions/${questionId}?expected_revision=${expectedRevision}`,
        { method: 'DELETE' },
      )
    },
    async remove(projectId: string, paperId: string) {
      await apiRequest<{ source_pdf_untouched: true; removed_files: string[] }>(
        `/projects/${projectId}/papers/${paperId}?confirm_metadata_only=true`,
        { method: 'DELETE' },
      )
      this.items = this.items.filter((item) => item.paper_id !== paperId)
      this.total = Math.max(0, this.total - 1)
    },
  },
})
