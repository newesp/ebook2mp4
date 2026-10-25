# T02 visual finish review

## Disposition — ship

Ship for the reviewed static visual scope. No material visual fix, recapture, or rebuild is required. The native A workbench retains its book/batch sidebar, simultaneous source/draft comparison, and tools inspector within the established calm green/paper design. This is an independent finish review of the final captures, not a functional or installation acceptance.

## Capture validity

Directly inspected all four supplied PNGs through `view_image`: `.impeccable/review/t02/desktop.png`, `narrow.png`, `preview-ready.png`, and `preview-error.png`. These show actual native Tk window chrome and controls, rather than a browser translation or design comp. Supplied logical sizes are 1360×780, 1040×640, and 760×680 for both dialogs; physical image dimensions are consistent with approximately 125% Windows scaling plus window decorations. The desktop capture is shorter than the application's configured 1360×820 default, which gives useful additional vertical pressure without claiming to capture that exact default geometry.

The minimum-size image is valid evidence for the supported compact workbench. The inspector's lowest disabled production action extends below its viewport and has its own visible scrollbar; this is ordinary vertical scrolling, not horizontal clipping. Both manuscript panes also have independent visible scrollbars. The images establish visible layout only; they do not demonstrate scrolling or other interactions being exercised.

## Material findings

No blocking finding. At both workbench sizes the batch list, selection, naming/up/down actions, add-TXT action, project context, source metadata, and both manuscript panes remain identifiable. Compact action widths preserve usable comparison space at the minimum width. Long batch names visibly truncate within the fixed sidebar; the center metadata gives the selected batch and source filename a separate wrapping location. The captures do not prove every possible long name fits there, but the truncation does not obscure the current selected manuscript's identity.

The ready dialog clearly exposes CP950 selection, source details, legible Chinese preview, cancellation, and the green import action. The failed auto-decoding dialog replaces the preview with an empty surface, explains the UTF-8 failure in red, directs the user to switch encoding, states that nothing has been imported, and visibly disables import. Neither state implies a successful import or substitutes corrupt text silently. The warning acknowledgment is present but inactive in these two non-warning states.

The flat native controls, restrained green selection, paper source, white editor, and clear grouping remain coherent. The small pointer highlight in the workbench captures does not hide a relevant control or prevent assessment.

## Brief and craft-floor coverage

Reviewed `PRODUCT.md`, `DESIGN.md`, the T02 ticket, relevant `ebook2mp4/desktop.py` definitions, and Impeccable's `reference/craft-floor.md`. The pinned native Operate direction governs: no new visual world, browser cards, shadows, bespoke motion, or display font is required. Numbered steps communicate the actual production sequence. Import preview warrants protected attention because users must inspect decoded source before creating a batch.

Source-token contrast calculations support the visible hierarchy: ink on paper approximately 11.56:1, muted text on canvas 5.37:1, white on primary green 7.56:1, and error text on canvas 6.52:1. These exceed the floor for active body text. Disabled ink on disabled surface is approximately 3.87:1; it is an intentional inactive-control treatment, with functional reasons supplied nearby. These are token calculations, not pixel-level measurements of native antialiasing or every theme-owned state.

The comparison layout, readable mixed-language content, distinct source/editor surfaces, spacing, batch context, encoding selector, error recovery copy, and disabled dependencies satisfy the applicable visible brief. Native Tk controls own parts of focus, combobox, checkbox, and scrollbar rendering. No HTML detector applies. No claim is made that an unavailable Impeccable engine was run.

## Remaining QA risk

Static images do not verify keyboard traversal/focus, hover, opened combobox options, warning-state acknowledgment, batch renaming/reordering, unsaved-change prompts, large-list scrolling, arbitrarily long names/paths, popup minimum-size resizing, other Windows scaling settings, or screen-reader behavior. The warning control's presence and source guard are visible/readable evidence, but an enabled-warning capture was not supplied. Those gaps do not require recapturing these four valid states for this static review.

Functional tests (20/20), mypy, and native executable build are reported separately by the implementation owner and were not rerun in this read-only visual scope. No application files were changed and no application or test processes were started by this review.
