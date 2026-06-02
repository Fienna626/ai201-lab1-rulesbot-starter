# Spec: `generate_response()`

**File:** `generator.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Given a user query and a list of retrieved rule chunks, generate a response that directly answers the question using only the retrieved text as context. The response must be grounded — it should not draw on the model's general knowledge of board games, only on what was retrieved.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's original question |
| `retrieved_chunks` | `list[dict]` | Ranked list of chunks from `retrieve()`, each with `"text"`, `"game"`, and `"distance"` |

**Output:** `str`

A plain string containing the response to show the user. The response should:
- Answer the question using only the retrieved rule text
- Identify which game the answer comes from
- Acknowledge clearly when the answer is not found in the loaded rules

Returns a fallback string (not an error) when `retrieved_chunks` is empty.

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Context formatting

*How will you format the retrieved chunks before passing them to the LLM? Describe the structure — not the code. Consider: will you label chunks by game? Include distance scores? Separate chunks with delimiters?*

```
(Draft — review and make it your own.)

I'll build a single context block where each retrieved chunk is a labelled,
numbered section, in the nearest-first order retrieve() returns:

  [Source 1 — Catan]
  <chunk text>

  [Source 2 — Risk]
  <chunk text>

Decisions:
  - LABEL BY GAME: yes. The game name is essential — it's how the model can
    cite which game the answer came from, and it stops it from blending two
    games' rules together silently.
  - DISTANCE SCORES: no, I won't put the raw numbers in the prompt. A cosine
    distance like 0.40 is meaningful to my code but noise to the LLM — it
    can't calibrate what "0.40" means and might try to reason about it. I use
    distance in code (for ordering / optional filtering), not in the prompt.
  - DELIMITERS: a clear "[Source N — Game]" header plus a blank line between
    chunks, so the model can tell where one rule ends and the next begins.
```

---

### System prompt — grounding instruction

*Write the exact system prompt instruction you will use to prevent the model from answering beyond the retrieved text. This is the most important design decision in this function.*

```
"You are RulesBot, a board-game rules assistant. Answer the user's question
using ONLY the rule text provided in the context below. Do not use any
outside knowledge of these or any other games, even if you are confident you
know the answer. If the context does not contain enough information to answer,
do not guess. Say you couldn't find it in the loaded rules. A confident
wrong answer is worse than admitting the rule isn't available."
```

---

### System prompt — citation instruction

*Write the exact instruction you will use to tell the model to identify which game its answer comes from.*

```
"Each source in the context is labelled with the game it comes from. Begin
your answer by naming the game it applies to (i.e. 'In Catan, ...'). If the
question could apply to more than one of the provided games, address each one
separately and make clear which rule belongs to which game. Never present a
rule without saying which game it is from."
```

---

### Fallback behavior

*What should the response say when the answer isn't found in the loaded rule books? Write the exact fallback message.*

```
Two cases:

1. retrieved_chunks is EMPTY (handled in code, before any API call) return exactly the message already in generator.py:
     "I couldn't find anything relevant in the loaded rule books. Try
      rephrasing your question — or check that your ingestion pipeline is
      working."

2. Chunks exist but DON'T answer the question (the model decides this, per the grounding instruction) I instruct the model to reply with:
     "I couldn't find that rule in the loaded rule books. I can only answer
      questions about: Catan, Clue, Codenames, Monopoly, Pandemic, Risk,
      Ticket to Ride, and Uno."

Listing the available games turns a dead end into a helpful nudge.
```

---

### Handling low-relevance chunks

*`retrieved_chunks` may include chunks with high distance scores (weak relevance). Will you filter these out before building context, pass them all in, or handle them another way? What are the tradeoffs?*

```
Decision: pass ALL retrieved chunks into the context, and lean on the
grounding instruction to make the model ignore irrelevant ones and decline
when nothing fits. This stays consistent with the no-filter decision in the
retrieve() spec — relevance judgment lives in one place (the prompt/LLM), not
split across two functions.

Tradeoffs:
  Pass all in (chosen):
    + simple, single source of truth for relevance
    + a borderline chunk that IS relevant won't get dropped by a guess
    - a little irrelevant text in the prompt; relies on the model behaving
  Filter by distance threshold:
    + cleaner prompt, fewer distractors
    - brittle cutoff value; risks dropping the only good chunk and forcing a
      false "not found"

If testing shows the model gets distracted by weak chunks, the smallest safe
change is to keep the top result always and drop only clearly-distant extras
(a config threshold, not a magic number) — not to filter aggressively.
```

---

### Message structure

*Describe how you will structure the messages list for the API call — what goes in the system message vs. the user message?*

```
A two-message list for the Groq chat completion:

  system: the persona + the grounding instruction + the citation instruction
          + the "if not found" fallback rule. This is the fixed behaviour that
          shouldn't change between questions.

  user:   the retrieved context block followed by the actual question, e.g.
            "Context:
             [Source 1 — Catan]
             ...

             Question: What happens when you roll a 7?"

Why this split: the system message defines HOW to answer (the rules of the
game, so to speak); the user message carries WHAT to answer and the evidence
to answer it from. Keeping the context next to the question in the user turn
makes it clear the context is material for THIS question, not standing policy.
```

---

## Implementation Notes

*Fill this in after implementing and testing.*

**Test query and response:**

```
Query: What happens when you roll a 7?
Response: "In Catan, when a 7 is rolled, no resources are produced. Every
          player with more than 7 resource cards must discard half (rounded
          down). The player who rolled moves the robber to any terrain hex
          and steals one random resource card from a player adjacent to it."
Correctly grounded? Yes — matches the Catan ROLLING A 7 rule exactly, no
          outside knowledge added.
Cited the right game? Yes — opened with "In Catan, ...".

(Also tested the fallback: "What are the rules of chess?" correctly returned
the not-found message instead of inventing chess rules, even though retrieval
handed it a Risk chunk.)
```

**One thing you changed from your original spec after seeing the actual output:**

```
The citation instruction. My original wording ("if the question could apply
to more than one game, address each separately") made the model volunteer
unwanted commentary: for "roll a 7" it answered correctly from Catan but then
added "In Risk, ... not mentioned" and "In Pandemic, there is no mention of
rolling a 7." Those games were only in context because retrieve() returns the
top 3 regardless of relevance.

I changed the code's instruction to tell the model to answer as if only the
relevant sources existed and to say nothing about unrelated games. This
connects back to the "pass all chunks in / no filter" decision in the
retrieve spec — the cost of that choice showed up here as distractor
commentary, so I'm paying for it in the prompt rather than by filtering.
```
