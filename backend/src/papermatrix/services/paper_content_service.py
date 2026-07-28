"""Paper note and reading-question orchestration."""

# ruff: noqa: RUF001

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from papermatrix.core.errors import (
    AnalysisCandidateSelectionError,
    AnalysisItemNotFoundError,
    AnalysisItemSourceError,
    AnalysisPreviewStaleError,
    QuestionNotFoundError,
)
from papermatrix.core.schema_registry import SchemaRegistry
from papermatrix.domain.note_analysis import (
    CandidateImportResult,
    EvidenceCreateResult,
    NoteAnalysisCandidate,
    NoteAnalysisRemoval,
    NoteItemDeleteResult,
    NoteItemDocument,
    NoteItemFavoriteUpdateResult,
    NoteItemSlot,
    NoteItemSource,
    NoteItemTemplate,
    NoteItemUpdateResult,
    NoteParsePreview,
    NoteSlotUpdateResult,
)
from papermatrix.domain.paper import AnalysisItem, Paper, PaperAnalysisDocument
from papermatrix.domain.paper_content import (
    EvidenceReference,
    PaperNote,
    QuestionsDocument,
    QuestionStatus,
    ReadingQuestion,
)
from papermatrix.repositories.paper_content_repository import PaperContentRepository
from papermatrix.repositories.paper_repository import PaperRepository
from papermatrix.repositories.project_repository import ProjectRepository
from papermatrix.services.markdown_analysis_parser import (
    add_item_anchors,
    append_evidence_row,
    append_item_evidence_reference,
    append_repeatable_note_item,
    note_item_fragment,
    note_template_slot_fragment,
    parse_note_candidates,
    remove_item_anchors,
    remove_note_item_fragments,
    replace_note_item_fragment,
    replace_note_template_slot,
)
from papermatrix.services.workspace_service import WorkspaceService


