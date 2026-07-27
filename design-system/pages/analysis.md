# Analysis Workspace Override

> This file overrides `design-system/papermatrix/MASTER.md` only for the cross-paper analysis workspace.

## Product Character

The analysis workspace is an academic operations surface. It should feel precise, calm, and inspectable. Visualization supports comparison and provenance; it is not decorative.

## Information Architecture

```text
Project context bar
Analysis scope bar: scope selector | paper count | missing references | readiness
Analysis tabs: Literature | Methods & Challenges | Experiments | Relations | Claims & Gaps | Synthesis
Active work surface
```

Keep the project sidebar compact. Analysis lenses belong in tabs inside one workspace so users do not lose the current scope while moving between matrix, graph, and synthesis.

## Scope Bar

- Remains visible while scrolling the work surface.
- Shows the active scope name as the strongest label.
- Shows paper count, missing references, and evidence gaps with icon, text, and color.
- Scope changes refresh every analysis tab.
- Create, rename, duplicate, and delete scope actions live in a menu; they are not separate large buttons.

## Matrix Mode

- Use a dense table with sticky paper identity columns and sticky headers.
- Keep row height stable; long evidence text opens in an inspector.
- Challenge status uses icon + text + restrained fill:
  - addressed: teal check
  - partial: amber half-circle
  - not addressed: red minus
  - not applicable: neutral slash
  - unknown: gray question mark
- Cell selection never changes column width or row height.
- A view toggle switches between heat map and accessible table without changing filters.

## Experiment Mode

- Show comparison criteria before numeric results.
- Use a segmented status control for comparable, partially comparable, not comparable, and unknown.
- Put the reason immediately beside the status.
- Disable ranking and winner emphasis for non-comparable groups.
- Keep units visible in headers and do not mix units in one numeric column.

## Relation Mode

Desktop layout:

```text
compact toolbar
full-width graph canvas | 320–400 px inspector
optional adjacency table below or as a view toggle
```

- The canvas is unframed and fills the available work area.
- Use Cytoscape.js with a proven layout; do not implement force simulation manually.
- Paper nodes use one consistent shape. Missing papers use dashed outlines.
- Edge type uses arrow direction, line style, and a labeled legend, not color alone.
- Node size does not imply quality, citations, or importance by default.
- Clicking empty canvas clears selection but never closes an edit dialog.
- Graph filters hide elements only. Delete requires an explicit command and confirmation.
- Mobile opens the adjacency table by default; graph mode is optional.

## Claim And Gap Mode

- Use two unframed columns on wide screens: supporting evidence and counterevidence.
- Stack the columns on narrow screens, preserving both headings.
- Display single-paper finding, consensus, dispute, and hypothesis as literal labels.
- Show the research-gap chain as connected full-width steps:
  `limitations → recurring pattern → why unresolved → research question → validation`.
- Every step has a source or a visible `待补证据` status.

## Inspector

- Opens for a paper, matrix cell, relation, claim, or gap.
- Header names the selected object and its type.
- Body shows concise facts, evidence locators, revision state, and edit action.
- Long notes open in the paper detail or note editor instead of nesting another panel.
- Unsaved edits block selection changes or ask for explicit discard.

## Controls

- Use Lucide icons for search, filter, fit view, layout, save view, edit, link, and delete.
- Icon-only graph tools have tooltips and accessible names.
- Use segmented controls for graph/table and heatmap/table modes.
- Use checkboxes for edge-type visibility and evidence-status filtering.
- Do not use pill-shaped text buttons as status decoration.

## Motion And Performance

- Use 150–200 ms color and panel transitions.
- Respect `prefers-reduced-motion`; disable animated graph transitions when requested.
- Load only the current scope/subgraph.
- Do not animate initial placement for large graphs.
- Preserve stable canvas and inspector dimensions while data loads.

## Visual QA

- Verify 1440×900, 1024×768, 768×1024, and 375×812.
- No graph toolbar, scope control, legend, or inspector text overlaps.
- Matrix scroll stays inside its container.
- All graph operations have an equivalent keyboard-accessible table path.
- Color-blind inspection still distinguishes every status and relation type.
