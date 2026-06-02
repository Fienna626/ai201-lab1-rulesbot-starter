import os
import re
from config import DOCS_PATH


def load_documents():
    """Load all .txt rule documents from the docs folder."""
    documents = []
    for filename in sorted(os.listdir(DOCS_PATH)):
        if filename.endswith(".txt"):
            filepath = os.path.join(DOCS_PATH, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            game_name = filename.replace(".txt", "").replace("_", " ").title()
            documents.append({
                "game": game_name,
                "filename": filename,
                "text": text,
            })
    print(f"Loaded {len(documents)} rule document(s): {[d['game'] for d in documents]}")
    return documents


def _split_long_paragraph(paragraph, max_chars):
    """
    Sub-split a paragraph that exceeds `max_chars` along sentence boundaries.

    Packs whole sentences into pieces of up to `max_chars`, carrying one
    sentence of overlap into the next piece so context isn't lost at the
    boundary. Splitting on sentences (not raw characters) means a piece
    never starts or ends mid-word.
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", paragraph) if s]
    pieces = []
    current = []
    cur_len = 0

    for sentence in sentences:
        add_len = len(sentence) + (1 if current else 0)
        if current and cur_len + add_len > max_chars:
            pieces.append(" ".join(current))
            # One-sentence overlap into the next piece.
            current = [current[-1], sentence]
            cur_len = len(current[-2]) + 1 + len(sentence)
        else:
            current.append(sentence)
            cur_len += add_len

    if current:
        pieces.append(" ".join(current))

    return pieces


def chunk_document(text, game_name):
    """
    Split a rule document into chunks ready for embedding.

    Strategy: paragraph-aware splitting.
      Rule books are written as discrete rules — an UPPERCASE header followed
      by its rule text, separated from neighbours by a blank line. Splitting on
      blank lines keeps each rule whole and self-contained, which embeds far
      more cleanly than a blind character window (no mid-word starts, no two
      unrelated rules merged into one chunk).

      - Paragraphs (blank-line delimited) are the primary unit.
      - max_chars = 600: an unusually long paragraph is sub-split on sentence
        boundaries so no single chunk is too large to embed meaningfully.
      - min_length = 50: filters out headers/whitespace fragments that carry
        no useful semantic signal.

    Returns a list of dicts, each with:
      - "text"     : the chunk text (str)
      - "game"     : the game name, e.g. "Catan" (str)
      - "chunk_id" : a unique identifier, e.g. "catan_0", "catan_1" (str)
    """
    max_chars = 600
    min_length = 50

    prefix = game_name.lower().replace(" ", "_")
    chunks = []
    counter = 0

    # Split into paragraphs on one or more blank lines.
    paragraphs = re.split(r"\n\s*\n", text)

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if len(paragraph) < min_length:
            continue

        # Short paragraphs stay whole; long ones are sentence-split.
        pieces = (
            [paragraph]
            if len(paragraph) <= max_chars
            else _split_long_paragraph(paragraph, max_chars)
        )

        for piece in pieces:
            if len(piece) >= min_length:
                chunks.append({
                    "text": piece,
                    "game": game_name,
                    "chunk_id": f"{prefix}_{counter}",
                })
                counter += 1

    return chunks
