---
name: 書籍製作工作台
description: Calm green and paper surfaces for a native Windows manuscript workbench.
colors:
  primary: "#315d43"
  primary-active: "#264d35"
  ink: "#263d34"
  muted: "#58695f"
  canvas: "#f5f6f2"
  paper: "#fffef9"
  surface: "#ffffff"
  line: "#dfe5dd"
  button-line: "#c7d2c6"
  hover: "#e9f0e5"
  selection: "#c5ddc8"
  disabled-surface: "#e1e5de"
  disabled-ink: "#68736c"
  error: "#963b32"
typography:
  display:
    fontFamily: "Microsoft JhengHei"
    fontSize: "19pt"
    fontWeight: 700
  title:
    fontFamily: "Microsoft JhengHei"
    fontSize: "13pt"
    fontWeight: 700
  heading:
    fontFamily: "Microsoft JhengHei"
    fontSize: "11pt"
    fontWeight: 700
  body:
    fontFamily: "Microsoft JhengHei"
    fontSize: "10pt"
    fontWeight: 400
  manuscript:
    fontFamily: "Microsoft JhengHei"
    fontSize: "12pt"
    fontWeight: 400
spacing:
  control-x: "10px"
  control-y: "8px"
  pane: "12px"
  workspace: "16px"
  group: "20px"
  section: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    padding: "8px 10px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    padding: "8px 10px"
  manuscript-source:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.manuscript}"
    padding: "16px"
  manuscript-editor:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.manuscript}"
    padding: "16px"
  batch-selected:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    height: "25px"
---

# Design System: 書籍製作工作台

## Overview

**Creative North Star: "Calm manuscript workbench"**

This documents the existing A workbench in Operate mode. It extends the selected green and paper visual system into native Windows Tkinter; it does not establish a new visual world. Clear Traditional Chinese labels, quiet surfaces, and simultaneous source/draft comparison support sustained proofreading.

The current implementation is the authority for native values. `prototype.css` preserves the inherited direction; its browser radii, shadows, serif paper styling, and responsive rules are reference material rather than Tkinter requirements. Product scope comes from `PRODUCT.md`; the selected composition is recorded in ADR 0003.

**Key Characteristics:**

- Muted green actions and dark green text on quiet light surfaces.
- Paper source beside a white editable manuscript.
- Persistent book/batch context and a separate confirmation inspector.
- Native controls with explicit status and disabled-function explanations.

## Colors

The palette uses one restrained green accent with warm paper and pale neutral surfaces. Frontmatter records the exact native colors.

### Primary

- **Workbench Green** (`primary`): active workflow step, primary save/import actions, selected batch row, text caret, and focused manuscript border.
- **Deep Workbench Green** (`primary-active`): active primary-button state.
- **Soft Leaf** (`hover`): active secondary-button background.
- **Selection Leaf** (`selection`): manuscript text selection.

### Neutral

- **Forest Ink** (`ink`) and **Quiet Ink** (`muted`): main text and secondary explanations/project location. Native muted text is darker than the prototype's muted token.
- **Quiet Canvas** (`canvas`): workbench and inspector background.
- **Warm Paper** (`paper`): read-only source; **Clean White** (`surface`): editable draft and secondary buttons.
- **Fine Divider** (`line`) and **Control Border** (`button-line`): manuscript and control boundaries.
- **Disabled Surface / Ink**: legible unavailable actions; **Error Clay** (`error`): failed-operation status.

**The Action Green Rule.** Reserve solid green for the active step, selected batch, and meaningful primary actions; manuscript surfaces stay light.

## Typography

**Display Font:** Microsoft JhengHei.
**Body Font:** Microsoft JhengHei.
**Label/Mono Font:** No separate family is authored.

All native text uses the same legible Traditional Chinese family, including mixed Chinese/English manuscripts. Tk font sizes are points, not CSS pixels; Windows scaling affects their rendered size. No custom fallback stack, fixed line-height, tracking, or manuscript character measure is authored.

### Hierarchy

- **Display:** bold application title (`display`).
- **Title:** bold book name (`title`).
- **Heading:** bold pane and inspector headings (`heading`).
- **Body:** controls, instructions, metadata, location and status (`body`).
- **Manuscript:** source and editable text (`manuscript`), with Tk `spacing1=3` and `spacing3=8` pixels between display paragraphs.

## Layout

The native workbench keeps book/batch context left and an expanding manuscript area. Step 2 shows source and draft side by side; search and optional AI tools open on demand. Step 3 expands the same editable draft, with a confirmation summary on the right. Default geometry remains 1360×820, minimum 1040×640. F6 hides/restores side panels for focused reading without removing the global save control. Opening search or AI tools exits focus mode. The source/draft divider is draggable and manuscript size is selectable.

