import { defineStore } from 'pinia'

import { apiGet, apiRequest } from '@/api/client'
import type {
  FieldProblem,
  ItemReference,
  ProblemBoard,
  ProblemSynthesesViewDocument,
  ProblemSynthesisMatrix,
  ResolutionLevel,
} from '@/types/api'

export type ProblemBoardInput = Pick<
  ProblemBoard,
  'name' | 'purpose' | 'scope_id' | 'problem_ids' | 'paper_ids'
>

export type FieldProblemInput = Pick<
  FieldProblem,
  'name' | 'definition' | 'scope_note' | 'aliases' | 'tags' | 'status'
> & { source_problem_refs: ItemReference[] }

export interface PaperContributionInput {
  problem_id: string
  paper_id: string
  research_problem_item_id: string
  method_item_id: string | null
  experiment_item_id: string | null
  resolution_level: ResolutionLevel
  rationale: string
  supporting_evidence_ids: string[]
  counter_evidence: string
  conditions: string
  user_judgment: string
}

export const useProblemSynthesisStore = defineStore('problem-syntheses', {
  actions: {
    get(projectId: string) {
      return apiGet<ProblemSynthesesViewDocument>(`/projects/${projectId}/problem-syntheses`)
    },
    matrix(projectId: string, boardId: string) {
      return apiGet<ProblemSynthesisMatrix>(
        `/projects/${projectId}/matrices/problems?board_id=${encodeURIComponent(boardId)}`,
      )
    },
    createBoard(projectId: string, input: ProblemBoardInput, expectedRevision: number) {
      return apiRequest<ProblemSynthesesViewDocument>(`/projects/${projectId}/problem-boards`, {
        method: 'POST',
        body: { ...input, expected_revision: expectedRevision },
      })
    },
    updateBoard(
      projectId: string,
      boardId: string,
      input: ProblemBoardInput,
      expectedRevision: number,
    ) {
      return apiRequest<ProblemSynthesesViewDocument>(
        `/projects/${projectId}/problem-boards/${boardId}`,
        {
          method: 'PATCH',
          body: { ...input, expected_revision: expectedRevision },
        },
      )
    },
    removeBoard(projectId: string, boardId: string, expectedRevision: number) {
      return apiRequest<ProblemSynthesesViewDocument>(
        `/projects/${projectId}/problem-boards/${boardId}`,
        { method: 'DELETE', body: { expected_revision: expectedRevision } },
      )
    },
    createProblem(projectId: string, input: FieldProblemInput, expectedRevision: number) {
      return apiRequest<ProblemSynthesesViewDocument>(`/projects/${projectId}/field-problems`, {
        method: 'POST',
        body: { ...input, expected_revision: expectedRevision },
      })
    },
    updateProblem(
      projectId: string,
      problemId: string,
      input: FieldProblemInput,
      expectedRevision: number,
    ) {
      return apiRequest<ProblemSynthesesViewDocument>(
        `/projects/${projectId}/field-problems/${problemId}`,
        {
          method: 'PATCH',
          body: { ...input, expected_revision: expectedRevision },
        },
      )
    },
    removeProblem(projectId: string, problemId: string, expectedRevision: number) {
      return apiRequest<ProblemSynthesesViewDocument>(
        `/projects/${projectId}/field-problems/${problemId}`,
        { method: 'DELETE', body: { expected_revision: expectedRevision } },
      )
    },
    createContribution(projectId: string, input: PaperContributionInput, expectedRevision: number) {
      return apiRequest<ProblemSynthesesViewDocument>(
        `/projects/${projectId}/paper-contributions`,
        { method: 'POST', body: { ...input, expected_revision: expectedRevision } },
      )
    },
    updateContribution(
      projectId: string,
      contributionId: string,
      input: PaperContributionInput,
      expectedRevision: number,
    ) {
      return apiRequest<ProblemSynthesesViewDocument>(
        `/projects/${projectId}/paper-contributions/${contributionId}`,
        { method: 'PATCH', body: { ...input, expected_revision: expectedRevision } },
      )
    },
    removeContribution(projectId: string, contributionId: string, expectedRevision: number) {
      return apiRequest<ProblemSynthesesViewDocument>(
        `/projects/${projectId}/paper-contributions/${contributionId}`,
        { method: 'DELETE', body: { expected_revision: expectedRevision } },
      )
    },
  },
})
