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

Native default client geometry is **1360×820**; minimum is **1040×640**. These are window constraints, not CSS breakpoints. Preserve the three-column workbench at supported sizes: book/batch context left, comparison center, inspector right. Body column minimum sizes are **190 / 470 / 240** logical pixels; only the center has expansion weight. The inspector canvas requests width **240**, with an additional scrollbar. Actual allocations may exceed these values through requested widget sizes.

The outer workbench has **16px** padding. Header bottom separation is **16px**. Four equal-weight numbered step buttons have **2px** horizontal grid padding. The instruction row uses **8px horizontal / 12px vertical** padding and wrap length **1000**. Source metadata uses **12px / 8px** padding and wrap length **500**. Statistics use **12px / 10px** padding; bottom status uses **8px / 10px** and adapts wrap length to available width.

The left frame uses padding **4,10,16,10** (left, top, right, bottom). Book text wraps at **175px**; the project-location text uses character wrapping, width **21 characters**, and height **4 lines** so a long path remains selectable. The fixed batch column prevents filenames stretching the sidebar.

Source and editor sit in a horizontal `ttk.Panedwindow` with equal expansion weights and a native draggable divider. Each wrapper has **12px** padding; each manuscript has **16px** inset, word wrapping, and its own vertical scrollbar. They scroll independently. The inspector is a separately scrollable canvas containing a padded frame (**12,10,4,10**); explanatory labels wrap at **220px**. Group actions have **10px** top and **24px** bottom separation.

Import preview uses native geometry **760×680**, minimum **640×580**, a flexible source preview, and persistent bottom actions. Its details wrap with the dialog width. A read-only encoding selector stays at the top; failures clear the old preview and disable import. Suspected corrupt characters require explicit acknowledgment before import.

The batch sidebar uses a vertically scrollable native Treeview with **25px** rows and white text on Workbench Green for the selected row. Selected batch names and revisions appear in wrapping center metadata; the tree remains fixed within its column for long names. Naming and up/down actions use a three-column button row, each with native `width=3` character units. The batch list expands vertically; the four-line project location keeps actions reachable at the native minimum size.

**The Comparison Rule.** Keep source and draft independently readable and scrollable while retaining batch context and reachable inspector actions.

## Elevation & Depth

The native workbench is flat. No authored shadows or animation tokens exist. Tonal surfaces, fine text-widget borders, spacing, the native sash, and `clam` control relief establish hierarchy. Prototype browser shadows are not native elevation tokens.

## Shapes

The native `clam` theme owns button shape and relief; the code sets no numeric corner radius. Manuscripts use flat relief with a **1px** highlight boundary. The inspector canvas has no highlight boundary. Preserve this plain rectangular control language instead of importing the prototype's rounded card shapes.

## Components

### Buttons

Restrained native controls. `TButton` uses the frontmatter control padding and border color; its active background is Soft Leaf. Primary buttons use Workbench Green and white text, Deep Workbench Green when active, and Disabled Surface / Ink when unavailable. Native keyboard focus treatment belongs to the theme; do not claim a custom button focus ring. Ctrl+S is visible on the save action.

### Inputs / Fields

The editable manuscript is a native `tk.Text` with undo, word wrapping, green caret, leaf selection, and a green focused highlight. The source uses the same text treatment on Warm Paper with editing disabled. Project location is selectable read-only text. Native file, folder, name, and message dialogs retain Windows conventions.

The import preview uses a read-only encoding combobox with native width **27 characters**: automatic UTF-8/BOM, UTF-8, UTF-8 BOM, UTF-16 BOM, Big5, or CP950. Changing encoding clears the old preview and resets warning acknowledgment before decoding again. Readable details use Quiet Ink; decoding failures use Error Clay, an empty preview, disabled acknowledgment, and disabled import. A successful preview enables import only when disk space is sufficient and any corrupt-character warning has been acknowledged. The acknowledgment checkbox is enabled only when warnings exist; native theme rendering owns its checkbox and combobox states.

### Navigation

Four equal-width numbered buttons read 來源 / 校對 / 語音 / 影片. The selected step uses the primary style. Changing to an unavailable production step displays its actual dependencies while preserving the editing surface and entered text.

### Comparison and Inspector

Plain labeled text panes provide the signature comparison surface, without decorative cards or fabricated TXT page numbers. The inspector groups Gemini, reading confirmation, and production dependencies vertically. Unimplemented controls are disabled with adjacent reasons; scrolling keeps the full inspector reachable at shorter heights. Statistics and bottom status remain outside manuscript scrolling.

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