The top global toolbar contains the book title, Project menu, Versions and Files menu, focus action, and save. Save uses an ordinary button, is disabled when clean, and retains Ctrl+S. Compact stage navigation replaces the previous full-width step row and permanent tutorial block. Long source paths and provenance are available through details rather than occupying the comparison area.

The batch list expands vertically and shows text status (pending issues, unconfirmed, confirmed). Add and management actions use native menu buttons beneath the list. Native menu commands use the same enabled/invoke behavior as their prior button entry points.

The optional right panel has Search/Replace and AI Proofreading tabs. Ctrl+F opens Search/Replace and focuses search; opening tools retains editor selection. Step 3 replaces those tools with source checks and snapshot state. The manuscript action row uses the explicit labels「儲存並前往確認朗讀稿 →」and「確認朗讀稿並前往語音設定 →」. Saving must succeed before advancing; confirming captures the latest edits before opening voice settings.

A fixed footer separates persistent manuscript/reading/source-blocker state from recent operation messages. Full operation messages are available as selectable history. Source problems use a separate list with explicit processing/skip decisions and navigation to the relevant PDF page. A success result cannot remove the persistent source-blocker count.

PDF comparison is a standard maximized Toplevel with native restore controls, a compact document header and page navigation, two adjustable image/text panes, and fixed bottom page state, progress and actions. Range/language/layout/model settings open in a compact separate window. Re-recognition commands are grouped in a named native menu. Fit-page, fit-width and percentage zoom resample the bounded preview only; region coordinates remain normalized to the displayed source page. Image and text remain independently scrollable. Candidate selection and publication controls appear only for the corresponding job state.

Line-break preview is a maximized original/candidate comparison with change highlighting, an optional candidate-only view, and fixed Cancel/Apply actions. Applying always uses the calculated candidate independently of the selected view and remains one undo unit.

Gemini review is a standard maximized/restorable adjustable two-pane comparison. Record and paragraph navigation, decision counts and next-pending remain above the manuscripts. Notes have a visible summary plus disclosure; persistent blockers, operation result and per-paragraph actions are separate below. Batch adoption/undo commands use a named menu. Small API settings dialogs retain native compact forms.

The comparison rule remains: keep source and draft independently readable while retaining batch context, visible save state and reachable task actions. Verify actual supported sizes and DPI with native captures; no browser-specific geometry or visual effects are implied.

## Elevation & Depth

The native workbench is flat. No authored shadows exist. Operation notifications have one motion: a 250ms ease-out opacity fade after a three-second hold. Tonal surfaces, fine text-widget borders, spacing, the native sash, and `clam` control relief establish hierarchy. Prototype browser shadows are not native elevation tokens.

## Shapes

The native `clam` theme owns button shape and relief; the code sets no numeric corner radius. Manuscripts use flat relief with a **1px** highlight boundary. The inspector canvas has no highlight boundary. Preserve this plain rectangular control language instead of importing the prototype's rounded card shapes.

## Components

### Operation Notifications

Shared owner-bound notifications sit at the top center of the active operation window's content area, with a 16px top inset and a width capped at 400 logical pixels. They use the existing paper surface, a fine semantic border, native Traditional Chinese text and a × close button. A transient native window supplies opacity animation without fading the manuscript itself; it never uses global topmost.

Each owner shows one message at a time. Success/info messages remain for three seconds before a 250ms ease-out fade; hovering or focusing the notification pauses dismissal. Errors/warnings remain until dismissed, replaced or their owner loses focus. Notifications do not grab or take the editor's focus. Moving/resizing the owner re-centers the notification; hiding, closing or switching away clears it and its timers. Long messages and dialog results remain available through the main workbench's message history.

Emit once after a user-visible operation finishes, rather than from rendering, polling or each edit. Suppress notifications from internal pre-save steps. Operations that close a preview publish their completion on the surviving main window. Keep validation, progress, dirty/source blockers and decision dialogs in their existing persistent locations; dismissing a notification does not resolve those states.

### Buttons

Restrained native controls. `TButton` uses the frontmatter control padding and border color; its active background is Soft Leaf. Primary buttons use Workbench Green and white text, Deep Workbench Green when active, and Disabled Surface / Ink when unavailable. Native keyboard focus treatment belongs to the theme; do not claim a custom button focus ring. Ctrl+S is visible on the save action.

### Inputs / Fields

The editable manuscript is a native `tk.Text` with undo, word wrapping, green caret, leaf selection, and a green focused highlight. The source uses the same text treatment on Warm Paper with editing disabled. Project location is selectable read-only text. Native file, folder, name, and message dialogs retain Windows conventions.

