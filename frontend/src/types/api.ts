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
  schema_version: 11
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
    urls: string[]
    code_url: string | null
    data_url: string | null
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
  evidence_code: string | null
  paper_id: string
  page_label: string | null
  pdf_page_index: number | null
  section: string | null
  figure: string | null
  table: string | null
  locator_note: string
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
  schema_version: 2
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
  | 'background'
  | 'research_problem'
  | 'scenario'
  | 'related_work'
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
  display_label: string | null
  title: string
  summary: string
  section_key: string | null
  section_title: string | null
  section_order: number | null
  source_anchor: string | null
  source_note_revision: number | null
  source_fingerprint: string | null
  attributes: Record<string, string>
  evidence_ids: string[]
  tags: string[]
  writing_uses: WritingUse[]
  is_favorite: boolean
  created_at: string
  updated_at: string
}

export interface PaperAnalysisDocument {
  paper_id: string
  revision: number
  updated_at: string
  evidence_catalog: EvidenceReference[]
  items: AnalysisItem[]
}

export interface AnalysisItemInput {
  kind: AnalysisItemKind
  display_label: string | null
  title: string
  summary: string
  attributes: Record<string, string>
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
  superseded_item_ids: string[]
}

export interface NoteParsePreview {
  paper_id: string
  note_revision: number
  paper_revision: number
  candidates: NoteAnalysisCandidate[]
  removals: NoteAnalysisRemoval[]
  warnings: string[]
}

export interface NoteAnalysisRemoval {
  item_id: string
  kind: AnalysisItemKind
  title: string
  section_key: string | null
  section_title: string | null
  section_order: number | null
}

export interface CandidateImportResult {
  analysis: PaperAnalysisDocument
  note: PaperNote
  imported_items: AnalysisItem[]
  synchronized_items: AnalysisItem[]
  skipped_candidate_ids: string[]
  superseded_item_ids: string[]
  deleted_item_ids: string[]
}

export interface NoteItemSource {
  item_id: string
  kind: AnalysisItemKind
  display_label: string | null
  title: string
  section_key: string | null
  section_title: string | null
  section_order: number | null
  markdown: string
  source_fingerprint: string | null
  sync_status: 'synced' | 'review_required' | 'missing'
  is_favorite: boolean
}

export interface NoteItemTemplate {
  template_key: string
  chapter: number
  kind: AnalysisItemKind
  label: string
  description: string
  heading: string
  heading_level: 2 | 3 | 4
  repeatable: boolean
  child_heading_prefix: string
  insert_before_heading: string | null
  body_template: string
}

export interface NoteItemSlot {
  slot_key: string
  template_key: string
  kind: AnalysisItemKind
  label: string
  description: string
  section_title: string
  markdown: string
  item_id: string | null
  source_fingerprint: string | null
  sync_status: 'empty' | 'synced' | 'review_required' | 'missing'
  is_favorite: boolean
  repeatable: boolean
  repeatable_template_key: string | null
  can_delete: boolean
}

export interface NoteItemDocument {
  paper_id: string
  note_revision: number
  paper_revision: number
  item_templates: NoteItemTemplate[]
  slots: NoteItemSlot[]
  evidence_catalog: EvidenceReference[]
  items: NoteItemSource[]
  candidates: NoteAnalysisCandidate[]
  removals: NoteAnalysisRemoval[]
  warnings: string[]
  pending_candidate_count: number
}

export interface NoteItemUpdateResult {
  note: PaperNote
  analysis: PaperAnalysisDocument
  item: AnalysisItem
}

export interface NoteSlotUpdateResult {
  note: PaperNote
  analysis: PaperAnalysisDocument
  slot: NoteItemSlot
  item: AnalysisItem | null
}

export interface EvidenceCreateResult {
  note: PaperNote
  analysis: PaperAnalysisDocument
  evidence: EvidenceReference
  item: AnalysisItem | null
}

export interface NoteItemFavoriteUpdateResult {
  analysis: PaperAnalysisDocument
  item: AnalysisItem
}

export interface NoteItemDeleteResult {
  note: PaperNote
  analysis: PaperAnalysisDocument
  deleted_item_ids: string[]
}

export type ItemLinkType =
  | 'addresses'
  | 'partially_addresses'
  | 'depends_on'
  | 'enables'
  | 'evaluates'
  | 'supports'
  | 'contradicts'
  | 'extends'
  | 'related_to'

export interface ItemReference {
  paper_id: string
  item_id: string
}

export interface ItemLink {
  link_id: string
  source: ItemReference
  target: ItemReference
  type: ItemLinkType
  description: string
  created_at: string
  updated_at: string
}

export interface ItemLinksDocument {
  schema_version: 1
  project_id: string
  revision: number
  updated_at: string
  links: ItemLink[]
}

export type ItemReferenceStatus = 'available' | 'missing_paper' | 'missing_item'

export interface ProjectAnalysisItem {
  paper_id: string
  paper_title: string
  item: AnalysisItem
}

export interface ProjectAnalysisItemCatalog {
  project_id: string
  items: ProjectAnalysisItem[]
}

export interface ItemReferenceView {
  reference: ItemReference
  status: ItemReferenceStatus
  paper_title: string | null
  item_title: string | null
  item_kind: AnalysisItem['kind'] | null
}

export interface ItemLinkView {
  link: ItemLink
  source: ItemReferenceView
  target: ItemReferenceView
}

export interface ItemLinksViewDocument {
  document: ItemLinksDocument
  links: ItemLinkView[]
  dangling_count: number
}

export interface ItemLinkImpact {
  references: ItemReference[]
  affected_links: ItemLinkView[]
}

export interface AnalysisScope {
  scope_id: string
  name: string
  purpose: string
  paper_ids: string[]
  source_filter_snapshot: Record<string, string>
  created_at: string
  updated_at: string
}

export interface AnalysisScopesDocument {
  schema_version: 1
  project_id: string
  revision: number
  updated_at: string
  scopes: AnalysisScope[]
}

export interface AnalysisScopeView {
  scope: AnalysisScope
  available_paper_ids: string[]
  missing_paper_ids: string[]
}

export interface AnalysisScopesViewDocument {
  document: AnalysisScopesDocument
  scopes: AnalysisScopeView[]
}

export interface AnalysisReadiness {
  method_ready: boolean
  experiment_ready: boolean
  limitation_ready: boolean
  evidence_ready: boolean
  ready_count: number
  missing_categories: string[]
}

export interface LiteratureMatrixRow {
  paper_id: string
  title: string
  short_title: string
  authors: string[]
  year: number | null
  venue: string | null
  group: string | null
  reading_status: PaperSummary['reading_status']
  source_status: PaperSourceStatus
  importance_score: number | null
  one_sentence_summary: string
  keywords: string[]
  background: string[]
  research_problems: string[]
  related_work: string[]
  methods: string[]
  challenges: string[]
  innovations: string[]
  experiments: string[]
  findings: string[]
  limitations: string[]
  conditions: string[]
  evidence_count: number
  readiness: AnalysisReadiness
  revision: number
}

export interface LiteratureMatrix {
  project_id: string
  scope_id: string | null
  scope_name: string | null
  rows: LiteratureMatrixRow[]
  missing_paper_ids: string[]
  total: number
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
