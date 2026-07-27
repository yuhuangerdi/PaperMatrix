# ruff: noqa: RUF001

from datetime import UTC, datetime
from uuid import UUID

from papermatrix.domain.paper import AnalysisItem
from papermatrix.services.markdown_analysis_parser import (
    add_item_anchors,
    note_item_fragment,
    parse_note_candidates,
    replace_note_item_fragment,
)

PAPER_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_parses_filled_sections_tables_and_evidence_deterministically() -> None:
    markdown = """# Example

## 1. 背景
### 1.2 具体问题
现有代理无法从工具失败中恢复。

## 3. 本文解决思路和整体框架
### 3.3 框架组成
| 模块 | 输入 | 处理过程 | 输出 | 作用 |
|---|---|---|---|---|
| 恢复规划器 | 失败反馈 | 重建计划 | 新动作 | 降低失败率 |
| 模块 B |  |  |  |  |

## 4. 需要克服的挑战或难点
### 挑战 1
- 为什么困难：工具返回的信息不完整
- 本文如何处理：保留可追溯的执行状态

## 7. 实验与复现性
### 7.5 主要实验结果
| 实验 | 结论 | 关键数据 | 图表位置 |
|---|---|---|---|
| 主实验 | 恢复成功率提升 | +12% | 表 3 |
| 消融实验 |  |  |  |

## 11. 关键引用、页码与证据
| 条目 ID | 类型 | 观点或证据 | 印刷页码 | PDF 页序号 | 图/表 | 备注 |
|---|---|---|---|---:|---|---|
| E-001 | 方法 | 恢复规划器结构 | 6 | 7 | 图 2 | 架构图 |
| E-002 | 结果 | 成功率提升 | 9 | 10 | 表 3 | 主结果 |
"""
    first = parse_note_candidates(PAPER_ID, markdown, [])
    second = parse_note_candidates(PAPER_ID, markdown, [])

    assert [item.model_dump() for item in first] == [item.model_dump() for item in second]
    assert [item.kind for item in first] == [
        "research_problem",
        "method_component",
        "challenge",
        "finding",
    ]
    assert first[1].title == "恢复规划器"
    assert first[1].attributes["处理过程"] == "重建计划"
    assert first[1].evidence_refs[0].page_label == "6"
    assert first[3].evidence_refs[0].table == "表 3"
    assert first[0].section_key == "section-1"
    assert first[1].section_key == "section-3"
    assert first[1].section_order == 1
    assert all(item.source_line_start >= 1 for item in first)


def test_ignores_unfilled_template_placeholders_and_marks_duplicates() -> None:
    markdown = """## 3. 本文解决思路和整体框架
### 3.2 整体框架
输入 → 模块 A → 模块 B → 模块 C → 输出

### 3.3 框架组成
| 模块 | 输入 | 处理过程 | 输出 | 作用 |
|---|---|---|---|---|
| 模块 A |  |  |  |  |

## 5. 大致流程和创新点（3+1）
### 5.2 创新点 1
- 针对的挑战：
- 做了什么：保存失败上下文

## 6. 具体流程和技术细节
### 6.10 关键实现细节
记录删除后可能导致方案失效或实验不可复现的细节。

## 7. 实验与复现性
### 7.7 开源情况
- 源码：公开 / 未公开 / 部分公开
- 数据：公开 / 未公开 / 部分公开
- 模型：开源 / 闭源
- 环境：可构建 / 难构建
- 复现难度：低 / 中 / 高
"""
    candidates = parse_note_candidates(PAPER_ID, markdown, [])
    assert len(candidates) == 1
    assert candidates[0].kind == "innovation"

    existing = candidates[0].model_dump(
        exclude={
            "candidate_id",
            "section_key",
            "section_title",
            "section_order",
            "source_anchor",
            "source_fingerprint",
            "sync_status",
            "source_section",
            "source_line_start",
            "source_line_end",
            "duplicate_item_id",
        }
    )
    item = AnalysisItem(
        item_id=candidates[0].candidate_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        tags=[],
        writing_uses=[],
        **existing,
    )
    reparsed = parse_note_candidates(PAPER_ID, markdown, [item])
    assert reparsed[0].duplicate_item_id == item.item_id


