from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)

AVAILABLE_GAMES = "Catan, Clue, Codenames, Monopoly, Pandemic, Risk, Ticket to Ride, and Uno"

SYSTEM_PROMPT = (
    "You are RulesBot, a board-game rules assistant. Answer the user's question "
    "using ONLY the rule text provided in the context. Do not use any outside "
    "knowledge of these or any other games, even if you are confident you know "
    "the answer. If the context does not contain enough information to answer, "
    "do not guess — reply exactly with: \"I couldn't find that rule in the loaded "
    f"rule books. I can only answer questions about: {AVAILABLE_GAMES}.\"\n\n"
    "Each source in the context is labelled with the game it comes from. The "
    "context often includes sources from games that have nothing to do with the "
    "question. Answer as if ONLY the relevant sources were provided: use the "
    "source(s) that actually answer the question and completely ignore the rest. "
    "Do NOT mention, list, or explain the unrelated games, and do NOT note that a "
    "game lacks the rule — say nothing about them at all. Begin your answer by "
    "naming the game it applies to (e.g. 'In Catan, ...'). If the question "
    "genuinely applies to more than one game, address each relevant one "
    "separately and make clear which rule belongs to which game. Never present a "
    "rule without saying which game it is from. A confident wrong answer is worse "
    "than admitting the rule isn't available."
)


def _format_context(retrieved_chunks):
    """Build the labelled, numbered context block from retrieved chunks."""
    blocks = [
        f"[Source {i} — {chunk['game']}]\n{chunk['text']}"
        for i, chunk in enumerate(retrieved_chunks, start=1)
    ]
    return "\n\n".join(blocks)


def generate_response(query, retrieved_chunks):
    """
    Generate a grounded answer from retrieved rule chunks.

    TODO — Milestone 3:

    `retrieved_chunks` is the list returned by retrieve(). Each item is a dict:
      - "text"     : the chunk text
      - "game"     : the game name
      - "distance" : similarity score (you can use this to filter weak matches)

    Before writing code, talk through these with your group:
      - How will you format the chunks into a context block for the prompt?
      - What instructions will stop the model from answering beyond what the
        rules say? (Grounding is the whole point — a confident wrong answer
        is worse than an honest "I don't know.")
      - How will you surface which game each answer comes from?

    Your response should:
      1. Answer using only the retrieved context — not the model's general knowledge
      2. Make clear which game the answer comes from
      3. Say so clearly when the answer isn't in the loaded rules

    Return the response as a plain string.
    """
    if not retrieved_chunks:
        return (
            "I couldn't find anything relevant in the loaded rule books. "
            "Try rephrasing your question — or check that your ingestion pipeline is working."
        )

    context = _format_context(retrieved_chunks)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,  # low — we want grounded, repeatable answers, not creativity
    )
    return response.choices[0].message.content
