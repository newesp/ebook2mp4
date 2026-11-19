---
name: frontend-visual-qa
description: Design, implement, or review web and desktop UI for task usability, component consistency, responsive layout, and visual or interaction regressions.
---

# Frontend Visual QA

Optimize task completion, not control count. Keep project-specific dimensions, placements, and workflows in the project specification.

## Workflow

1. **Baseline:** identify the primary task, parent layout, shared components, and closest working surface. Inventory affected capabilities and their entry points; distinguish intentional changes from regressions. Reproduce reported defects when runtime access is available.
2. **Acceptance:** specify representative content, supported viewport/text scales, applicable states, and measurable usable space for primary regions. Use short actions with observable results: “Expand history → Verify the editor still shows the agreed number of lines.”
3. **Design:** apply the rules below and fix parent constraints before local clipping workarounds. When mockups or approval are required, show normal, reduced, and expanded-tool states before implementation; reuse approval for agreed scope. Assessment-only work produces recommendations without product changes.
4. **Verify:** complete the task on the actual browser/native surface, including affected tools and one adverse transition. Compare capabilities with the baseline. Record observations and unverified paths; screenshots, tests, and mockups alone do not prove runtime usability.

## Structure and Components

- Order prerequisites and actions by the interface's reading direction. Make the next action evident. Keep consecutive operations on the same content in a stable workspace; preserve input, selection, scroll, and user-adjusted pane state across transitions.
- Reuse shared component styles across screens: typography, height, padding, alignment, and interaction states. Define size variants by role, not by screen; controls in one toolbar use a compatible size. Align peer content regions at shared edges; place their labels and controls in coordinated header/footer bands. Check default, selected, focused, busy, and disabled states.
- Budget space around the primary task before placing tools. Set project-specific minimum usable dimensions or visible-content targets with real data. Expand secondary panels only while those targets remain usable; otherwise reflow, switch panes, or use a dedicated view with retained context.
- A preview must support its intended inspection task. Preserve required navigation, zoom, fit, and source access during redesign. For example, a page thumbnail can support selection but cannot replace a readable comparison pane.
- Keep related controls in one row when labels, hit targets, and primary content still fit. At smaller sizes, deliberately reflow or collapse by priority; never force one row through clipping or unreadable compression.
- Place local actions and disclosure controls in the region's header or adjacent edge. Collapsing a region must release its layout track and gaps, not just hide its contents; keep a nearby reopen control without an empty full-height rail. Expose an accessible name, expanded state, keyboard operation, and hover/focus help for unclear icon controls. Global commands belong at the workspace level.
- Choose direct actions versus menus by task frequency, space, and explicit user preferences. Group and order peer actions by user-recognizable task or object, with descriptive entry points. Avoid an unrelated “More tools” collection. Specify each tool's opening, closing, and retained state; keep destructive actions distinct.
- Every visible element must support a task, decision, or necessary state. Consolidate shared status in a stable location; keep region-specific feedback near its subject. Disclose technical details on demand. Show only context-applicable fields and actions. Let whole-item operations batch internally where appropriate.

## Scrolling and Reachability

- Assign each overflow region a scroll owner and direction. Editor workspaces keep navigation and primary actions stable while content scrolls; ordinary documents and forms may use page scrolling.
- Give scroll regions bounded, usable space. Avoid competing same-axis scrollers; when nesting is necessary, define boundary behavior. Wrap prose; reserve horizontal scrolling for content that requires it, such as wide tables or code.
- Route wheel/touch input to the intended region and keyboard scrolling to the focused control. Keep final lines, focus, and actions reachable; hiding scrollbars or clipping content is not a fix.

## Feedback and Data Contracts

- Acknowledge processing promptly; prevent duplicate/conflicting actions. Show real progress and supported cancellation. Make success, partial, cancelled, and failed outcomes perceptible without unnecessary blocking alerts.
- Place actionable errors and resolvable prerequisites near the affected control; provide a navigable summary for errors across hidden regions. Explain meaningful consequences before commitment and honor required consent.
- Follow existing save, validation, permissions, and recovery contracts. Label the scope of save/apply/publish; combine actions only when their commit behavior permits it. Failure must not report success or advance readiness.
- Preserve edits across navigation and failures. Before replacement/reload would discard input, use the project's retention mechanism or obtain a discard decision. Distinguish editing, preview, saved, and approved states where they exist; invalidate downstream state as required and reject stale asynchronous overwrites.
- Offer eligible related-data choices with meaningful names/status. Explain empty choices and clearing consequences. Preview current input without publishing or bypassing permissions; store sensitive drafts and credentials only through approved mechanisms. Do not invent persistence or approval workflows to simplify layout.

## Evidence

Exercise affected scenarios on the actual surface:

- Complete the primary task and locate each affected capability from its new entry point; compare shared controls across relevant screens.
- At normal and reduced sizes and supported text scaling, expand/collapse tools; verify released space is reclaimed, peer content edges align, primary regions remain usable, and labels, focus, and actions remain reachable.
- With content several times taller than the viewport, reach both ends using supported wheel/touch, scrollbar, and keyboard input. Confirm only the intended region moves; repeat after resize and tool expansion.
- Trigger a relevant failure, partial result, or navigation with unsaved edits; verify feedback and data retention.

Use isolated fixtures and retain evidence plus regression tests for plausible state/data-loss bugs. Close only owned tabs/processes and remove temporary artifacts. Report the baseline/cause, changes or recommendations, exercised scenarios and dimensions, and remaining gaps. Design-only work leaves runtime acceptance pending.

When documentation maintenance is in scope, update authoritative rules and replace superseded guidance rather than adding parallel copies.
