"""Adaptive Support Engine (rule-based, explainable).

  1. Safety check first   -> crisis flag goes directly to Level 4
  2. Collect signals      -> check-in score, concern type, repeats in last 14 days, asked for help
  3. Score + thresholds   -> simple weighted sum (weights in config.py)
  4. Choose pathway       -> Level 1 / 2 / 3, logged for follow-up

Every decision returns the list of reasons so it can be traced and tested.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from . import config as C

HELP_REQUEST = re.compile(
    r"\b(talk|speak|meet|connect)\s+(to|with)\s+(a\s+|the\s+|some\s*)?(counsell?or|therapist|someone|somebody|professional|human|person)"
    r"|\b(need|want)\s+(professional\s+)?help\b|\bbook (an )?appointment\b|\bsee a counsell?or\b",
    re.I,
)


@dataclass
class Signals:
    concern: str
    safety_flag: bool
    checkin_wellbeing: Optional[float] = None       # 1-5, higher is better
    recent_wellbeing_avg: Optional[float] = None    # avg of last 3 check-ins
    recent_concerns: list = field(default_factory=list)  # concerns in last HISTORY_DAYS
    asked_for_help: bool = False


@dataclass
class Decision:
    level: int
    score: int
    reasons: list

    @property
    def name(self):
        return C.PATHWAYS[self.level][0]

    @property
    def action(self):
        return C.PATHWAYS[self.level][1]


def asked_for_help(text: str) -> bool:
    return bool(HELP_REQUEST.search(text))


def decide(s: Signals) -> Decision:
    W = C.ENGINE_WEIGHTS
    if s.safety_flag:
        return Decision(4, 99, ["Safety layer raised a crisis flag -> crisis pathway (overrides all rules)"])

    score, reasons = 0, []
    if s.checkin_wellbeing is not None:
        if s.checkin_wellbeing <= C.LOW_CHECKIN:
            score += W["low_checkin"]; reasons.append(f"Low check-in wellbeing ({s.checkin_wellbeing}/5) +{W['low_checkin']}")
        if s.checkin_wellbeing <= C.VERY_LOW_CHECKIN:
            score += W["very_low_checkin"]; reasons.append(f"Very low check-in +{W['very_low_checkin']}")
    if s.recent_wellbeing_avg is not None and s.recent_wellbeing_avg <= C.LOW_CHECKIN:
        score += W["low_trend"]; reasons.append(f"Low scores over recent check-ins (avg {s.recent_wellbeing_avg}) +{W['low_trend']}")
    if s.concern in C.HIGH_IMPACT_CONCERNS:
        score += W["high_impact"]; reasons.append(f"High-impact concern ({C.LABEL_NAMES[s.concern]}) +{W['high_impact']}")
    repeats = s.recent_concerns.count(s.concern) if s.concern != "other" else 0
    if repeats >= 1:
        score += W["recurring"]; reasons.append(f"Same concern {repeats}x in last {C.HISTORY_DAYS} days +{W['recurring']}")
    if repeats >= C.PERSISTENT_COUNT:
        score += W["persistent"]; reasons.append(f"Persistent concern (>= {C.PERSISTENT_COUNT}) +{W['persistent']}")
    if s.asked_for_help:
        score += W["asked_for_help"]; reasons.append(f"Student asked to talk to someone +{W['asked_for_help']}")

    level = 3 if score >= C.LEVEL3_MIN else 2 if score >= C.LEVEL2_MIN else 1
    if not reasons:
        reasons.append("No elevated signals")
    reasons.append(f"Total score {score} -> Level {level} (L2 >= {C.LEVEL2_MIN}, L3 >= {C.LEVEL3_MIN})")
    return Decision(level, score, reasons)