def test_uses_heading_blocks_and_table_rows_as_balanced_item_boundaries() -> None:
    markdown = """## 2. 现有方案分类和经典文献
### 2.1 现有方法分类
| 类别 | 核心思路 | 优点 | 缺点 |
|---|---|---|---|
| 状态恢复 | 保存执行状态后重试 | 可追溯 | 存储成本较高 |

### 2.3 现有方案的共同不足
- 无法区分暂时故障和永久故障
- 缺少失败原因证据

### 2.4 本文切入点
利用可验证检查点恢复执行。

## 5. 大致流程和创新点（3+1）
### 5.1 大致流程
1. 捕获失败状态
2. 验证检查点
3. 恢复并继续执行

## 6. 具体流程和技术细节
### 6.1 输入与预处理
规范化任务和工具返回。

### 6.2 任务规划
- 输入：规范化任务
- 输出：带检查点的执行计划

## 7. 实验与复现性
### 7.7 开源情况
- 源码：公开
- 数据：部分公开
- 复现难度：中

## 8. 批判性评价
### 8.1 论文优点及证据
失败恢复过程具有完整审计日志。

### 8.5 可靠性检查
- 基线是否公平：是
- 是否适用于真实环境：仅验证了容器环境
"""
    candidates = parse_note_candidates(PAPER_ID, markdown, [])

    assert [candidate.kind for candidate in candidates] == [
        "method",
        "challenge",
        "method",
        "method",
        "method_component",
        "method_component",
        "experiment",
        "contribution",
        "condition",
    ]
    assert candidates[0].title == "状态恢复"
    assert candidates[0].attributes["核心思路"] == "保存执行状态后重试"
    assert candidates[1].summary.count("\n") == 1
    assert candidates[5].attributes == {
        "输入": "规范化任务",
        "输出": "带检查点的执行计划",
    }
    assert all(
        candidate.source_line_end - candidate.source_line_start < 8 for candidate in candidates
    )
    assert len({candidate.source_section for candidate in candidates}) == len(candidates)


def test_anchors_preserve_content_and_stabilize_heading_and_table_item_ids() -> None:
    markdown = """# Example

## 3. 本文解决思路和整体框架
### 3.1 核心思路
失败后重新规划。

### 3.3 框架组成
| 模块 | 作用 |
|---|---|
| 恢复器 | 重建计划 |
"""
    before = parse_note_candidates(PAPER_ID, markdown, [])
    anchored = add_item_anchors(markdown, before)

    assert "失败后重新规划。" in anchored
    assert "| <!-- papermatrix:item:" in anchored
    assert anchored.count("papermatrix:item:") == 2

    after = parse_note_candidates(PAPER_ID, anchored, [])
    assert [item.candidate_id for item in after] == [item.candidate_id for item in before]
    assert [item.title for item in after] == [item.title for item in before]
    assert add_item_anchors(anchored, after) == anchored

    method = after[0]
    changed = replace_note_item_fragment(
        anchored,
        method.candidate_id,
        "### 3.1 核心思路\n使用检查点恢复失败任务。",
    )
    assert "使用检查点恢复失败任务。" in changed
    assert "### 3.3 框架组成" in changed
    reparsed = parse_note_candidates(PAPER_ID, changed, [])
    assert reparsed[0].candidate_id == method.candidate_id
    assert reparsed[0].source_fingerprint != method.source_fingerprint
    assert note_item_fragment(changed, reparsed[0]).endswith("使用检查点恢复失败任务。")

    table = after[1]
    table_changed = replace_note_item_fragment(
        anchored,
        table.candidate_id,
        "| 恢复器 | 保存并重放状态 |",
    )
    assert f"<!-- papermatrix:item:{table.candidate_id} -->" in table_changed
    assert "| 恢复器 | 保存并重放状态 |" not in anchored
    assert parse_note_candidates(PAPER_ID, table_changed, [])[1].candidate_id == table.candidate_id