The import preview uses a read-only encoding combobox with native width **27 characters**: automatic UTF-8/BOM, UTF-8, UTF-8 BOM, UTF-16 BOM, Big5, or CP950. Changing encoding clears the old preview and resets warning acknowledgment before decoding again. Readable details use Quiet Ink; decoding failures use Error Clay, an empty preview, disabled acknowledgment, and disabled import. A successful preview enables import only when disk space is sufficient and any corrupt-character warning has been acknowledged. The acknowledgment checkbox is enabled only when warnings exist; native theme rendering owns its checkbox and combobox states.

### Navigation

Four stage controls read left to right: 1 匯入來源 → 2 校對文字 → 3 確認朗讀稿 → 4 試聽與製作. Import shows project and PDF/TXT actions. Proofreading and confirmation share one editable text buffer, so changing stages preserves unsaved edits and undo history. Voice preview is available before reading confirmation; formal MP3/SRT production still requires a confirmed reading. Video is not a main navigation stage. Global commands stay in the top toolbar; optional task tools appear on demand. Selected stage and primary task use the restrained green accent.

### Comparison and Inspector

PDF entry points use **PDF 原頁與文字對照**. Tabs distinguish the current page's working text, the batch's immutable extracted text, and its manually edited full draft. An unpublished correction is explicitly marked as unsaved. The original/current page tabs may initially match; their relationship changes after OCR refinement.

Region refinement follows one region at a time: select image and text, recognize with an indeterminate progress bar, choose **採用本次結果／捨棄本次結果** under **本次框選辨識**, keep the choice and continue, then save a single new batch. Rejecting restores the input of the latest operation, including earlier accepted corrections; the immutable extracted text remains a separate comparison tab. Limit this choice to the latest region's page. Whole-page retry retains its explicit page-level choices. Keep the recognition/continue action on the same fixed row as save and close. Hide warning-resolution actions during region selection. Do not represent a selected checkbox's native X as a dismiss button. Source warning actions explicitly say **本頁已核對** and **略過本頁警告**; neither deletes page text. Ready models show **模型已就緒** and disable download instead of reporting a zero-byte installation.

Plain labeled text panes provide the signature comparison surface, without decorative cards or fabricated TXT page numbers. Optional proofreading tools and reading confirmation appear in their corresponding stages. Statistics, page actions and bottom status remain outside manuscript scrolling.

Exact-text search/replacement and undo are in Search/Replace; normalization, scope and candidate access are in optional AI tools. Step 3 displays editable full text, source checks and history, with confirmation below the text. Export/reload and version access also have top-level file-menu entry points. Full paths and hashes remain available in dedicated details/history views. For verification of this layout, see `docs/verification/main-flow.md`; prior screenshots document earlier arrangements.

## Do's and Don'ts

### Do:

- **Do** retain the calm green/paper system and native Microsoft JhengHei hierarchy.
- **Do** preserve independent manuscript scrolling and a separately scrollable inspector.
- **Do** keep unavailable actions legible and explain their dependencies nearby.
- **Do** verify supported window sizes with real native captures and treat source/draft distinction as functional hierarchy.

### Don't:

- **Don't** replace the selected A workbench with wizard or batch-console composition without a new design decision.
- **Don't** import browser-specific shadows, radii, serif typography, or mobile breakpoints as if they were native tokens.
- **Don't** imply online proofreading, reading confirmation, audio, or video succeeds before those functions exist.

Evidence: `ebook2mp4/desktop.py`, `PRODUCT.md`, `prototype.css`, ADR 0003, `docs/verification/T01-visual-review.md`, and `docs/verification/T02-visual-review.md`. T01 retains `.impeccable/review/desktop.png` and `narrow.png`; the independent T02 review directly inspected all four native captures in `.impeccable/review/t02/`: `desktop.png`, `narrow.png`, `preview-ready.png`, and `preview-error.png`. T02 covers a 1360×780 workbench (shorter than the configured 1360×820 default), the 1040×640 minimum workbench, and two 760×680 import dialogs at approximately 125% Windows scaling. The reviewer gives a **ship** disposition for this static visual scope only. These captures do not establish keyboard traversal/focus, hover, opened encoding choices, enabled warning acknowledgment, naming/reordering, unsaved-change prompts, large-list scrolling, arbitrary long names/paths, popup minimum-size resizing, other scaling settings, screen-reader behavior, persistence, or clean-Windows installation. Warning-state behavior above is extracted from source; no enabled-warning capture was supplied. No HTML detector is applicable to native Tkinter. The unavailable Impeccable engine was not rerun or represented as executed; the sidecar's existing HTML/CSS tiles remain illustrative translations for its viewer, not application source.
