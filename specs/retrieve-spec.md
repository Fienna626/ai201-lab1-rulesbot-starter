# Spec: `retrieve()`

**File:** `retriever.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Given a user's natural language query, find the most relevant chunks from the vector store using semantic similarity search. Return them ranked by relevance so that `generate_response()` can use them as context.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's natural language question |
| `n_results` | `int` | Maximum number of chunks to return (default: `N_RESULTS` from `config.py`) |

**Output:** `list[dict]`

Each dict in the returned list must contain exactly these keys:

| Key | Type | Description |
|-----|------|-------------|
| `"text"` | `str` | The chunk text |
| `"game"` | `str` | The game name this chunk came from |
| `"distance"` | `float` | Cosine distance score — lower means more similar to the query |

Results should be ordered from most to least relevant (lowest to highest distance). Returns an empty list `[]` if the collection contains no documents.

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Query approach

*Describe how you will use `_collection.query()` to find relevant chunks. What arguments will you pass, and why?*

```
I'll call _collection.query() with three arguments:
  - query_texts=[query] is a LIST containing the single user question.
        Chroma embeds each string with the same SentenceTransformer model
        used at ingestion, then finds the nearest stored vectors. It's a
        list because query() supports batching many queries in one call;
        I only have one, so the list has one element.
  - n_results=n_results basically caps how many chunks come back (default 3 from
        N_RESULTS in config.py). Enough context for an answer without
        flooding the prompt.
  - include=["documents", "metadatas", "distances"] is exactly the three
        payloads I need: documents = chunk text, metadatas = the game tag,
        distances = the cosine similarity score. I don't request embeddings
        or ids because the return contract doesn't use them.
```

---

### Return structure

*Sketch out what one item in your return list looks like as a concrete example. Where does each field come from in the query results?*

```
One item in my returned list, for the query "What happens if you roll a 7?":

  {
    "text": "When a 7 is rolled, the player who rolled moves the robber...",
    "game": "Catan",
    "distance": 0.41,
  }

Each field comes from the parallel result lists, at the same index i:
  - "text" <- results["documents"][0][i]
  - "game" <- results["metadatas"][0][i]["game"]   (the dict I stored in embed_and_store as {"game": ...})
  - "distance" <- results["distances"][0][i]

The lists are already ordered nearest-first, so building my list in order
preserves "most to least relevant."
```

---

### Handling the nested result structure

*`_collection.query()` returns nested lists. Describe what index you need to access to get the actual list of results for a single query, and why the nesting exists.*

```
query() returns a dict like:
  {
    "documents":  [[chunk, chunk, chunk]],   # note the OUTER list
    "metadatas":  [[{...}, {...}, {...}]],
    "distances":  [[0.41, 0.55, 0.62]],
  }

The outer list has one entry PER QUERY in query_texts. Because I passed a
single query, I access index [0] to get the actual results for it:
  results["documents"][0], results["metadatas"][0], results["distances"][0].

The nesting exists so a single query() call can answer many queries at once
(query_texts=[q1, q2, ...]) — index [0] is q1's results, [1] is q2's, etc.
```

---

### Relevance threshold

*Will you filter out results above a certain distance score, or return all `n_results` regardless of how relevant they are? What are the tradeoffs of each approach?*

```
Decision: for this milestone I'll RETURN ALL n_results, no distance filter.

Why: a hard cosine cutoff is brittle. A "good" distance varies by model
and by how the question is phrased, so a fixed threshold either throws away
valid-but-distant matches (returning []) or lets junk through anyway. The
cleaner place to handle weak relevance is generate_response(), which is
meant to say "that rule isn't in the rule books" when the context doesn't
support an answer — so I'll hand it the chunks plus their distance scores
and let the LLM judge.

Tradeoff of the alternative (filtering, e.g. drop distance > 1.0):
  + avoids feeding obviously irrelevant text into the prompt
  - brittle cutoff; risks empty results for questions that DO have a
    reasonable-but-not-perfect match
  - duplicates relevance judgment that the generator already does

If I revisit this, I'd make the threshold a config value rather than a
magic number, and keep at least the single best result instead of ever
returning [] on a non-empty collection.
```

---

### Edge cases

*How does your implementation behave when: (a) the collection is empty, (b) the query matches no chunks well, (c) the query matches chunks from multiple games?*

```
(a) Empty collection: the guard `if _collection.count() == 0: return []`
    (already in retriever.py) short-circuits before querying, so I return
    [] and generate_response can report it has no rules loaded.

(b) Query matches nothing well: query() still returns the n_results NEAREST
    neighbors — it never returns "nothing" on a populated collection. They
    just come back with high distance scores. Since I'm not thresholding,
    I return them as-is; the high distances are the signal generate_response
    uses to decline rather than make something up.

(c) Matches span multiple games: totally possible, the search is purely
    semantic across ALL games, with no per-game filter. A question like
    "how does trading work?" could pull chunks from Catan AND Monopoly.
    Each returned dict carries its own "game" field, so the answer can name
    which game each rule came from. This is a feature (cross-game answers)
    but also a risk (mixing rules from different games into one answer).
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 3.*

**Test query and top result returned:**

```
Query: What happens when you roll a 7?
Top result game: Catan
Distance score: 0.402
Does it make sense? Yes — the top chunk is the full "ROLLING A 7" rule from
Catan (discard half if holding 7+ cards, move the robber, steal a card).
Results #2 and #3 came from other games (Risk dice, Pandemic card draw), but
those are loosely related "dice / draw" mechanics, and the correct game is
ranked first.
```

**One thing about the query results that surprised you:**

```
(Draft — replace with your own observation.)

The distance scores were higher than I expected — around 0.40 even for a
clearly correct top match, not near 0. Cosine distance here isn't an
absolute "correctness" score; what matters is the relative ranking. The best
match just needs the smallest distance, not a tiny one. It also surprised me
that a short query like "How do you win?" pulled the WINNING rule from three
different games at once — semantic search has no idea I might have meant one
specific game unless I say so.
```
