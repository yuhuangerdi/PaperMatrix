export interface HealthResponse {
  status: 'ok'
  version: string
  workspace_initialized: boolean
}

export interface Workspace {
  workspace_id: string
  name: string
  root_path: string
  allowed_paper_roots: string[]
  revision: number
}

export interface PathValidation {
  valid: boolean
  normalized_path: string
  readable: boolean
  writable: boolean
  reason: string | null
}

export interface Project {
  schema_version: 1
  project_id: string
  name: string
  slug: string
  topic: string
  description: string
  tags: string[]
  status: 'active' | 'archived'
  created_at: string
  updated_at: string
  revision: number
}

export interface ProjectSummary extends Project {
  paper_count: number
  deep_read_count: number
  reported_count: number
}

export interface ProjectList {
  items: ProjectSummary[]
  total: number
}

export type PaperSourceStatus = 'available' | 'missing' | 'changed' | 'unreadable' | 'unlinked'

export interface PaperSummary {
  paper_id: string
  project_id: string
  title: string
  short_title: string
  authors: string[]
  affiliations: string[]
  year: number | null
  venue: string | null
  publication_date: string | null
  reading_date: string | null
  citation_count: number | null
  language: string | null
  keywords: string[]
  group: string | null
  topics: string[]
  tags: string[]
  reading_status: 'unread' | 'skimmed' | 'deep_read' | 'summarized' | 'reported'
  importance_score: number | null
  writing_uses: string[]
  source_status: PaperSourceStatus
  source_filename: string | null
  page_count: number | null
  one_sentence_summary: string
  updated_at: string
  revision: number
}

export interface Paper extends Omit<
  PaperSummary,
  'source_status' | 'source_filename' | 'page_count'
> {
  schema_version: 6
  source: {
    path: string | null
    path_mode: 'absolute' | 'workspace_relative' | null
    original_filename: string | null
    size_bytes: number | null
    modified_at: string | null
    fingerprint: string | null
    sha256: string | null
    page_count: number | null
    status: PaperSourceStatus
  }
  bibliography: {
    title: string
    short_title: string
    authors: string[]
    affiliations: string[]
    year: number | null
    venue: string | null
    publication_date: string | null
    citation_count: number | null
    language: string | null
    keywords: string[]
    abstract_text: string
    publication_type: string
  }
  organization: {
    topics: string[]
    tags: string[]
    group: string | null
    reading_date: string | null
    reading_status: PaperSummary['reading_status']
    importance_score: number | null
    writing_uses: string[]
    one_sentence_summary: string
  }
  structured_summary: Record<string, unknown> & { items: AnalysisItem[] }
  created_at: string
}

export interface PaperList {
  items: PaperSummary[]
  invalid_items: InvalidPaperRecord[]
  total: number
  invalid_total: number
  page: number
  page_size: number
}

export interface InvalidPaperRecord {
  paper_id: string
  title: string
  schema_version: number | null
  reason: string
}

export interface PaperNote {
  paper_id: string
  markdown: string
  revision: number
  updated_at: string
}

export type QuestionStatus = 'open' | 'answered' | 'deferred'

export interface EvidenceReference {
  evidence_id?: string
  paper_id: string
  page_label: string | null
  pdf_page_index: number | null
  section: string | null
  figure: string | null
  table: string | null
  locator_note: string
  source_item_id: string | null
}

export interface ReadingQuestion {
  question_id: string
  paper_id: string
  question: string
  status: QuestionStatus
  answer: string
  evidence: EvidenceReference[]
  tags: string[]
  created_at: string
  updated_at: string
}

export interface QuestionsDocument {
  schema_version: 1
  paper_id: string
  revision: number
  updated_at: string
  questions: ReadingQuestion[]
}

export interface QuestionInput {
  question: string
  status: QuestionStatus
  answer: string
  evidence: EvidenceReference[]
  tags: string[]
}

export type WritingUse =
  | 'INTRO'
  | 'RELATED'
  | 'METHOD'
  | 'BASELINE'
  | 'DATASET'
  | 'METRIC'
  | 'LIMITATION'
  | 'DISCUSSION'
  | 'FUTURE'

export type AnalysisItemKind =
  | 'research_problem'
  | 'scenario'
  | 'method'
  | 'method_component'
  | 'mechanism'
  | 'challenge'
  | 'innovation'
  | 'contribution'
  | 'experiment'
  | 'finding'
  | 'author_limitation'
  | 'reviewer_limitation'
  | 'condition'

export interface AnalysisItem {
  item_id: string
  kind: AnalysisItemKind
  title: string
  summary: string
  section_key: string | null
  section_title: string | null
  section_order: number | null
  source_anchor: string | null
  source_note_revision: number | null
  source_fingerprint: string | null
  attributes: Record<string, string>
  evidence_refs: EvidenceReference[]
  tags: string[]
  writing_uses: WritingUse[]
  created_at: string
  updated_at: string
}

export interface PaperAnalysisDocument {
  paper_id: string
  revision: number
  updated_at: string
  items: AnalysisItem[]
}

export interface AnalysisItemInput {
  kind: AnalysisItemKind
  title: string
  summary: string
  attributes: Record<string, string>
  evidence_refs: EvidenceReference[]
  tags: string[]
  writing_uses: WritingUse[]
}

export interface NoteAnalysisCandidate {
  candidate_id: string
  kind: AnalysisItemKind
  title: string
  summary: string
  attributes: Record<string, string>
  evidence_refs: EvidenceReference[]
  section_key: string
  section_title: string
  section_order: number
  source_anchor: string
  source_fingerprint: string
  sync_status: 'new' | 'unchanged' | 'modified'
  source_section: string
  source_line_start: number
  source_line_end: number
  duplicate_item_id: string | null
}

export interface NoteParsePreview {
  paper_id: string
  note_revision: number
  paper_revision: number
  candidates: NoteAnalysisCandidate[]
  warnings: string[]
}

export interface CandidateImportResult {
  analysis: PaperAnalysisDocument
  note: PaperNote
  imported_items: AnalysisItem[]
  synchronized_items: AnalysisItem[]
  skipped_candidate_ids: string[]
}

export interface NoteItemSource {
  item_id: string
  kind: AnalysisItemKind
  title: string
  section_key: string | null
  section_title: string | null
  section_order: number | null
  markdown: string
  source_fingerprint: string | null
  sync_status: 'synced' | 'review_required' | 'missing'
}

export interface NoteItemDocument {
  paper_id: string
  note_revision: number
  paper_revision: number
  items: NoteItemSource[]
  pending_candidate_count: number
}

export interface NoteItemUpdateResult {
  note: PaperNote
  analysis: PaperAnalysisDocument
  item: AnalysisItem
}

export interface ScanCandidate {
  candidate_id: string
  display_path: string
  filename: string
  title: string
  page_count: number | null
  size_bytes: number
  readable: boolean
}

export interface ScanResult {
  scan_token: string
  items: ScanCandidate[]
  warnings: string[]
}

export interface ApiErrorPayload {
  error: {
    code: string
    message: string
    details: Record<string, unknown>
    action: string | null
    request_id: string
  }
}
