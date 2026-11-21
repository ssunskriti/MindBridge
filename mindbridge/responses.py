# Generated with AI assistance (Claude, Anthropic) - reviewed and tested by the team
# (whole file written with AI help in Stage 1, Nov 2026)
"""Builds the chatbot's reply when no LLM is running (the default).

A reply has three parts:
  1. a short, supportive opening written by the team for the detected concern
  2. two or three practical tips, taken as whole sentences from the
     knowledge base (data/kb) or, if nothing matches, from the team's tip list
     in plans.py
  3. a gentle closing question

Nothing here diagnoses or gives medical advice.
"""
from __future__ import annotations

import re
import zlib

from .plans import PLANS

OPENINGS = {
    "academic_stress": [
        "That sounds like a lot of pressure with your studies right now.",
        "Exams and deadlines can feel overwhelming, and it makes sense that you're stressed.",
    ],
    "sleep_difficulty": [
        "Not getting enough sleep can make everything else feel harder.",
        "It's tiring when your sleep is off, and it's good that you're paying attention to it.",
    ],
    "loneliness": [
        "Feeling lonely is hard, and it's more common in college than people show.",
        "Thank you for sharing that. Feeling left out or alone can really weigh on you.",
    ],
    "relationship_social": [
        "Problems with people close to us can take up a lot of headspace.",
        "That sounds like a difficult situation with someone who matters to you.",
    ],
    "burnout": [
        "It sounds like you've been running on empty for a while.",
        "Feeling drained after doing so much is a sign you need some recovery time, not that you're failing.",
    ],
    "emotional_distress": [
        "I'm sorry you're feeling this way. It's okay to not be okay.",
        "That sounds really heavy, and I'm glad you put it into words.",
    ],
    "self_esteem": [
        "It's hard when you're being tough on yourself.",
        "Those thoughts about yourself sound painful, and you deserve kindness too.",
    ],
}

CLOSINGS = {
    "academic_stress": "Which subject or deadline is worrying you the most right now?",
    "sleep_difficulty": "How long has your sleep been like this?",
    "loneliness": "Is there one person or group you'd feel comfortable reaching out to this week?",
    "relationship_social": "What would you most like to change about the situation?",
    "burnout": "What is one thing you could drop or postpone this week?",
    "emotional_distress": "Would it help to talk about what has been happening?",
    "self_esteem": "What is one small thing you did well recently, even if it feels minor?",
}

GREETING = re.compile(r"^\s*(hi+|hello+|hey+|hii+|good (morning|afternoon|evening)|namaste)\b[\s!.]*$", re.I)

OPEN_QUESTION = (
    "I'm here to listen. Could you tell me a little more about what's on your mind? "
    "For example, it could be studies, sleep, friends, family, or just how you've been feeling lately."
)

HELP_REPLY = (
    "Reaching out to someone is a good step, and I'm glad you asked. "
    "A counsellor can listen properly and help you work through what's going on."
)

DIAGNOSIS_REPLY = (
    "I can't tell you whether you have a condition, and I don't give medical or medication advice. "
    "Only a qualified professional can assess that properly. The university counsellor is a good, "
    "confidential place to start, and you can raise a request from the *Talk to a Counsellor* page. "
    "If you'd like, you can also tell me what you've been experiencing and I'll share some general tips."
)


def _pick(options: list, message: str) -> str:
    """Same message -> same choice, so replies are reproducible in a demo."""
    return options[zlib.crc32(message.encode()) % len(options)]


def _clean_sentences(text: str) -> list:
    """Whole sentences only. Chunks overlap, so a chunk can start mid-sentence."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if len(s) > 25 and s[0].isupper() and s[-1] in ".!?"]


def tips_from_knowledge_base(message: str, hits, limit: int = 3) -> list:
    query_words = set(re.findall(r"[a-z]{4,}", message.lower()))
    scored, seen = [], set()
    for rank, (chunk, _score) in enumerate(hits):
        for sentence in _clean_sentences(chunk.text):
            if sentence in seen:
                continue
            seen.add(sentence)
            overlap = len(query_words & set(re.findall(r"[a-z]{4,}", sentence.lower())))
            scored.append((overlap, -rank, sentence))
    scored.sort(reverse=True)
    return [s for _, _, s in scored[:limit]]


def compose(message: str, concern: str, hits, checkin_note: str | None = None) -> tuple:
    """Returns (reply_text, list_of_tip_sources_used)."""
    if concern == "other":
        if GREETING.match(message):
            return "Hi, I'm MindBridge. " + OPEN_QUESTION, []
        return "Thanks for sharing that. " + OPEN_QUESTION, []

    tips = tips_from_knowledge_base(message, hits)
    used = "knowledge base"
    if len(tips) < 2:
        tips = PLANS.get(concern, PLANS["other"])[:3]
        used = "team tip list"

    parts = [_pick(OPENINGS[concern], message)]
    if checkin_note:
        parts.append(checkin_note)
    parts.append("A few things that may help:\n" + "\n".join(f"- {t}" for t in tips))
    parts.append(CLOSINGS[concern])
    return "\n\n".join(parts), used
