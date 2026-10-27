# Ordinary found-text authoring

`DataLoader` recursively loads text definitions from `data/texts/*.json` and
subdirectories. Each Workbench-authored file contains one object with a unique
nonempty `id` and at least one page object containing a string `text` body.
`text_item_map.json` is excluded by basename at every depth and is not a text
publication target. Workbench checks duplicate identities and refuses ambiguous
or malformed sources instead of accepting the loader's overwrite behavior.

In Workbench, duplicate an eligible ordinary definition using **Save as new
variant**. The title is the reader heading. Pages can be added, removed and moved;
moving a page retains its entire object and unknown metadata. A page's `trailing`
boolean adds “— [text ends here] —”; absent is effectively false and stays absent
until deliberately changed. Literal authored newlines, blank paragraphs, Unicode,
quotes and backslashes are preserved through JSON escaping at the source boundary.

The production `engine.text_reader.parse_page` interprets literal `[DAMAGED]` as a
corruption-glyph span and `[REDACTED]` as a solid block. A player's recovered damage
text can replace a damaged span in ordinary play. Preview uses fresh empty
language knowledge, never a personal save. Even ordinary pages consult the saved
deep-tongue lexicon: known words translate and unknown words can draw glyphs.

Condition is a string, not an enum. With UI art, `pristine`, `worn`, `damaged`,
`fragmentary` and `burned` choose tints; unknown conditions use the worn tint.
Without UI art, pristine/worn/damaged/fragmentary choose border colors and other
conditions use the brown fallback. Shipped `stained` and `weathered` strings remain
valid. The heading displays the condition in uppercase.

`type`, `reads_as`, `lacunae` and page `damaged` remain inspectable metadata; no
active Python consumer establishes the behavior their names might imply. They
are not recalculated from prose. Language/alternate-render fields are inspectable;
active `deep_tongue` at root or page level, any `teach_words` block and special
`render_mode` (including alphabet) make a source read-only. Removing them in a
draft cannot upgrade the original source's entitlement.

Publication deliberately creates a new identity/file. Reopened definitions may be
inspected or duplicated again. Same-ID revisions are deferred because saved
recovery uses `(text_id, page_idx, span_idx)`; changing page/span positions under
an existing identity can change what previous knowledge refers to.

## Binding an existing readable item

Saving a text makes it available to the next data load; it does not select a
world location or modify any existing object. The existing authored-layout item
special can bind a text explicitly:

```json
{"type":"item","item_id":"letter","text_id":"your_new_text_id","x":3,"y":3}
```

Coordinates must be valid for that separately authored layout, with valid arrival
and return access. The authored-submap population route defaults to
`map_text=False`, so an explicit `letter` remains a letter. Its `on_use: "read"`
resolves `text_id` in `data.texts`. No text-item mapping edit is required. Other
routes can use `map_text=True` and the existing mapping; Workbench text publication
does not alter those routes, selection tables, active layouts or personal campaigns.

The registered reference provider reports explicit `text_id` declarations in saved
items, layouts and buildings plus direct text-item map entries. It does not scan
saves or infer every dynamic relationship. These are declared references, not
proof of natural acquisition.

Workbench's reader preview uses actual fonts, UI panels and lexicon in a disposable
context, with a bounded image for each requested page/scroll position. Preview is
consumer evidence only. Fresh validation, exact-source review and deliberate
single-file publication remain required. The W5B physical-letter test separately
uses production scene construction, normal pickup, inventory use and reader keys
in a controlled fixture; it does not certify natural world selection or balance.

## Multiple drafts and reader headings

Workbench document tabs can retain several ordinary texts alongside item and
recipe drafts. Tabs display source paths and dirty state. Close/Reload targets
only that document, with an explicit discard choice for edited source. Source,
page selection, variant inputs and structured history survive tab switches.
Publication replaces only its originating tab after verified reopen; a saved-file
reopen failure retains the draft and receipt with a deliberate retry action.
References and previews still use saved dependencies, not other parked drafts.

Accepted item, recipe and text drafts also checkpoint to per-user recovery storage
after a bounded 500 ms delay plus local write time. **Keep for Recovery and Close**
waits for the latest checkpoint. **Recover drafts** retains invalid text and target
intent across restart, but requires fresh source eligibility, validation and review;
Undo/Redo history is not restored. Changed/missing sources remain available for
comparison and copying. A newer post-publication draft is never replaced by retry;
completed publication is reconciled separately without another write. See the
[Workbench recovery workflow](../../workbench/README.md#recover-unfinished-item-recipe-and-text-drafts).

Text-reference mapping entries match the text ID key in `text_item_map.json`.
The value identifies a carrier item and does not establish another text reference.
In the production reader, oversized headings join the existing scrollable content
so the full heading and body remain accessible with arrows, Page Up/Down and
Home/End. Short headings stay fixed when enough body space remains. The footer
stays separate; no prose is truncated or rewritten.
