# MindBridge
**A student wellbeing support platform with privacy-first institutional reporting**
B.Tech CSE (AI & ML) · The NorthCap University · Session 2023–2027
Team: Sanskriti Ghildiyal (23CSU281), Janya Anand (23CSU430), Ruder Mittal (23CSU434) · Supervisor: Dr. Bhavana Sharma

> MindBridge is a prototype. It does not diagnose or treat and does not replace counsellors.
> Differential privacy is **planned, not implemented yet** (see `DEVELOPMENT_STATUS.md`).

## Setup (once)
Needs Python 3.10 or newer.

**Windows (Command Prompt or PowerShell), inside this folder:**
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python scripts/seed_demo.py        # optional: demo accounts + sample data (deletes mindbridge.db first)
python -m streamlit run app.py     # opens http://localhost:8501
```
Demo logins: `student / student123` · `counsellor / counsel123` · `admin / admin123`.
You can also register a new student account from the login page.

The first start trains the concern classifier (a few seconds) and saves it to `models/`.

## Test
```bash
python scripts/test_stage1.py      # 29 checks: register, login, consent, check-ins, history, chatbot, explanations
python scripts/evaluate.py         # classifier accuracy, safety-layer recall, support-engine scenarios
```
`test_stage1.py` uses a temporary database, so your `mindbridge.db` is not changed.

## Optional: local LLM
Not required, and no API key is used anywhere. Without an LLM, replies are built from
team-written openings plus tips from the knowledge base (`data/kb`).
To try a local LLM: install [Ollama](https://ollama.com), run `ollama pull llama3.2:3b`, then `ollama serve`.
MindBridge detects it automatically (settings in `mindbridge/config.py`).

## Project layout
| Path | What it does |
|---|---|
| `app.py` | Entry point: login, registration, consent check, sidebar navigation |
| `mindbridge/ui/student.py` | Student pages: dashboard + check-ins, chat, profile, counsellor request, helplines |
| `mindbridge/ui/staff.py` | Counsellor page and admin page (admin sees group totals only) |
| `mindbridge/db.py` | SQLite tables and all personal-data functions; upgrades older databases |
| `mindbridge/analytics.py` | Group-level totals for the admin page (no DP yet) |
| `mindbridge/pipeline.py` | Handles one chat message from start to finish |
| `mindbridge/classifier.py` | Concern classifier (TF-IDF + Logistic Regression) and key-word explanation |
| `mindbridge/safety.py` | Crisis-phrase check and diagnosis-question check |
| `mindbridge/engine.py` | Rule-based support level (1–4) with reasons |
| `mindbridge/responses.py` | Builds the reply when no LLM is running |
| `mindbridge/rag.py` | Finds relevant knowledge-base text |
| `mindbridge/llm.py` | Optional local LLM (Ollama) |
| `mindbridge/plans.py` | Wellness plans and team tip lists |
| `mindbridge/config.py` | All settings, labels and thresholds |
| `data/` | Training/test messages, safety phrases, knowledge base |
| `scripts/` | Dataset builder, evaluation, demo data, Stage 1 tests |

## Adaptive Support Engine rules (`config.py`)
1. Safety flag → **Level 4 Crisis** (overrides everything, LLM not used)
2. Signals: low check-in +2, very low +1, low 3-check-in trend +1, high-impact concern +1, same concern in 14 days +1, persistent (≥3) +1, asks for help +4
3. Score ≥ 4 → **Level 3 Professional**, ≥ 2 → **Level 2 Guided**, else **Level 1 Self-guided**

Thresholds are routing decisions, not clinical cut-offs.

## Current results (early prototype, small synthetic data)
- Classifier (TF-IDF + LR) on 40 hand-written held-out messages: accuracy 0.80, macro-F1 0.80
- Safety layer on a synthetic test set: recall 8/8, false positives 0/8
- Engine scenario tests: 8/8 correct pathway
- Stage 1 app tests (`scripts/test_stage1.py`): 29/29 pass

Training data is synthetic (team-written). Public data (e.g. Dreaddit) and more test data are still to be added.

## Helplines
Tele-MANAS **14416** / 1-800-891-4416 (24x7) · Emergency **112**

## AI assistance (disclosure)
Parts of this project were written with help from an AI assistant (Claude, by Anthropic).
- **Whole files written with AI help (Stage 1):** `mindbridge/analytics.py`, `mindbridge/responses.py`, `mindbridge/ui/student.py`, `mindbridge/ui/staff.py`, `scripts/test_stage1.py`
- **Files partly changed with AI help:** `app.py`, `mindbridge/db.py`, `mindbridge/classifier.py`, `mindbridge/safety.py`, `mindbridge/llm.py`, `mindbridge/pipeline.py`, `mindbridge/config.py`, `scripts/seed_demo.py`
- Each such file starts with a comment, and each AI-written function has `# Generated with AI assistance (Claude)` above it.
- **How we checked it:** we read the code, ran `python scripts/test_stage1.py` (29/29 pass) and `python scripts/evaluate.py` (classifier accuracy 0.80, safety 8/8), and used the app by hand.
