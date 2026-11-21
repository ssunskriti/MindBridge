# Partly generated with AI assistance (Claude, Anthropic): asks_for_diagnosis() and DIAGNOSIS_REQUEST added with AI help
"""Independent Safety / Risk Layer.

Runs on EVERY message, separately from the concern classifier, and is always
checked FIRST by the Adaptive Support Engine. Two signals are combined:
  1. curated phrase list (data/safety_phrases.txt)  -> hard flag
  2. similarity to a small set of synthetic risk exemplars (TF-IDF cosine)
     -> soft flag above SIM_THRESHOLD (kept low to favour recall)
No real student crisis data is collected or used.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import SAFETY_PHRASES

RISK_EXEMPLARS = [
    "i want to end my life",
    "i am thinking about killing myself",
    "i don't want to be alive anymore",
    "i want to hurt myself",
    "everyone would be better off without me",
    "i have a plan to die",
    "i can't go on living like this",
    "i wish i could disappear forever and never wake up",
    "life is not worth living",
    "i am going to take all my pills",
]
SIM_THRESHOLD = 0.45
# Questions that ask MindBridge to diagnose or prescribe. These are not a crisis,
# but the chatbot must not answer them as if it were a clinician.
DIAGNOSIS_REQUEST = re.compile(
    r"\b(do|did|could|might|am) i (have|has|got|suffer from|be)\b.*\b(depress\w*|anxiety|adhd|ocd|bipolar|"
    r"disorder|insomnia|ptsd|autis\w*)"
    r"|\bam i (depressed|bipolar|mentally ill|crazy|autistic)\b"
    r"|\b(diagnos\w*|prescri\w*)\b"
    r"|\b(which|what) (medicine|medication|tablet|pill)s?\b"
    r"|\b(medicine|medication|tablets?) for (my )?(stress|anxiety|depression|sleep)\b",
    re.I,
)


# Generated with AI assistance (Claude)


def asks_for_diagnosis(text: str) -> bool:
    return bool(DIAGNOSIS_REQUEST.search(text))


NEGATIONS = re.compile(r"\b(not|never|no longer|don'?t)\s+(feel(ing)?\s+)?(suicidal|want to die)\b", re.I)


@dataclass
class SafetyResult:
    flag: bool
    score: float
    matched: list = field(default_factory=list)
    reason: str = ""


class SafetyLayer:
    def __init__(self):
        lines = [l.strip() for l in open(SAFETY_PHRASES, encoding="utf-8") if l.strip() and not l.startswith("#")]
        self.patterns = [re.compile(p, re.I) for p in lines]
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit(RISK_EXEMPLARS)
        self.ex = self.vec.transform(RISK_EXEMPLARS)

    def check(self, text: str) -> SafetyResult:
        t = text.lower().replace("’", "'")
        matched = [p.pattern for p in self.patterns if p.search(t)]
        sim = float(cosine_similarity(self.vec.transform([t]), self.ex).max())
        # Explicit negation ("I'm not suicidal") lowers only the soft signal; phrases still count
        # unless the ONLY match is the negated phrase itself.
        negated = bool(NEGATIONS.search(t))
        if matched and not (negated and len(matched) == 1 and re.search(r"suicid|want to die", matched[0])):
            return SafetyResult(True, max(sim, 0.9), matched, "Risk phrase detected")
        if sim >= SIM_THRESHOLD and not negated:
            return SafetyResult(True, sim, [], f"High similarity to risk exemplars ({sim:.2f})")
        return SafetyResult(False, sim, matched, "")
