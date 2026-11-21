# Partly generated with AI assistance (Claude, Anthropic): llm_answer() rewritten with AI help
"""Optional local LLM via Ollama (~3B model, e.g. llama3.2:3b).

MindBridge does NOT need an LLM or any API key. If Ollama is not running on
this computer, llm_answer() returns None and the pipeline uses the
team-written replies in responses.py instead.

To switch the LLM on:  install Ollama, run `ollama pull llama3.2:3b`,
then `ollama serve`. The model is told to answer only from the retrieved
knowledge-base text.
"""
from __future__ import annotations

import json
import urllib.request

from .config import LLM_TIMEOUT, OLLAMA_MODEL, OLLAMA_URL

SYSTEM = (
    "You are MindBridge, a supportive wellbeing assistant for college students. "
    "Answer ONLY using the CONTEXT below. If the context does not contain the answer, say you don't know "
    "and suggest speaking to a counsellor. Be warm, brief (max 120 words), practical. "
    "Do not diagnose. Do not give medication advice. End with the source titles in square brackets."
)


def _ollama(prompt: str) -> str | None:
    try:
        data = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                           "options": {"temperature": 0.2}}).encode()
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as r:
            return json.loads(r.read()).get("response", "").strip() or None
    except Exception:
        return None


# Generated with AI assistance (Claude)


def llm_answer(query: str, hits) -> str | None:
    """Reply written by the local LLM, or None if no context or Ollama is not running."""
    if not hits:
        return None
    context = "\n\n".join(f"[{c.title}] {c.text}" for c, _ in hits)
    return _ollama(f"{SYSTEM}\n\nCONTEXT:\n{context}\n\nSTUDENT: {query}\nMINDBRIDGE:")
