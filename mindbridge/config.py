# Partly generated with AI assistance (Claude, Anthropic): Stage 1 settings (mood labels, year options, MIN_CONCERN_CONFIDENCE, MINDBRIDGE_DB) added with AI help
"""Central configuration for MindBridge.

All thresholds here are ROUTING decisions made by the team, not clinical
cut-off values (see Synopsis, Table 2). They are tuned with scenario tests.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
KB_DIR = DATA_DIR / "kb"
MODEL_DIR = ROOT / "models"
# MINDBRIDGE_DB lets the test script use a separate, temporary database.
DB_PATH = Path(os.environ.get("MINDBRIDGE_DB", ROOT / "mindbridge.db"))

TRAIN_CSV = DATA_DIR / "concerns_train.csv"
SAFETY_PHRASES = DATA_DIR / "safety_phrases.txt"
CLASSIFIER_PATH = MODEL_DIR / "concern_classifier.joblib"

# ---- Concern labels (8 labels, Synopsis Section: Concern classification) ----
CONCERN_LABELS = [
    "academic_stress",
    "sleep_difficulty",
    "loneliness",
    "relationship_social",
    "burnout",
    "emotional_distress",
    "self_esteem",
    "other",
]
LABEL_NAMES = {
    "academic_stress": "Academic stress",
    "sleep_difficulty": "Sleep difficulty",
    "loneliness": "Loneliness",
    "relationship_social": "Relationship / social concern",
    "burnout": "Burnout",
    "emotional_distress": "General emotional distress",
    "self_esteem": "Self-esteem",
    "other": "Other",
}
# Below this classifier confidence the chatbot treats the message as "other"
# and asks an open question instead of guessing a topic.
MIN_CONCERN_CONFIDENCE = 0.40

# ---- Student check-in form ----
# Mood is stored as a number (1-5) so the existing wellbeing score keeps working.
MOOD_OPTIONS = {1: "Very low", 2: "Low", 3: "Okay", 4: "Good", 5: "Very good"}
CHECKIN_NOTE_MAX_CHARS = 280
YEAR_OPTIONS = ["Not set", "1st year", "2nd year", "3rd year", "4th year", "Postgraduate"]

# Concern categories treated as "high impact" by the engine
HIGH_IMPACT_CONCERNS = {"burnout", "emotional_distress"}

# ---- Adaptive Support Engine weights and thresholds ----
ENGINE_WEIGHTS = {
    "low_checkin": 2,        # average check-in wellbeing <= LOW_CHECKIN
    "very_low_checkin": 1,   # extra point if <= VERY_LOW_CHECKIN
    "high_impact": 1,        # concern in HIGH_IMPACT_CONCERNS
    "recurring": 1,          # same concern seen in last HISTORY_DAYS
    "persistent": 1,         # same concern seen >= PERSISTENT_COUNT times
    "low_trend": 1,          # avg of last 3 check-ins also low
    "asked_for_help": 4,     # student explicitly asks to talk to someone
}
LOW_CHECKIN = 2.5
VERY_LOW_CHECKIN = 1.75
HISTORY_DAYS = 14
PERSISTENT_COUNT = 3

# score -> pathway
LEVEL2_MIN = 2
LEVEL3_MIN = 4

PATHWAYS = {
    1: ("Level 1: Self-guided", "Grounded answer + tips and resources"),
    2: ("Level 2: Guided", "Wellness support plan + follow-up check-in"),
    3: ("Level 3: Professional", "Encourage counselling; identified or anonymous request"),
    4: ("Level 4: Crisis", "Normal chat stops; verified helplines and emergency contacts"),
}

# ---- RAG ----
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_WORDS = 120
CHUNK_OVERLAP = 30
TOP_K = 3
MIN_RETRIEVAL_SCORE = 0.08

# ---- LLM (local via Ollama; extractive fallback if unavailable) ----
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
LLM_TIMEOUT = 60

# ---- Verified helplines (India) ----
HELPLINES = [
    ("Tele-MANAS (National Tele Mental Health Programme)", "14416 or 1-800-891-4416", "24x7, free, multiple languages"),
    ("National Emergency Number", "112", "Police / ambulance / immediate danger"),
]

AI_DISCLAIMER = (
    "MindBridge is an AI support tool, not a medical professional. "
    "It does not diagnose or treat. If you feel unsafe, call Tele-MANAS 14416 or 112."
)
