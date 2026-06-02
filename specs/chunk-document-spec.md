# Spec: `chunk_document()`

**File:** `ingest.py`
**Status:** Pre-implemented — read through this spec and the code in `ingest.py` before moving to Milestone 2.

---

## Purpose

Split a single rule book document into smaller chunks suitable for embedding and semantic retrieval. Each chunk should carry enough context to be meaningful on its own when retrieved in response to a user query.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | The full text of a rule book document |
| `game_name` | `str` | The name of the game this document belongs to (e.g., `"Catan"`) |

**Output:** `list[dict]`

Each dict in the returned list contains exactly these keys:

| Key | Type | Description |
|-----|------|-------------|
| `"text"` | `str` | The chunk text |
| `"game"` | `str` | The game name (passed through from `game_name`) |
| `"chunk_id"` | `str` | A unique identifier for this chunk (e.g., `"catan_0"`, `"catan_1"`) |

Returns an empty list `[]` if the input text is empty or produces no valid chunks.

---

## Design Decisions

---

### Splitting approach

```
Paragraph-aware splitting. The document is split on blank lines into
paragraphs, and each paragraph becomes one chunk. Rule books are written as
discrete rules — an UPPERCASE header line followed by its rule text,
separated from neighbours by a blank line — so a paragraph is already a
self-contained rule unit. A paragraph longer than `max_chars` is sub-split
on sentence boundaries (with one sentence of overlap) so no chunk is too
large to embed meaningfully.

(Switched from the original character-based sliding window after Milestone 2
testing: blind 300-char windows started chunks mid-word, which diluted the
embeddings and let the wrong game's chunks rank highly.)
```

---

### Chunk size

```
Variable — one paragraph per chunk, capped at max_chars = 600. Rule
paragraphs are typically one complete rule (1–4 sentences), which sits
comfortably under 600 characters. The cap only triggers for unusually long
sections, which then split on sentence boundaries rather than mid-word.
```

---

### Overlap

```
None between paragraphs — each paragraph is already a complete rule, so
duplicating text across paragraph boundaries isn't needed. The only overlap
is inside the long-paragraph fallback: when a single paragraph exceeds
max_chars, consecutive pieces share one sentence so a rule split across two
pieces keeps its context.
```

---

### Minimum chunk length

```
50 characters. Paragraphs shorter than this are discarded. Very short
segments are usually bare section titles or whitespace — content that has no
semantic signal and would just add noise to the vector database.
```

---

### Rationale

```
Rule books are already structured as discrete rules separated by blank
lines, so paragraph boundaries line up almost exactly with the unit a user
asks about ("What happens when you roll a 7?" maps to the ROLLING A 7
paragraph). Splitting on those natural boundaries keeps each rule whole and
its header attached, which embeds more cleanly than a fixed character window
that ignores sentence and word boundaries.
```

---

### Known limitations

```
Paragraph splitting assumes the source documents use blank lines to separate
rules. If a document were one giant wall of text with no blank lines, the
whole thing would become a single oversized paragraph and fall back to
sentence splitting. Very long sentence-split pieces can still begin mid-rule
within a single long paragraph, though never mid-word. Documents with
inconsistent formatting (e.g. headers not on their own line) would chunk less
cleanly.
```

---

## Implementation Notes

*Fill this in after running the app and confirming ingestion worked.*

**Actual chunk count produced across all 8 rule books:**

```
128 chunks (paragraph-aware splitting).
Note: the original 300-char sliding window produced 149.
```

**One thing that surprised you or didn't match your expectations:**

```
(Draft — replace with your own observation.)

I didn't expect the chunking strategy to matter so much for retrieval. With
the original 300-char window, a query for "roll a 7" returned a chunk that
literally started mid-word ("x, that hex...") and Risk's dice rules ranked
above the actual Catan rule. Switching to paragraph-aware splitting — same
embedding model, same retrieve() code — put the correct, whole rule on top.
The chunk boundaries, not the search, were the bottleneck.
```
