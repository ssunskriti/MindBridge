# Partly generated with AI assistance (Claude, Anthropic): _checkin_context() added and handle() changed with AI help
"""End-to-end message pipeline (System Architecture slide):

 message -> [Safety Layer] + [Concern Classifier] + [Latest check-in]
         -> Adaptive Support Engine -> pathway
         -> Level 1-3: supportive reply (+ plan at Level 2, counsellor suggestion at Level 3)
            Level 4: fixed crisis screen (no LLM)

Every reply comes with an `explanation` dict that the "Why am I getting this
response?" panel shows. It only contains observable inputs and rules.
"""
from __future__ import annotations

import time
from datetime import datetime
from dataclasses import dataclass, field

from . import db, config as C
from .classifier import ConcernClassifier
from .engine import Signals, asked_for_help, decide
from .llm import llm_answer
from .plans import make_plan
from .rag import Retriever
from .responses import DIAGNOSIS_REPLY, HELP_REPLY, compose
from .safety import SafetyLayer, asks_for_diagnosis

CRISIS_TEXT = (
    "I'm really concerned about what you've shared, and I want you to be safe right now. "
    "Please reach out to someone immediately:\n\n"
    + "\n".join(f"- **{n}**: {num} ({note})" for n, num, note in C.HELPLINES)
    + "\n\nIf you are in immediate danger, call **112** or go to the nearest hospital. "
      "You can also tell a trusted friend, warden or family member right now. You don't have to go through this alone."
)


@dataclass
class Response:
    text: str
    level: int
    concern: str
    confidence: float
    reasons: list
    sources: list
    mode: str
    latency: float
    plan: str | None = None
    explanation: dict = field(default_factory=dict)


# Generated with AI assistance (Claude)


def _checkin_context(last) -> tuple:
    """(dict for the explanation panel, optional sentence for the reply)."""
    if last is None:
        return None, None
    info = {
        "date": last["created_at"][:10],
        "mood": C.MOOD_OPTIONS.get(last["mood"], last["mood"]),
        "stress": last["stress"],
        "wellbeing": last["wellbeing"],
        "concern": C.LABEL_NAMES.get(last["concern"]) if last["concern"] else None,
    }
    sentence = None
    days_old = (datetime.now() - datetime.fromisoformat(last["created_at"])).days
    if days_old <= C.HISTORY_DAYS // 2 and last["stress"] is not None and last["stress"] >= 4:
        sentence = f"Your last check-in ({info['date']}) also showed high stress ({last['stress']}/5)."
    return info, sentence


class MindBridge:
    def __init__(self):
        self.classifier = ConcernClassifier()
        self.safety = SafetyLayer()
        self.retriever = Retriever()

    # Generated with AI assistance (Claude)

    def handle(self, conn, user_id: int, message: str) -> Response:
        t0 = time.time()
        safety = self.safety.check(message)
        pred = self.classifier.predict(message)
        # A weak guess is treated as "other": the bot asks an open question instead of guessing a topic.
        low_confidence = pred.confidence < C.MIN_CONCERN_CONFIDENCE
        concern = "other" if low_confidence else pred.label
        key_words = [] if low_confidence else self.classifier.key_words(message, pred.label)

        last = db.latest_checkin(conn, user_id)
        recent = db.recent_checkins(conn, user_id, 3)
        sig = Signals(
            concern=concern,
            safety_flag=safety.flag,
            checkin_wellbeing=last["wellbeing"] if last else None,
            recent_wellbeing_avg=round(sum(r["wellbeing"] for r in recent) / len(recent), 2) if len(recent) >= 2 else None,
            recent_concerns=db.recent_concerns(conn, user_id, C.HISTORY_DAYS),
            asked_for_help=asked_for_help(message),
        )
        d = decide(sig)
        reasons = ([safety.reason] if safety.flag else []) + d.reasons
        db.log_event(conn, user_id, concern, pred.confidence, d.level, d.score, safety.flag, reasons)

        checkin_info, checkin_sentence = _checkin_context(last)
        explanation = {
            "concern": concern,
            "concern_name": C.LABEL_NAMES[concern],
            "model_guess": C.LABEL_NAMES[pred.label],
            "confidence": round(pred.confidence, 2),
            "low_confidence": low_confidence,
            "key_words": key_words,
            "safety": safety.reason if safety.flag else "No risk phrases found",
            "diagnosis_request": False,
            "checkin": checkin_info,
            "level": d.level,
            "pathway": C.PATHWAYS[d.level][0],
            "reasons": reasons,
            "sources": [],
            "reply_source": "",
        }

        if d.level == 4:  # crisis: normal chat stops, no LLM
            explanation["reply_source"] = "Fixed crisis message with verified helplines (no AI-generated text)"
            return Response(CRISIS_TEXT, 4, concern, pred.confidence, reasons, [], "fixed crisis pathway",
                            time.time() - t0, explanation=explanation)

        hits = [] if concern == "other" else self.retriever.search(f"{C.LABEL_NAMES[concern]}. {message}")
        sources = sorted({(c.title, c.source, c.url) for c, _ in hits})

        if sig.asked_for_help and concern == "other":
            answer, mode, sources = HELP_REPLY, "team-written reply (no LLM)", []
            explanation["reply_source"] = "Team-written reply because you asked to talk to someone"
        elif asks_for_diagnosis(message):
            answer, mode, sources = DIAGNOSIS_REPLY, "fixed safety message", []
            explanation["diagnosis_request"] = True
            explanation["reply_source"] = "Fixed message: MindBridge does not diagnose or give medication advice"
        else:
            answer = llm_answer(message, hits)
            if answer:
                mode = f"LLM ({C.OLLAMA_MODEL})"
                explanation["reply_source"] = f"Local LLM ({C.OLLAMA_MODEL}) using only the knowledge-base text listed below"
            else:
                answer, tip_source = compose(message, concern, hits, checkin_sentence)
                mode = "team-written reply (no LLM)"
                if concern == "other":
                    explanation["reply_source"] = "Team-written open question (the topic was not clear)"
                else:
                    explanation["reply_source"] = f"Team-written opening for this concern + tips from the {tip_source}"
                if tip_source != "knowledge base":
                    sources = []

        plan = None
        if d.level == 2 and concern != "other":
            plan = make_plan(concern)
            db.save_plan(conn, user_id, concern, plan)
            answer += ("\n\n**I've made a short wellness support plan for you** (see *Dashboard*). "
                       "Please check in again in 3 days.")
        elif d.level == 3:
            answer += ("\n\n**It sounds like talking to a counsellor could really help.** You can raise a request "
                       "from the *Talk to a Counsellor* page - with your name, or anonymously.")
        explanation["sources"] = [[t, u] for t, _s, u in sources]
        return Response(answer, d.level, concern, pred.confidence, reasons, sources, mode,
                        time.time() - t0, plan, explanation)