class PaperContentService:
    _ITEM_TEMPLATES = (
        NoteItemTemplate(
            template_key="1.1",
            chapter=1,
            kind="background",
            label="研究背景",
            description="领域背景、研究脉络或问题出现的环境。",
        ),
        NoteItemTemplate(
            template_key="1.2",
            chapter=1,
            kind="research_problem",
            label="具体问题",
            description="论文明确提出、形式化或试图解决的问题。",
        ),
        NoteItemTemplate(
            template_key="1.3",
            chapter=1,
            kind="background",
            label="为什么重要",
            description="问题价值、风险或现实影响。",
        ),
        NoteItemTemplate(
            template_key="1.4",
            chapter=1,
            kind="scenario",
            label="实际应用场景",
            description="方法成立或部署的真实场景。",
        ),
        NoteItemTemplate(
            template_key="1.5",
            chapter=1,
            kind="research_problem",
            label="问题形式化",
            description="输入、输出、目标、约束和假设。",
        ),
        NoteItemTemplate(
            template_key="2.1",
            chapter=2,
            kind="method",
            label="现有方法分类",
            description="已有路线及其核心思路。",
        ),
        NoteItemTemplate(
            template_key="2.2",
            chapter=2,
            kind="related_work",
            label="代表性顶会顶刊文献",
            description="经典工作的思路、缺点及与本文关系。",
            heading="2.2 代表性顶会顶刊文献（3–5篇）",
            repeatable=True,
            body_template="- 主要思路：\n- 主要缺点：\n- 与本文关系：",
        ),
        NoteItemTemplate(
            template_key="2.3",
            chapter=2,
            kind="challenge",
            label="现有方案的共同不足",
            description="已有工作仍未解决的共同问题。",
        ),
        NoteItemTemplate(
            template_key="2.4",
            chapter=2,
            kind="method",
            label="本文切入点",
            description="本文选择的突破口。",
        ),
        NoteItemTemplate(
            template_key="3.1",
            chapter=3,
            kind="method",
            label="核心思路",
            description="作者最核心的解决策略。",
        ),
        NoteItemTemplate(
            template_key="3.2",
            chapter=3,
            kind="method",
            label="整体框架",
            description="系统级组成与数据流。",
        ),
        NoteItemTemplate(
            template_key="3.3",
            chapter=3,
            kind="method_component",
            label="框架组成",
            description="模块、输入、处理、输出和作用。",
        ),
        NoteItemTemplate(
            template_key="3.4",
            chapter=3,
            kind="mechanism",
            label="与现有方法的核心区别",
            description="相对已有工作的机制差异。",
        ),
        NoteItemTemplate(
            template_key="4",
            chapter=4,
            kind="challenge",
            label="挑战",
            description="可重复添加需要克服的独立难点。",
            heading="4. 需要克服的挑战或难点",
            heading_level=2,
            repeatable=True,
            child_heading_prefix="挑战",
            body_template=(
                "- 为什么困难：\n- 现有方案为什么解决不好：\n- 本文如何处理：\n- 是否真正解决："
            ),
        ),
        NoteItemTemplate(
            template_key="5.1",
            chapter=5,
            kind="method",
            label="大致流程",
            description="方法的主要执行步骤。",
        ),
        NoteItemTemplate(
            template_key="5.innovation",
            chapter=5,
            kind="innovation",
            label="创新点",
            description="可重复添加的具体创新。",
            heading="5. 大致流程和创新点（3+1）",
            heading_level=2,
            repeatable=True,
            child_heading_prefix="创新点",
            insert_before_heading="5.5 附加贡献 +1",
            body_template=(
                "- 针对的挑战：\n"
                "- 做了什么：\n"
                "- 与已有工作的区别：\n"
                "- 为什么有效：\n"
                "- 哪个实验验证："
            ),
        ),
        NoteItemTemplate(
            template_key="5.5",
            chapter=5,
            kind="contribution",
            label="附加贡献",
            description="数据集、开源系统、评价框架或重要发现。",
        ),
        NoteItemTemplate(
            template_key="6",
            chapter=6,
            kind="method_component",
            label="具体流程和技术细节",
            description="按模板固定阶段填写模块、机制或实现步骤。",
        ),
        NoteItemTemplate(
            template_key="6.10",
            chapter=6,
            kind="mechanism",
            label="关键实现细节",
            description="缺失后会影响效果或复现的细节。",
        ),
        NoteItemTemplate(
            template_key="7.1",
            chapter=7,
            kind="experiment",
            label="实验研究问题",
            description="实验试图回答的 RQ。",
        ),
        NoteItemTemplate(
            template_key="7.2",
            chapter=7,
            kind="experiment",
            label="数据集与实验环境",
            description="数据、任务、硬件、软件和配置。",
        ),
        NoteItemTemplate(
            template_key="7.3",
            chapter=7,
            kind="experiment",
            label="对比基线",
            description="基线选择及其可比条件。",
        ),
        NoteItemTemplate(
            template_key="7.4",
            chapter=7,
            kind="experiment",
            label="评价指标",
            description="指标定义与统计口径。",
        ),
        NoteItemTemplate(
            template_key="7.5",
            chapter=7,
            kind="finding",
            label="主要实验结果",
            description="实验结论、关键数据和图表位置。",
        ),
        NoteItemTemplate(
            template_key="7.6",
            chapter=7,
            kind="finding",
            label="失败案例",
            description="失败现象、原因和边界。",
        ),
        NoteItemTemplate(
            template_key="7.7",
            chapter=7,
            kind="experiment",
            label="开源情况",
            description="源码、数据、Prompt、模型和环境。",
        ),
        NoteItemTemplate(
            template_key="8.1",
            chapter=8,
            kind="contribution",
            label="论文优点及证据",
            description="有证据支持的论文优点。",
        ),
        NoteItemTemplate(
            template_key="8.2",
            chapter=8,
            kind="author_limitation",
            label="作者承认的局限",
            description="作者明确说明的限制。",
        ),
        NoteItemTemplate(
            template_key="8.3",
            chapter=8,
            kind="reviewer_limitation",
            label="我发现的局限",
            description="阅读者判断的不足及依据。",
        ),
        NoteItemTemplate(
            template_key="8.4",
            chapter=8,
            kind="condition",
            label="结论成立的条件",
            description="适用范围、假设与失效边界。",
        ),
    )
    _FIXED_ITEM_TEMPLATES = tuple(
        NoteItemTemplate(
            template_key=template_key,
            chapter=chapter,
            kind=kind,  # type: ignore[arg-type]
            label=label,
            description=description,
            heading=heading,
            heading_level=heading_level,  # type: ignore[arg-type]
        )
        for (
            template_key,
            chapter,
            kind,
            label,
            description,
            heading,
            heading_level,
        ) in (
            ("1.1", 1, "background", "研究背景", "研究方向的背景与发展脉络。", "1.1 研究背景", 3),
            (
                "1.2",
                1,
                "research_problem",
                "具体问题",
                "论文试图解决的具体问题。",
                "1.2 具体问题",
                3,
            ),
            (
                "1.3",
                1,
                "background",
                "为什么重要",
                "问题的价值、风险或现实影响。",
                "1.3 为什么重要",
                3,
            ),
            (
                "1.4",
                1,
                "scenario",
                "实际应用场景",
                "方法成立或部署的真实场景。",
                "1.4 实际应用场景",
                3,
            ),
            (
                "1.5",
                1,
                "research_problem",
                "问题形式化",
                "输入、输出、目标、约束和假设。",
                "1.5 问题形式化",
                3,
            ),
            ("2.1", 2, "method", "现有方法分类", "已有路线及其核心思路。", "2.1 现有方法分类", 3),
            (
                "2.2.a",
                2,
                "related_work",
                "代表性文献 A",
                "第一篇代表性工作的思路、缺点及与本文关系。",
                "文献 A",
                4,
            ),
            (
                "2.2.b",
                2,
                "related_work",
                "代表性文献 B",
                "第二篇代表性工作的思路、缺点及与本文关系。",
                "文献 B",
                4,
            ),
            (
                "2.2.c",
                2,
                "related_work",
                "代表性文献 C",
                "第三篇代表性工作的思路、缺点及与本文关系。",
                "文献 C",
                4,
            ),
            (
                "2.3",
                2,
                "challenge",
                "现有方案的共同不足",
                "已有工作仍未解决的共同问题。",
                "2.3 现有方案的共同不足",
                3,
            ),
            ("2.4", 2, "method", "本文切入点", "本文选择的突破口。", "2.4 本文切入点", 3),
            ("3.1", 3, "method", "核心思路", "作者最核心的解决策略。", "3.1 核心思路", 3),
            ("3.2", 3, "method", "整体框架", "系统级组成与数据流。", "3.2 整体框架", 3),
            (
                "3.3",
                3,
                "method_component",
                "框架组成",
                "模块、输入、处理、输出和作用。",
                "3.3 框架组成",
                3,
            ),
            (
                "3.4",
                3,
                "mechanism",
                "与现有方法的核心区别",
                "相对已有工作的机制差异。",
                "3.4 与现有方法的核心区别",
                3,
            ),
            ("4.1", 4, "challenge", "挑战 1", "需要克服的第一项难点。", "挑战 1", 3),
            ("4.2", 4, "challenge", "挑战 2", "需要克服的第二项难点。", "挑战 2", 3),
            ("4.3", 4, "challenge", "挑战 3", "需要克服的第三项难点。", "挑战 3", 3),
            ("5.1", 5, "method", "大致流程", "方法的主要执行步骤。", "5.1 大致流程", 3),
            ("5.2", 5, "innovation", "创新点 1", "第一项核心创新。", "5.2 创新点 1", 3),
            ("5.3", 5, "innovation", "创新点 2", "第二项核心创新。", "5.3 创新点 2", 3),
            ("5.4", 5, "innovation", "创新点 3", "第三项核心创新。", "5.4 创新点 3", 3),
            (
                "5.5",
                5,
                "contribution",
                "附加贡献 +1",
                "数据集、系统、评价框架或重要发现。",
                "5.5 附加贡献 +1",
                3,
            ),
            (
                "6.1",
                6,
                "method_component",
                "输入与预处理",
                "输入形式与预处理步骤。",
                "6.1 输入与预处理",
                3,
            ),
            ("6.2", 6, "method_component", "任务规划", "任务拆分与规划机制。", "6.2 任务规划", 3),
            (
                "6.3",
                6,
                "method_component",
                "知识检索或 RAG",
                "知识来源与检索方式。",
                "6.3 知识检索或 RAG",
                3,
            ),
            (
                "6.4",
                6,
                "method_component",
                "Agent / 模型决策",
                "模型或 Agent 的决策机制。",
                "6.4 Agent / 模型决策",
                3,
            ),
            (
                "6.5",
                6,
                "method_component",
                "工具调用",
                "工具选择、参数与调用方式。",
                "6.5 工具调用",
                3,
            ),
            (
                "6.6",
                6,
                "method_component",
                "环境反馈处理",
                "环境反馈如何进入下一步。",
                "6.6 环境反馈处理",
                3,
            ),
            (
                "6.7",
                6,
                "method_component",
                "结果验证",
                "结果真实性与正确性验证。",
                "6.7 结果验证",
                3,
            ),
            (
                "6.8",
                6,
                "method_component",
                "失败恢复与重新规划",
                "失败后的重试、回滚与重新规划。",
                "6.8 失败恢复与重新规划",
                3,
            ),
            ("6.9", 6, "method_component", "输出结果", "系统最终输出及其形式。", "6.9 输出结果", 3),
            (
                "6.10",
                6,
                "mechanism",
                "关键实现细节",
                "影响效果或复现的关键细节。",
                "6.10 关键实现细节",
                3,
            ),
            (
                "7.1",
                7,
                "experiment",
                "实验研究问题",
                "实验试图回答的研究问题。",
                "7.1 实验研究问题",
                3,
            ),
            (
                "7.2",
                7,
                "experiment",
                "数据集与实验环境",
                "数据、任务、硬件、软件和配置。",
                "7.2 数据集与实验环境",
                3,
            ),
            ("7.3", 7, "experiment", "对比基线", "基线选择及其可比条件。", "7.3 对比基线", 3),
            ("7.4", 7, "experiment", "评价指标", "指标定义与统计口径。", "7.4 评价指标", 3),
            (
                "7.5",
                7,
                "finding",
                "主要实验结果",
                "实验结论、关键数据和图表位置。",
                "7.5 主要实验结果",
                3,
            ),
            ("7.6", 7, "finding", "失败案例", "失败现象、原因和边界。", "7.6 失败案例", 3),
            (
                "7.7",
                7,
                "experiment",
                "开源情况",
                "源码、数据、Prompt、模型和环境。",
                "7.7 开源情况",
                3,
            ),
            (
                "8.1",
                8,
                "contribution",
                "论文优点及证据",
                "有证据支持的论文优点。",
                "8.1 论文优点及证据",
                3,
            ),
            (
                "8.2",
                8,
                "author_limitation",
                "作者承认的局限",
                "作者明确说明的限制。",
                "8.2 作者承认的局限",
                3,
            ),
            (
                "8.3",
                8,
                "reviewer_limitation",
                "我发现的局限",
                "阅读者判断的不足及依据。",
                "8.3 我发现的局限",
                3,
            ),
            (
                "8.4",
                8,
                "condition",
                "结论成立的条件",
                "适用范围、假设与失效边界。",
                "8.4 结论成立的条件",
                3,
            ),
            (
                "8.5",
                8,
                "condition",
                "可靠性检查",
                "基线、数据、指标、成本和风险检查。",
                "8.5 可靠性检查",
                3,
            ),
        )
    )

    def __init__(
        self,
        workspace: WorkspaceService,
        schemas: SchemaRegistry,
        note_template_path: Path,
    ) -> None:
        self._workspace = workspace
        self._schemas = schemas
        self._note_template_path = note_template_path

    def _repositories(
        self,
    ) -> tuple[ProjectRepository, PaperRepository, PaperContentRepository]:
        self._workspace.require_workspace()
        return (
            ProjectRepository(self._workspace.root, self._schemas),
            PaperRepository(self._workspace.root, self._schemas),
            PaperContentRepository(self._workspace.root, self._schemas),
        )

    def get_note(self, project_id: UUID, paper_id: UUID) -> PaperNote:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        existing = content.load_note(project_id, paper_id)
        if existing is not None:
            return existing
        return PaperNote(
            paper_id=paper_id,
            markdown=self._initial_note_body(paper),
            revision=0,
            updated_at=datetime.now(UTC),
        )

    def initialize_note(self, project_id: UUID, paper: Paper) -> PaperNote:
        """Persist a metadata-seeded template exactly once when a paper is created."""
        projects, _, content = self._repositories()
        projects.load(project_id)
        existing = content.load_note(project_id, paper.paper_id)
        if existing is not None:
            return existing
        note = PaperNote(
            paper_id=paper.paper_id,
            markdown=self._initial_note_body(paper),
            revision=1,
            updated_at=datetime.now(UTC),
        )
        return content.save_note(project_id, note, expected_revision=0)

    def save_note(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        markdown: str,
        expected_revision: int,
    ) -> PaperNote:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        note = PaperNote(
            paper_id=paper_id,
            markdown=self._synchronize_basic_information(markdown, paper),
            revision=expected_revision + 1,
            updated_at=datetime.now(UTC),
        )
        return content.save_note(project_id, note, expected_revision=expected_revision)

    def sync_note_basic_information(self, project_id: UUID, paper: Paper) -> PaperNote:
        """Keep the non-item chapter 0 projection aligned with overview metadata."""
        _, _, content = self._repositories()
        current = content.load_note(project_id, paper.paper_id)
        if current is None:
            return self.initialize_note(project_id, paper)
        markdown = self._synchronize_basic_information(current.markdown, paper)
        if markdown == current.markdown:
            return current
        return content.save_note(
            project_id,
            current.model_copy(
                update={
                    "markdown": markdown,
                    "revision": current.revision + 1,
                    "updated_at": datetime.now(UTC),
                }
            ),
            expected_revision=current.revision,
        )

    def get_supplement(self, project_id: UUID, paper_id: UUID) -> PaperNote:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        papers.load(project_id, paper_id)
        existing = content.load_supplement(project_id, paper_id)
        if existing is not None:
            return existing
        return PaperNote(
            paper_id=paper_id,
            markdown="",
            revision=0,
            updated_at=datetime.now(UTC),
        )

    def save_supplement(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        markdown: str,
        expected_revision: int,
    ) -> PaperNote:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        papers.load(project_id, paper_id)
        note = PaperNote(
            paper_id=paper_id,
            markdown=markdown,
            revision=expected_revision + 1,
            updated_at=datetime.now(UTC),
        )
        return content.save_supplement(project_id, note, expected_revision=expected_revision)

    def get_questions(self, project_id: UUID, paper_id: UUID) -> QuestionsDocument:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        papers.load(project_id, paper_id)
        return content.load_questions(project_id, paper_id)

    def preview_note_analysis(self, project_id: UUID, paper_id: UUID) -> NoteParsePreview:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        note = content.load_note(project_id, paper_id)
        warnings: list[str] = []
        if note is None:
            note = self.get_note(project_id, paper_id)
            warnings.append("当前显示尚未保存的默认模板。请先填写并保存笔记后再解析分析候选。")
        candidates = parse_note_candidates(
            paper_id,
            note.markdown,
            paper.structured_summary.items,
        )
        removals = self._removal_candidates(paper, candidates)
        superseded_count = len(
            {item_id for candidate in candidates for item_id in candidate.superseded_item_ids}
        )
        if superseded_count:
            warnings.append(
                f"检测到 {superseded_count} 个旧版表格行条目; 确认整表候选后将合并为标题块条目。"
            )
        if not candidates and not warnings:
            warnings.append("没有找到已填写的结构化内容, 请检查模板标题和内容。")
        return NoteParsePreview(
            paper_id=paper_id,
            note_revision=note.revision,
            paper_revision=paper.revision,
            candidates=candidates,
            removals=removals,
            warnings=warnings,
        )

    def get_note_items(self, project_id: UUID, paper_id: UUID) -> NoteItemDocument:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        persisted_note = content.load_note(project_id, paper_id)
        note = persisted_note or self.get_note(project_id, paper_id)
        candidates = parse_note_candidates(
            paper_id,
            note.markdown,
            paper.structured_summary.items,
        )
        removals = self._removal_candidates(paper, candidates)
        warnings: list[str] = []
        if persisted_note is None:
            warnings.append("当前显示尚未保存的默认模板。填写任一模板条目时会自动保存。")
        superseded_ids = {
            item_id for candidate in candidates for item_id in candidate.superseded_item_ids
        }
        if superseded_ids:
            warnings.append(
                f"检测到 {len(superseded_ids)} 个旧版表格行条目; "
                "确认整表候选后将保留人工标签、写作用途和证据并完成合并。"
            )
        by_id = {candidate.candidate_id: candidate for candidate in candidates}
        sources: list[NoteItemSource] = []
        for item in paper.structured_summary.items:
            if item.item_id in superseded_ids:
                continue
            candidate = by_id.get(item.item_id)
            if candidate is None:
                sources.append(
                    NoteItemSource(
                        item_id=item.item_id,
                        kind=item.kind,
                        display_label=item.display_label,
                        title=item.title,
                        section_key=item.section_key,
                        section_title=item.section_title,
                        section_order=item.section_order,
                        markdown="",
                        source_fingerprint=item.source_fingerprint,
                        sync_status="missing",
                        is_favorite=item.is_favorite,
                    )
                )
                continue
            sources.append(
                NoteItemSource(
                    item_id=item.item_id,
                    kind=item.kind,
                    display_label=item.display_label,
                    title=item.title,
                    section_key=item.section_key,
                    section_title=item.section_title,
                    section_order=item.section_order,
                    markdown=note_item_fragment(note.markdown, candidate),
                    source_fingerprint=candidate.source_fingerprint,
                    sync_status=(
                        "synced"
                        if item.source_fingerprint == candidate.source_fingerprint
                        else "review_required"
                    ),
                    is_favorite=item.is_favorite,
                )
            )
        pending = sum(candidate.sync_status != "unchanged" for candidate in candidates) + len(
            removals
        )
        return NoteItemDocument(
            paper_id=paper_id,
            note_revision=note.revision,
            paper_revision=paper.revision,
            item_templates=[item for item in self._ITEM_TEMPLATES if item.repeatable],
            slots=self._note_slots(note, paper, candidates),
            evidence_catalog=paper.structured_summary.evidence_catalog,
            items=sources,
            candidates=candidates,
            removals=removals,
            warnings=warnings,
            pending_candidate_count=pending,
        )

    def create_note_item(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        template_key: str,
        title: str,
        markdown: str,
        expected_note_revision: int,
        expected_paper_revision: int,
    ) -> NoteItemUpdateResult:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        self._check_revisions(
            paper,
            content.load_note(project_id, paper_id),
            expected_paper_revision=expected_paper_revision,
            expected_note_revision=expected_note_revision,
        )
        note = content.load_note(project_id, paper_id) or self.get_note(project_id, paper_id)
        template = next(
            (
                item
                for item in self._ITEM_TEMPLATES
                if item.template_key == template_key and item.repeatable
            ),
            None,
        )
        if template is None:
            raise AnalysisItemSourceError("该模板位置是固定填写项，不能继续新增。")
        item_id = uuid4()
        updated_markdown = append_repeatable_note_item(
            note.markdown,
            item_id=item_id,
            parent_heading=template.heading,
            parent_heading_level=template.heading_level,
            title=title,
            body=markdown,
            child_heading_prefix=template.child_heading_prefix,
            insert_before_heading=template.insert_before_heading,
        )
        if updated_markdown == note.markdown:
            raise AnalysisItemSourceError("结构化笔记缺少对应模板章节，未写入任何文件。")
        candidates = parse_note_candidates(
            paper_id,
            updated_markdown,
            paper.structured_summary.items,
        )
        candidate = next(
            (item for item in candidates if item.candidate_id == item_id),
            None,
        )
        if candidate is None or candidate.kind != template.kind:
            raise AnalysisItemSourceError("新条目无法映射到所选模板章节，未写入任何文件。")
        updated_note = content.save_note(
            project_id,
            note.model_copy(
                update={
                    "markdown": updated_markdown,
                    "revision": note.revision + 1,
                    "updated_at": datetime.now(UTC),
                }
            ),
            expected_revision=expected_note_revision,
        )
        created = self._item_from_new_candidate(
            candidate,
            source_note_revision=updated_note.revision,
            superseded_items=[],
        )
        updated_paper = paper.model_copy(
            update={
                "structured_summary": paper.structured_summary.model_copy(
                    update={"items": [*paper.structured_summary.items, created]}
                ),
                "revision": paper.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        updated_paper = papers.save(updated_paper, expected_revision=expected_paper_revision)
        return NoteItemUpdateResult(
            note=updated_note,
            analysis=self._analysis_document(updated_paper),
            item=created,
        )

    def update_note_slot(
        self,
        project_id: UUID,
        paper_id: UUID,
        template_key: str,
        *,
        markdown: str,
        expected_note_revision: int,
        expected_paper_revision: int,
    ) -> NoteSlotUpdateResult:
        """Fill one fixed template position in place and synchronize its projection."""
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        persisted_note = content.load_note(project_id, paper_id)
        self._check_revisions(
            paper,
            persisted_note,
            expected_paper_revision=expected_paper_revision,
            expected_note_revision=expected_note_revision,
        )
        note = persisted_note or self.get_note(project_id, paper_id)
        template = next(
            (item for item in self._FIXED_ITEM_TEMPLATES if item.template_key == template_key),
            None,
        )
        if template is None:
            raise AnalysisItemSourceError("模板填写项不存在，请刷新后重试。")
        before = parse_note_candidates(
            paper_id,
            note.markdown,
            paper.structured_summary.items,
        )
        current = self._candidate_for_template(before, template)
        existing_id = (
            current.duplicate_item_id
            if current is not None and current.duplicate_item_id is not None
            else current.candidate_id
            if current is not None
            and (
                f"<!-- papermatrix:item:{current.candidate_id} -->" in note.markdown
                or any(
                    item.item_id == current.candidate_id for item in paper.structured_summary.items
                )
            )
            else None
        )
        item_id = existing_id or uuid5(
            NAMESPACE_URL,
            f"papermatrix:slot:{paper_id}:{template.template_key}",
        )
        source_markdown = note.markdown
        if current is not None and current.source_section != template.heading:
            source_markdown = remove_note_item_fragments(
                source_markdown,
                {current.candidate_id},
            )
        updated_markdown = replace_note_template_slot(
            source_markdown,
            heading=template.heading,
            heading_level=template.heading_level,
            item_id=item_id,
            body=markdown,
        )
        if updated_markdown == note.markdown and markdown.strip() != note_template_slot_fragment(
            note.markdown,
            heading=template.heading,
            heading_level=template.heading_level,
        ):
            raise AnalysisItemSourceError("模板填写项不存在，未写入任何文件。")
        parsed = parse_note_candidates(
            paper_id,
            updated_markdown,
            paper.structured_summary.items,
        )
        updated_candidate = next(
            (candidate for candidate in parsed if candidate.candidate_id == item_id),
            None,
        )
        if updated_candidate is not None and updated_candidate.kind != template.kind:
            raise AnalysisItemSourceError("填写内容无法保留模板条目类型，未写入任何文件。")
        updated_note = content.save_note(
            project_id,
            note.model_copy(
                update={
                    "markdown": updated_markdown,
                    "revision": note.revision + 1,
                    "updated_at": datetime.now(UTC),
                }
            ),
            expected_revision=expected_note_revision,
        )
        existing = next(
            (item for item in paper.structured_summary.items if item.item_id == item_id),
            None,
        )
        items = [item for item in paper.structured_summary.items if item.item_id != item_id]
        updated_item = None
        if updated_candidate is not None:
            updated_item = (
                self._item_from_candidate(
                    existing,
                    updated_candidate,
                    source_note_revision=updated_note.revision,
                )
                if existing is not None
                else self._item_from_new_candidate(
                    updated_candidate,
                    source_note_revision=updated_note.revision,
                    superseded_items=[],
                )
            )
            items.append(updated_item)
        updated_paper = paper.model_copy(
            update={
                "structured_summary": paper.structured_summary.model_copy(update={"items": items}),
                "revision": paper.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        updated_paper = papers.save(updated_paper, expected_revision=expected_paper_revision)
        refreshed_candidates = parse_note_candidates(
            paper_id,
            updated_note.markdown,
            updated_paper.structured_summary.items,
        )
        slot = next(
            slot
            for slot in self._note_slots(
                updated_note,
                updated_paper,
                refreshed_candidates,
            )
            if slot.template_key == template_key
        )
        return NoteSlotUpdateResult(
            note=updated_note,
            analysis=self._analysis_document(updated_paper),
            slot=slot,
            item=updated_item,
        )

    def create_evidence(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        item_id: UUID | None,
        evidence_type: str,
        page_label: str | None,
        pdf_page_index: int | None,
        section: str | None,
        figure: str | None,
        table: str | None,
        locator_note: str,
        expected_note_revision: int,
        expected_paper_revision: int,
    ) -> EvidenceCreateResult:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        note = content.load_note(project_id, paper_id)
        self._check_revisions(
            paper,
            note,
            expected_paper_revision=expected_paper_revision,
            expected_note_revision=expected_note_revision,
        )
        note = note or self.get_note(project_id, paper_id)
        existing_item = None
        if item_id is not None:
            existing_item = next(
                (item for item in paper.structured_summary.items if item.item_id == item_id),
                None,
            )
            if existing_item is None:
                raise AnalysisItemNotFoundError()
        evidence_code = self._next_evidence_code(
            paper.structured_summary.evidence_catalog,
            note.markdown,
        )
        evidence = EvidenceReference(
            evidence_id=uuid5(
                NAMESPACE_URL,
                f"papermatrix:evidence:{paper_id}:{evidence_code}",
            ),
            evidence_code=evidence_code,
            paper_id=paper_id,
            page_label=self._clean_optional(page_label),
            pdf_page_index=pdf_page_index,
            section=self._clean_optional(section),
            figure=self._clean_optional(figure),
            table=self._clean_optional(table),
            locator_note=locator_note.strip(),
        )
        updated_markdown = append_evidence_row(
            note.markdown,
            evidence,
            evidence_type=evidence_type.strip(),
        )
        updated_item = None
        if existing_item is not None:
            candidates = parse_note_candidates(
                paper_id,
                updated_markdown,
                paper.structured_summary.items,
            )
            current = next(
                (candidate for candidate in candidates if candidate.candidate_id == item_id),
                None,
            )
            if current is None:
                raise AnalysisItemSourceError()
            if current.source_fingerprint != existing_item.source_fingerprint:
                raise AnalysisItemSourceError(
                    "当前条目正文存在待审阅变化，请先完成差异审阅再关联证据。"
                )
            updated_markdown = append_item_evidence_reference(
                updated_markdown,
                current,
                evidence.evidence_code or "",
            )
        parsed = parse_note_candidates(
            paper_id,
            updated_markdown,
            paper.structured_summary.items,
        )
        updated_note = content.save_note(
            project_id,
            note.model_copy(
                update={
                    "markdown": updated_markdown,
                    "revision": note.revision + 1,
                    "updated_at": datetime.now(UTC),
                }
            ),
            expected_revision=expected_note_revision,
        )
        items = list(paper.structured_summary.items)
        if existing_item is not None:
            candidate = next(
                (candidate for candidate in parsed if candidate.candidate_id == item_id),
                None,
            )
            if candidate is None:
                raise AnalysisItemSourceError()
            updated_item = self._item_from_candidate(
                existing_item,
                candidate,
                source_note_revision=updated_note.revision,
            )
            items = [
                updated_item if item.item_id == updated_item.item_id else item for item in items
            ]
        updated_paper = paper.model_copy(
            update={
                "structured_summary": paper.structured_summary.model_copy(
                    update={
                        "evidence_catalog": [
                            *paper.structured_summary.evidence_catalog,
                            evidence,
                        ],
                        "items": items,
                    }
                ),
                "revision": paper.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        updated_paper = papers.save(updated_paper, expected_revision=expected_paper_revision)
        return EvidenceCreateResult(
            note=updated_note,
            analysis=self._analysis_document(updated_paper),
            evidence=evidence,
            item=updated_item,
        )

    def update_note_item(
        self,
        project_id: UUID,
        paper_id: UUID,
        item_id: UUID,
        *,
        markdown: str,
        expected_note_revision: int,
        expected_paper_revision: int,
        expected_source_fingerprint: str,
    ) -> NoteItemUpdateResult:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        if paper.revision != expected_paper_revision:
            raise AnalysisPreviewStaleError(
                resource="paper",
                expected=expected_paper_revision,
                actual=paper.revision,
            )
        existing = next(
            (item for item in paper.structured_summary.items if item.item_id == item_id),
            None,
        )
        if existing is None:
            raise AnalysisItemNotFoundError()
        note = content.load_note(project_id, paper_id)
        if note is None:
            raise AnalysisItemSourceError("结构化笔记尚未保存, 无法编辑条目来源。")
        if note.revision != expected_note_revision:
            raise AnalysisPreviewStaleError(
                resource="note",
                expected=expected_note_revision,
                actual=note.revision,
            )
        candidates = parse_note_candidates(
            paper_id,
            note.markdown,
            paper.structured_summary.items,
        )
        current = next(
            (candidate for candidate in candidates if candidate.candidate_id == item_id),
            None,
        )
        if current is None:
            raise AnalysisItemSourceError()
        if current.source_fingerprint != expected_source_fingerprint:
            raise AnalysisPreviewStaleError(
                resource="item_source",
                expected=expected_note_revision,
                actual=note.revision,
            )

        updated_markdown = replace_note_item_fragment(note.markdown, item_id, markdown)
        if updated_markdown == note.markdown and markdown.strip() != note_item_fragment(
            note.markdown, current
        ):
            raise AnalysisItemSourceError()
        parsed = parse_note_candidates(
            paper_id,
            updated_markdown,
            paper.structured_summary.items,
        )
        updated_candidate = next(
            (candidate for candidate in parsed if candidate.candidate_id == item_id),
            None,
        )
        if updated_candidate is None or updated_candidate.kind != existing.kind:
            raise AnalysisItemSourceError("条目修改后无法保留原类型和稳定 ID, 未写入任何文件。")

        updated_note = content.save_note(
            project_id,
            note.model_copy(
                update={
                    "markdown": updated_markdown,
                    "revision": note.revision + 1,
                    "updated_at": datetime.now(UTC),
                }
            ),
            expected_revision=expected_note_revision,
        )
        updated_item = self._item_from_candidate(
            existing,
            updated_candidate,
            source_note_revision=updated_note.revision,
        )
        items = [
            updated_item if item.item_id == item_id else item
            for item in paper.structured_summary.items
        ]
        updated_paper = paper.model_copy(
            update={
                "structured_summary": paper.structured_summary.model_copy(update={"items": items}),
                "revision": paper.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        updated_paper = papers.save(updated_paper, expected_revision=expected_paper_revision)
        return NoteItemUpdateResult(
            note=updated_note,
            analysis=self._analysis_document(updated_paper),
            item=updated_item,
        )

    def update_note_item_favorite(
        self,
        project_id: UUID,
        paper_id: UUID,
        item_id: UUID,
        *,
        is_favorite: bool,
        expected_paper_revision: int,
    ) -> NoteItemFavoriteUpdateResult:
        projects, papers, _ = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        if paper.revision != expected_paper_revision:
            raise AnalysisPreviewStaleError(
                resource="paper",
                expected=expected_paper_revision,
                actual=paper.revision,
            )
        existing = next(
            (item for item in paper.structured_summary.items if item.item_id == item_id),
            None,
        )
        if existing is None:
            raise AnalysisItemNotFoundError()
        updated_item = existing.model_copy(
            update={"is_favorite": is_favorite, "updated_at": datetime.now(UTC)}
        )
        updated = paper.model_copy(
            update={
                "structured_summary": paper.structured_summary.model_copy(
                    update={
                        "items": [
                            updated_item if item.item_id == item_id else item
                            for item in paper.structured_summary.items
                        ]
                    }
                ),
                "revision": paper.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        saved = papers.save(updated, expected_revision=expected_paper_revision)
        return NoteItemFavoriteUpdateResult(
            analysis=self._analysis_document(saved),
            item=updated_item,
        )

    def import_note_candidates(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        candidate_ids: list[UUID],
        removal_item_ids: list[UUID],
        expected_note_revision: int,
        expected_paper_revision: int,
    ) -> CandidateImportResult:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        if paper.revision != expected_paper_revision:
            raise AnalysisPreviewStaleError(
                resource="paper",
                expected=expected_paper_revision,
                actual=paper.revision,
            )
        note = content.load_note(project_id, paper_id)
        actual_note_revision = note.revision if note else 0
        if actual_note_revision != expected_note_revision:
            raise AnalysisPreviewStaleError(
                resource="note",
                expected=expected_note_revision,
                actual=actual_note_revision,
            )
        if note is None:
            note = self.get_note(project_id, paper_id)
        candidates = parse_note_candidates(
            paper_id,
            note.markdown,
            paper.structured_summary.items,
        )
        removals = self._removal_candidates(paper, candidates)
        by_id = {candidate.candidate_id: candidate for candidate in candidates}
        unknown = [str(candidate_id) for candidate_id in candidate_ids if candidate_id not in by_id]
        if unknown:
            raise AnalysisCandidateSelectionError(unknown)
        removal_ids = {item.item_id for item in removals}
        unknown_removals = [
            str(item_id) for item_id in removal_item_ids if item_id not in removal_ids
        ]
        if unknown_removals:
            raise AnalysisCandidateSelectionError(unknown_removals)

        imported: list[AnalysisItem] = []
        skipped: list[UUID] = []
        existing_ids = {item.item_id for item in paper.structured_summary.items}
        selected_candidates = []
        synchronized: list[tuple[AnalysisItem, NoteAnalysisCandidate]] = []
        for candidate_id in dict.fromkeys(candidate_ids):
            candidate = by_id[candidate_id]
            existing = next(
                (item for item in paper.structured_summary.items if item.item_id == candidate_id),
                None,
            )
            if existing is not None and candidate.sync_status == "modified":
                synchronized.append((existing, candidate))
                continue
            if candidate.duplicate_item_id is not None or candidate_id in existing_ids:
                skipped.append(candidate_id)
                continue
            selected_candidates.append(candidate)
        superseded_ids = {
            item_id
            for candidate in selected_candidates
            for item_id in candidate.superseded_item_ids
        }
        superseded_items = [
            item for item in paper.structured_summary.items if item.item_id in superseded_ids
        ]
        ordered_deleted_ids = list(dict.fromkeys(removal_item_ids))
        deleted_ids = set(ordered_deleted_ids)
        consolidated_markdown = remove_item_anchors(
            note.markdown,
            superseded_ids | deleted_ids,
        )
        anchored_markdown = add_item_anchors(consolidated_markdown, selected_candidates)
        if anchored_markdown != note.markdown:
            note = content.save_note(
                project_id,
                note.model_copy(
                    update={
                        "markdown": anchored_markdown,
                        "revision": note.revision + 1,
                        "updated_at": datetime.now(UTC),
                    }
                ),
                expected_revision=expected_note_revision,
            )
        for candidate in selected_candidates:
            imported.append(
                self._item_from_new_candidate(
                    candidate,
                    source_note_revision=note.revision,
                    superseded_items=[
                        item
                        for item in superseded_items
                        if item.item_id in candidate.superseded_item_ids
                    ],
                )
            )
        synchronized_items = [
            self._item_from_candidate(existing, candidate, source_note_revision=note.revision)
            for existing, candidate in synchronized
        ]
        if imported or synchronized_items or deleted_ids:
            synchronized_by_id = {item.item_id: item for item in synchronized_items}
            existing_items = [
                synchronized_by_id.get(item.item_id, item)
                for item in paper.structured_summary.items
                if item.item_id not in superseded_ids | deleted_ids
            ]
            evidence_catalog = self._merge_evidence_catalog(
                paper.structured_summary.evidence_catalog,
                [
                    reference
                    for candidate in [*selected_candidates, *(item[1] for item in synchronized)]
                    for reference in candidate.evidence_refs
                ],
            )
            updated = paper.model_copy(
                update={
                    "structured_summary": paper.structured_summary.model_copy(
                        update={
                            "items": [*existing_items, *imported],
                            "evidence_catalog": evidence_catalog,
                        }
                    ),
                    "revision": paper.revision + 1,
                    "updated_at": datetime.now(UTC),
                }
            )
            paper = papers.save(updated, expected_revision=expected_paper_revision)
        return CandidateImportResult(
            analysis=self._analysis_document(paper),
            note=note,
            imported_items=imported,
            synchronized_items=synchronized_items,
            skipped_candidate_ids=skipped,
            superseded_item_ids=list(superseded_ids),
            deleted_item_ids=ordered_deleted_ids,
        )

    def delete_note_items(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        item_ids: list[UUID],
        expected_note_revision: int,
        expected_paper_revision: int,
    ) -> NoteItemDeleteResult:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        paper = papers.load(project_id, paper_id)
        if paper.revision != expected_paper_revision:
            raise AnalysisPreviewStaleError(
                resource="paper",
                expected=expected_paper_revision,
                actual=paper.revision,
            )
        note = content.load_note(project_id, paper_id)
        actual_note_revision = note.revision if note else 0
        if actual_note_revision != expected_note_revision:
            raise AnalysisPreviewStaleError(
                resource="note",
                expected=expected_note_revision,
                actual=actual_note_revision,
            )
        ordered_item_ids = list(dict.fromkeys(item_ids))
        selected_ids = set(ordered_item_ids)
        existing_ids = {item.item_id for item in paper.structured_summary.items}
        unknown = [str(item_id) for item_id in selected_ids if item_id not in existing_ids]
        if unknown:
            raise AnalysisCandidateSelectionError(unknown)

        if note is None:
            note = self.get_note(project_id, paper_id)
        updated_markdown = remove_note_item_fragments(note.markdown, selected_ids)
        if updated_markdown != note.markdown:
            note = content.save_note(
                project_id,
                note.model_copy(
                    update={
                        "markdown": updated_markdown,
                        "revision": note.revision + 1,
                        "updated_at": datetime.now(UTC),
                    }
                ),
                expected_revision=expected_note_revision,
            )
        remaining = [
            item for item in paper.structured_summary.items if item.item_id not in selected_ids
        ]
        updated = paper.model_copy(
            update={
                "structured_summary": paper.structured_summary.model_copy(
                    update={"items": remaining}
                ),
                "revision": paper.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        paper = papers.save(updated, expected_revision=expected_paper_revision)
        return NoteItemDeleteResult(
            note=note,
            analysis=self._analysis_document(paper),
            deleted_item_ids=ordered_item_ids,
        )

    @staticmethod
    def _item_from_new_candidate(
        candidate: NoteAnalysisCandidate,
        *,
        source_note_revision: int,
        superseded_items: list[AnalysisItem],
    ) -> AnalysisItem:
        now = datetime.now(UTC)
        evidence_ids = [reference.evidence_id for reference in candidate.evidence_refs]
        for item in superseded_items:
            evidence_ids.extend(item.evidence_ids)
        tags = list(
            dict.fromkeys(
                [
                    *(tag for item in superseded_items for tag in item.tags),
                ]
            )
        )
        writing_uses = list(
            dict.fromkeys(
                writing_use for item in superseded_items for writing_use in item.writing_uses
            )
        )
        created_at = min(
            (item.created_at for item in superseded_items),
            default=now,
        )
        return AnalysisItem(
            item_id=candidate.candidate_id,
            kind=candidate.kind,
            display_label=None,
            title=candidate.title,
            summary=candidate.summary,
            section_key=candidate.section_key,
            section_title=candidate.section_title,
            section_order=candidate.section_order,
            source_anchor=candidate.source_anchor,
            source_note_revision=source_note_revision,
            source_fingerprint=candidate.source_fingerprint,
            attributes=candidate.attributes,
            evidence_ids=list(dict.fromkeys(evidence_ids)),
            tags=tags,
            writing_uses=writing_uses,
            is_favorite=any(item.is_favorite for item in superseded_items),
            created_at=created_at,
            updated_at=now,
        )

    @staticmethod
    def _item_from_candidate(
        existing: AnalysisItem,
        candidate: NoteAnalysisCandidate,
        *,
        source_note_revision: int,
    ) -> AnalysisItem:
        return existing.model_copy(
            update={
                "kind": candidate.kind,
                "display_label": existing.display_label,
                "title": candidate.title,
                "summary": candidate.summary,
                "section_key": candidate.section_key,
                "section_title": candidate.section_title,
                "section_order": candidate.section_order,
                "source_anchor": candidate.source_anchor,
                "source_note_revision": source_note_revision,
                "source_fingerprint": candidate.source_fingerprint,
                "attributes": candidate.attributes,
                "evidence_ids": [reference.evidence_id for reference in candidate.evidence_refs],
                "updated_at": datetime.now(UTC),
            }
        )

    def create_question(
        self,
        project_id: UUID,
        paper_id: UUID,
        *,
        question: str,
        status: QuestionStatus,
        answer: str,
        evidence: list[EvidenceReference],
        tags: list[str],
        expected_revision: int,
    ) -> QuestionsDocument:
        document, content = self._question_context(project_id, paper_id)
        item = ReadingQuestion.create(
            paper_id=paper_id,
            question=question,
            status=status,
            answer=answer,
            evidence=self._normalize_evidence(paper_id, evidence),
            tags=self._clean_tags(tags),
        )
        updated = document.model_copy(
            update={
                "questions": [*document.questions, item],
                "revision": document.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        return content.save_questions(project_id, updated, expected_revision=expected_revision)

    def update_question(
        self,
        project_id: UUID,
        paper_id: UUID,
        question_id: UUID,
        *,
        question: str,
        status: QuestionStatus,
        answer: str,
        evidence: list[EvidenceReference],
        tags: list[str],
        expected_revision: int,
    ) -> QuestionsDocument:
        document, content = self._question_context(project_id, paper_id)
        found = False
        questions: list[ReadingQuestion] = []
        for item in document.questions:
            if item.question_id != question_id:
                questions.append(item)
                continue
            found = True
            questions.append(
                ReadingQuestion.model_validate(
                    {
                        **item.model_dump(),
                        "question": question.strip(),
                        "status": status,
                        "answer": answer.strip(),
                        "evidence": self._normalize_evidence(paper_id, evidence),
                        "tags": self._clean_tags(tags),
                        "updated_at": datetime.now(UTC),
                    }
                )
            )
        if not found:
            raise QuestionNotFoundError()
        updated = document.model_copy(
            update={
                "questions": questions,
                "revision": document.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        return content.save_questions(project_id, updated, expected_revision=expected_revision)

    def delete_question(
        self,
        project_id: UUID,
        paper_id: UUID,
        question_id: UUID,
        *,
        expected_revision: int,
    ) -> QuestionsDocument:
        document, content = self._question_context(project_id, paper_id)
        questions = [item for item in document.questions if item.question_id != question_id]
        if len(questions) == len(document.questions):
            raise QuestionNotFoundError()
        updated = document.model_copy(
            update={
                "questions": questions,
                "revision": document.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        return content.save_questions(project_id, updated, expected_revision=expected_revision)

    def _question_context(
        self, project_id: UUID, paper_id: UUID
    ) -> tuple[QuestionsDocument, PaperContentRepository]:
        projects, papers, content = self._repositories()
        projects.load(project_id)
        papers.load(project_id, paper_id)
        return content.load_questions(project_id, paper_id), content

    def _note_slots(
        self,
        note: PaperNote,
        paper: Paper,
        candidates: list[NoteAnalysisCandidate],
    ) -> list[NoteItemSlot]:
        existing_by_id = {item.item_id: item for item in paper.structured_summary.items}
        chapter_titles = {
            1: "1. 背景：解决什么问题？为什么重要？",
            2: "2. 现有方案分类和经典文献",
            3: "3. 本文解决思路和整体框架",
            4: "4. 需要克服的挑战或难点",
            5: "5. 大致流程和创新点（3+1）",
            6: "6. 具体流程和技术细节",
            7: "7. 实验与复现性",
            8: "8. 批判性评价",
        }
        slots: list[NoteItemSlot] = []
        slot_positions: dict[str, int] = {}
        fixed_headings = {item.heading for item in self._FIXED_ITEM_TEMPLATES}
        repeatable_seed_keys = {
            "2.2.a": "2.2",
            "2.2.b": "2.2",
            "2.2.c": "2.2",
            "4.1": "4",
            "4.2": "4",
            "4.3": "4",
            "5.2": "5.innovation",
            "5.3": "5.innovation",
            "5.4": "5.innovation",
        }
        for template in self._FIXED_ITEM_TEMPLATES:
            candidate = self._candidate_for_template(candidates, template)
            existing = None
            if candidate is not None:
                existing = existing_by_id.get(candidate.duplicate_item_id or candidate.candidate_id)
            heading_pattern = re.compile(
                rf"(?m)^{'#' * template.heading_level}\s+"
                rf"{re.escape(template.heading)}\s*$"
            )
            heading_match = heading_pattern.search(note.markdown)
            heading_exists = heading_match is not None
            sync_status: Literal["empty", "synced", "review_required", "missing"]
            if not heading_exists:
                sync_status = "missing"
            elif candidate is None:
                sync_status = "empty"
            elif candidate.source_section != template.heading:
                sync_status = "review_required"
            elif (
                existing is not None and existing.source_fingerprint == candidate.source_fingerprint
            ):
                sync_status = "synced"
            else:
                sync_status = "review_required"
            slot = NoteItemSlot(
                slot_key=template.template_key,
                template_key=template.template_key,
                kind=template.kind,
                label=template.label,
                description=template.description,
                section_title=chapter_titles[template.chapter],
                markdown=(
                    self._legacy_candidate_body(note.markdown, candidate)
                    if candidate is not None and candidate.source_section != template.heading
                    else note_template_slot_fragment(
                        note.markdown,
                        heading=template.heading,
                        heading_level=template.heading_level,
                    )
                ),
                item_id=existing.item_id if existing is not None else None,
                source_fingerprint=(
                    candidate.source_fingerprint if candidate is not None else None
                ),
                sync_status=sync_status,
                is_favorite=existing.is_favorite if existing is not None else False,
                repeatable_template_key=repeatable_seed_keys.get(template.template_key),
            )
            slots.append(slot)
            slot_positions[slot.slot_key] = (
                note.markdown.count("\n", 0, heading_match.start()) + 1
                if heading_match is not None
                else 1_000_000 + len(slots)
            )
        repeatable_templates = [item for item in self._ITEM_TEMPLATES if item.repeatable]
        for candidate in candidates:
            if candidate.source_section in fixed_headings:
                continue
            repeatable_template = next(
                (
                    item
                    for item in repeatable_templates
                    if self._candidate_matches_repeatable_template(candidate, item)
                ),
                None,
            )
            if repeatable_template is None:
                continue
            existing = existing_by_id.get(candidate.duplicate_item_id or candidate.candidate_id)
            slot = NoteItemSlot(
                slot_key=f"{repeatable_template.template_key}:{candidate.candidate_id}",
                template_key=repeatable_template.template_key,
                kind=repeatable_template.kind,
                label=candidate.title,
                description=repeatable_template.description,
                section_title=chapter_titles[repeatable_template.chapter],
                markdown=note_item_fragment(note.markdown, candidate),
                item_id=existing.item_id if existing is not None else None,
                source_fingerprint=candidate.source_fingerprint,
                sync_status=(
                    "synced"
                    if existing is not None
                    and existing.source_fingerprint == candidate.source_fingerprint
                    else "review_required"
                ),
                is_favorite=existing.is_favorite if existing is not None else False,
                repeatable=True,
                repeatable_template_key=repeatable_template.template_key,
                can_delete=existing is not None,
            )
            slots.append(slot)
            slot_positions[slot.slot_key] = candidate.source_line_start
        return sorted(slots, key=lambda item: slot_positions[item.slot_key])

    @staticmethod
    def _candidate_matches_repeatable_template(
        candidate: NoteAnalysisCandidate,
        template: NoteItemTemplate,
    ) -> bool:
        if (
            candidate.kind != template.kind
            or candidate.section_key != f"section-{template.chapter}"
        ):
            return False
        if template.template_key == "2.2":
            return candidate.source_section not in {"文献 A", "文献 B", "文献 C"}
        prefix = template.child_heading_prefix
        return bool(prefix) and candidate.source_section.startswith(
            (f"{prefix}:", f"{prefix}\uff1a")
        )

    @staticmethod
    def _candidate_for_template(
        candidates: list[NoteAnalysisCandidate],
        template: NoteItemTemplate,
    ) -> NoteAnalysisCandidate | None:
        exact = next(
            (
                item
                for item in candidates
                if item.source_section == template.heading and item.kind == template.kind
            ),
            None,
        )
        if exact is not None:
            return exact
        legacy_prefixes = (f"{template.label}:", f"{template.label}：")
        matches = [
            item
            for item in candidates
            if item.kind == template.kind
            and item.section_key == f"section-{template.chapter}"
            and item.source_section.startswith(legacy_prefixes)
        ]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _legacy_candidate_body(
        markdown: str,
        candidate: NoteAnalysisCandidate,
    ) -> str:
        fragment = note_item_fragment(markdown, candidate)
        lines = fragment.splitlines()
        body = "\n".join(lines[1:]).strip() if lines else ""
        return re.sub(r"\n+---\s*$", "", body).strip()

    def _initial_note_body(self, paper: Paper) -> str:
        template = self._note_template_path.read_text(encoding="utf-8")
        _, body = PaperContentRepository._parse_note(
            template.replace("{{ paper_id }}", str(paper.paper_id))
            .replace("{{ updated_at }}", datetime.now(UTC).isoformat())
            .replace(
                "{{ short_title }}",
                paper.bibliography.short_title or paper.bibliography.title,
            )
        )
        return self._synchronize_basic_information(body, paper)

    def _synchronize_basic_information(self, body: str, paper: Paper) -> str:
        if re.search(r"(?m)^## 0(?:[.、]\s*|\s+)基本信息\s*$", body) is None:
            return body
        bibliography = paper.bibliography
        organization = paper.organization
        publication_date = (
            bibliography.publication_date.isoformat()
            if bibliography.publication_date
            else str(bibliography.year or "")
        )
        reading_status = {
            "unread": "未读",
            "skimmed": "粗读",
            "deep_read": "精读",
            "summarized": "已总结",
            "reported": "已汇报",
        }[organization.reading_status]
        values: dict[str, str] = {
            "完整标题": bibliography.title,
            "作者": "，".join(bibliography.authors),
            "署名单位": "，".join(bibliography.affiliations),
            "发表载体（会议/期刊/平台）": bibliography.venue or "",
            "发表时间": publication_date,
            "被引次数": (
                str(bibliography.citation_count) if bibliography.citation_count is not None else ""
            ),
            "语言": bibliography.language or "",
            "关键词": "，".join(bibliography.keywords),
            "项目内分组": organization.group or "",
            "论文链接": bibliography.urls[0] if bibliography.urls else "",
            "代码链接": bibliography.code_url or "",
            "数据链接": bibliography.data_url or "",
            "阅读日期": (
                organization.reading_date.isoformat() if organization.reading_date else ""
            ),
            "阅读状态": reading_status,
            "重要程度": (
                str(organization.importance_score)
                if organization.importance_score is not None
                else ""
            ),
            "一句话总结": organization.one_sentence_summary,
            "摘要": bibliography.abstract_text,
        }
        for label, value in values.items():
            body = self._replace_template_field(body, label, value)
        title = bibliography.short_title or bibliography.title
        body = re.sub(r"(?m)^# .+$", f"# {' '.join(title.split())}", body, count=1)
        return body

    @staticmethod
    def _replace_template_field(markdown: str, label: str, value: str) -> str:
        normalized = " ".join(value.split())
        pattern = re.compile(rf"(?m)^- {re.escape(label)}：.*$")
        return pattern.sub(f"- {label}：{normalized}", markdown, count=1)

    @staticmethod
    def _removal_candidates(
        paper: Paper,
        candidates: list[NoteAnalysisCandidate],
    ) -> list[NoteAnalysisRemoval]:
        candidate_ids = {candidate.candidate_id for candidate in candidates}
        superseded_ids = {
            item_id for candidate in candidates for item_id in candidate.superseded_item_ids
        }
        return [
            NoteAnalysisRemoval(
                item_id=item.item_id,
                kind=item.kind,
                title=item.title,
                section_key=item.section_key,
                section_title=item.section_title,
                section_order=item.section_order,
            )
            for item in paper.structured_summary.items
            if item.source_anchor is not None
            and item.item_id not in candidate_ids
            and item.item_id not in superseded_ids
        ]

    @staticmethod
    def _clean_tags(tags: list[str]) -> list[str]:
        return list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        cleaned = value.strip() if value else ""
        return cleaned or None

    @staticmethod
    def _next_evidence_code(existing: list[EvidenceReference], markdown: str = "") -> str:
        numbers = [
            int(match.group(1))
            for reference in existing
            if reference.evidence_code
            and (match := re.fullmatch(r"E-(\d+)", reference.evidence_code.upper()))
        ]
        for line in markdown.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[2] and (match := re.fullmatch(r"E-(\d+)", cells[0], re.I)):
                numbers.append(int(match.group(1)))
        return f"E-{max(numbers, default=0) + 1:03d}"

    @staticmethod
    def _check_revisions(
        paper: Paper,
        note: PaperNote | None,
        *,
        expected_paper_revision: int,
        expected_note_revision: int,
    ) -> None:
        if paper.revision != expected_paper_revision:
            raise AnalysisPreviewStaleError(
                resource="paper",
                expected=expected_paper_revision,
                actual=paper.revision,
            )
        actual_note_revision = note.revision if note else 0
        if actual_note_revision != expected_note_revision:
            raise AnalysisPreviewStaleError(
                resource="note",
                expected=expected_note_revision,
                actual=actual_note_revision,
            )

    @staticmethod
    def _normalize_evidence(
        paper_id: UUID, evidence: list[EvidenceReference]
    ) -> list[EvidenceReference]:
        return [item.model_copy(update={"paper_id": paper_id}) for item in evidence]

    @staticmethod
    def _merge_evidence_catalog(
        existing: list[EvidenceReference],
        incoming: list[EvidenceReference],
    ) -> list[EvidenceReference]:
        merged = {reference.evidence_id: reference for reference in existing}
        for reference in incoming:
            merged[reference.evidence_id] = reference
        return list(merged.values())

    @staticmethod
    def _analysis_document(paper: Paper) -> PaperAnalysisDocument:
        return PaperAnalysisDocument(
            paper_id=paper.paper_id,
            revision=paper.revision,
            updated_at=paper.updated_at,
            evidence_catalog=paper.structured_summary.evidence_catalog,
            items=paper.structured_summary.items,
        )
