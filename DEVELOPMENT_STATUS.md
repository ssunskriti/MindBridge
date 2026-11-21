# MindBridge – Development Status

Last updated: 20 November 2026 (Stage 1: student dashboard + chatbot)

## 1. Features implemented and tested
All of these are checked by `python scripts/test_stage1.py` (29/29 pass) and by running the app.

| Feature | Status | Where |
|---|---|---|
| Student registration (with password confirmation) and login | Working | `app.py`, `db.py` |
| Passwords salted and hashed (PBKDF2-SHA256) | Working (from mid-term) | `db.py` |
| Consent screen: what is collected and what it is used for; required before use | Working | `ui/student.py` |
| Withdraw consent (asks again before further use) | Working | `ui/student.py`, `db.py` |
| Basic profile: display name, year of study, programme | Working | `ui/student.py`, `db.py` |
| Check-in form: mood (labelled 1–5), stress, sleep, energy, main concern, optional note | Working | `ui/student.py` |
| Check-ins saved in SQLite | Working | `db.add_checkin` |
| Check-in history table (newest first) + wellbeing/stress chart | Working | `ui/student.py` |
| Chatbot: concern classifier (8 categories) | Working (from mid-term) | `classifier.py` |
| Low-confidence messages treated as "unclear"; bot asks an open question | Working (new) | `pipeline.py`, `responses.py` |
| Supportive, non-clinical replies without any LLM | Working (new) | `responses.py` |
| Safety layer: crisis phrases → fixed helpline message | Working (from mid-term) | `safety.py` |
| Safety layer: diagnosis/medication questions → fixed "I can't diagnose" reply | Working (new) | `safety.py` |
| "Why am I getting this response?" (concern, confidence, key words, safety result, latest check-in, support level + rules, reply source) | Working, saved with each reply | `pipeline.py`, `ui/student.py` |
| Delete my data | Working (from mid-term) | `ui/student.py`, `db.py` |
| Counsellor request (named or anonymous) + counsellor reply page | Working (from mid-term, unchanged) | `ui/student.py`, `ui/staff.py` |
| Admin page with plain group totals | Working (from mid-term), now clearly labelled "no DP yet" | `ui/staff.py`, `analytics.py` |

## 2. Files created or modified in Stage 1
**Created**
- `mindbridge/ui/__init__.py`, `mindbridge/ui/student.py`, `mindbridge/ui/staff.py` – pages moved out of `app.py`
- `mindbridge/analytics.py` – admin totals moved out of `db.py`
- `mindbridge/responses.py` – reply builder used when no LLM is running
- `scripts/test_stage1.py` – automated tests for Stage 1
- `.streamlit/config.toml` – one consistent colour theme
- `DEVELOPMENT_STATUS.md` – this file

**Modified**
- `app.py` – now only login, registration, consent check and navigation
- `mindbridge/db.py` – new columns + automatic upgrade of old databases; profile, consent-withdrawal and history functions; check-in validation
- `mindbridge/pipeline.py` – low-confidence handling, diagnosis check, new reply builder, explanation dict
- `mindbridge/classifier.py` – `key_words()` for the explanation panel
- `mindbridge/safety.py` – `asks_for_diagnosis()`
- `mindbridge/llm.py` – LLM is now optional only; old extractive fallback replaced by `responses.py`
- `mindbridge/config.py` – mood labels, year options, note length, confidence threshold, `MINDBRIDGE_DB` override
- `scripts/seed_demo.py` – demo check-ins now include concern and note; demo profile
- `README.md` – Windows setup, run, test, file guide

A backup of the project before Stage 1 is in `..\MindBridge_backup_before_stage1.zip`.

## 3. Database structure (`mindbridge.db`, SQLite)
| Table | Main columns | Who reads it |
|---|---|---|
| `users` | id, username, display_name, role, pw_hash, salt, consent, consent_at, **year_of_study**, **programme**, created_at | login, profile |
| `checkins` | id, user_id, mood, stress, sleep, energy, wellbeing, **concern**, **note**, created_at | the student; chatbot context; admin only as averages |
| `messages` | id, user_id, role, content, **explanation** (JSON), created_at | the student only |
| `events` | id, user_id, concern, confidence, pathway, score, safety_flag, reasons, created_at | support engine; admin only as counts |
| `plans` | id, user_id, concern, content, followup_on, created_at | the student |
| `counsellor_requests` | id, ticket, user_id, anonymous, category, message, status, reply, created_at, replied_at | the student; the counsellor |

**Bold** = added in Stage 1. `db.init_db()` adds missing columns to an older database automatically, so existing data is kept.

## 4. How to run
See `README.md`. Short version (Windows):
```bat
pip install -r requirements.txt
python scripts/seed_demo.py
python -m streamlit run app.py
```

## 5. Known limitations
- Training and test data are synthetic (team-written); classifier accuracy is 0.80 on only 40 test messages.
- Crisis detection uses phrases and similarity; it can miss messages written in unusual words.
- Without an LLM, replies come from team-written openings and knowledge-base sentences, so they can feel repetitive.
- The knowledge base has 6 topics; relationship and self-esteem replies use the team tip list instead.
- "Key words" in the explanation come from the word part of the model only, so a short message may show none.
- The admin page shows plain totals. **Differential privacy is not implemented.** Small groups could still reveal individuals.
- No encryption at rest; the app trusts whoever runs the server. Demo passwords are weak by design.
- Counsellor workflow is a demo and is not connected to the real counselling cell.

## 6. Not implemented yet
- Differential privacy engine (Laplace noise, contribution bounding, small-group suppression)
- Privacy budget ledger
- Privacy-protected admin reports and admin analytics dashboard
- "What Does My College See?" transparency page
- Student-controlled sharing with preview (the current counsellor request has no preview step)

## 7. Recommended next steps (Stage 2: differential privacy + admin dashboard)
1. **Create `mindbridge/privacy/` with `mechanisms.py`.** Write `laplace_count(true_count, epsilon)` and `laplace_sum(true_sum, sensitivity, epsilon)` using `numpy.random.laplace(0, sensitivity/epsilon)`. Add unit tests that check the noise scale on many samples.
2. **Add a monthly reduction in `privacy/reports.py`.** For each student keep one record per month (latest check-in), clip stress to 1–5 and keep at most 3 tags. Group students by `users.year_of_study` (already collected in the profile).
3. **Add two tables in `db.py` (via `MIGRATIONS`/`SCHEMA`):** `privacy_releases(id, month, group_name, query, noisy_value, epsilon, created_at)` and `privacy_ledger(id, month, epsilon_spent, semester_total, status, created_at)`.
4. **Build `release_month(month)`.** Compute count (ε 0.15), stress sum (ε 0.20, sensitivity 5) and campus topic counts (ε 0.15, sensitivity 3); noisy average = noisy sum ÷ noisy count; hide a group if its noisy count < 20; refuse if the semester total would exceed ε 2.0; store results once.
5. **Replace the admin page.** In `ui/staff.py`, read only from `privacy_releases` (never from `analytics.py`). Add a "Generate this month's report" button and show the ledger.
6. **Add the "What Does My College See?" page** in `ui/student.py`, reading the same `privacy_releases` rows.
7. **Test it.** Add `scripts/test_privacy.py`: refresh shows the same numbers; the cap refuses a 5th release; admin and student pages match; then run the accuracy (error vs group size) and differencing-attack simulations on this code.
8. **Only after step 7 passes**, describe differential privacy as implemented in the report and README. For the final version, cross-check the noise with OpenDP or diffprivlib.
