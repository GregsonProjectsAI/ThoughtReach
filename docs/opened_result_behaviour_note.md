# Opened Search Result Behaviour Note
_ThoughtReach V1 — Authority Reference for Step 480_

## Canonical Rules

1. **One primary anchor per result.** Each opened search result has exactly one primary anchor block. This is the matched chunk text that caused the result to surface.

2. **Context is immediately visible on open.** When a result is expanded, a window of surrounding context is shown immediately alongside the matched text — the user sees meaning without any additional click.

3. **Anchor expands in place.** All context expansion (Previous/Next Line, Previous/Next Paragraph, Full Thread/Text) operates on the same rendered anchor block. The block grows. It does not spawn a sibling block.

4. **No duplicate rendering.** The matched excerpt text must never appear twice — once as a "snippet preview" and again inside an "expanded context" section. Only one representation of the anchor is visible at any time. The snippet preview is replaced by the expanded context view, not shown alongside it.

5. **Secondary matches are collapsed by default.** A conversation may have multiple matching regions (Match 2, Match 3, etc.). These are collapsed to a snippet preview by default.

6. **Secondary matches open independently only on explicit selection.** A secondary match may be expanded only when the user directly selects it. Opening a secondary match collapses the previously active anchor.

7. **Only one anchor is active at a time.** Within a single result card, only one excerpt is in the expanded state at any moment.

8. **Controls apply to the active anchor only.** Previous/Next Line and Previous/Next Paragraph (or Message) controls act exclusively on the currently expanded anchor block. They do not affect collapsed excerpts.

9. **Controls preserve scroll orientation.** Expanding upward (Previous Line, Previous Paragraph) scrolls the newly revealed content into view from the top. Expanding downward (Next Line, Next Paragraph) scrolls from the bottom. Empty-state feedback is shown if the boundary of the conversation is reached.

10. **Label accuracy is required.** The position label (e.g., "Messages 2–4" or "Paragraphs 3–5") must reflect the currently visible window of context, not the original snippet range.

11. **Structured and raw paths use the same anchor model.** The anchor-in-place rule applies identically regardless of whether the result is classified as STRUCTURED CONVERSATION or RAW IMPORTED TEXT. Only the control labels differ (Message vs. Paragraph).

## Authority Compliance

These rules are consistent with:
- `docs/ui_spec_search.md` §3 (Result Item Component, Expanded View)
- `docs/ui_interaction_result_item.md`
- `docs/api_contract_search.md` §1 (surrounding_messages, message_start/end_index)

No authority extension is required to enforce these rules.
