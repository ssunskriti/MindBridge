"""Personalisation: wellness support plans (Level 2) and resource tips (Level 1)."""

PLANS = {
    "academic_stress": [
        "Break the syllabus into small daily targets; tick off one block at a time.",
        "Study in 25-minute focus blocks with 5-minute breaks (Pomodoro).",
        "Do one past paper under timed conditions this week.",
        "Ask one doubt from a teacher or batchmate instead of stuck-looping alone.",
        "Protect 7+ hours of sleep - memory consolidates during sleep.",
    ],
    "sleep_difficulty": [
        "Fix a wake-up time and keep it, even on weekends.",
        "No screens for 30-45 minutes before bed; keep the phone away from the bed.",
        "Avoid tea/coffee/energy drinks after 4 pm.",
        "If awake for ~20 minutes, get up and do something calm in dim light, then return.",
        "Try 4-7-8 or box breathing in bed.",
    ],
    "loneliness": [
        "Join one club, sports group or study circle this week.",
        "Message one person (old friend or family) today.",
        "Eat at least one meal a day with someone from your floor or class.",
        "Spend 15 minutes outdoors in a common area rather than your room.",
        "Peer support / student mentor programmes are a good first step.",
    ],
    "relationship_social": [
        "Write down what happened and what you actually need from the other person.",
        "Use 'I feel ... when ... ' statements instead of blame.",
        "Take a 24-hour pause before replying when emotions are high.",
        "Talk it through with someone neutral you trust.",
        "Set one clear, kind boundary if something keeps hurting you.",
    ],
    "burnout": [
        "List your commitments and drop or postpone one this week.",
        "Schedule one fully free evening - no study, no clubs.",
        "Move your body for 20 minutes a day (walk, sport, yoga).",
        "Keep regular meals and sleep before adding more work.",
        "Do a check-in again in 3 days to see if energy is changing.",
    ],
    "emotional_distress": [
        "Try 5-4-3-2-1 grounding when feelings get overwhelming.",
        "Write your thoughts down for 10 minutes - names feelings, reduces their grip.",
        "Reach out to one trusted person today and tell them how you feel.",
        "Keep a basic routine: wake, eat, move, sleep at regular times.",
        "If low mood lasts 2+ weeks or affects daily life, please talk to a counsellor.",
    ],
    "self_esteem": [
        "Each night write 3 things you did okay today, however small.",
        "Notice comparisons; limit social media scrolling to a fixed time.",
        "Replace 'I always fail' with a specific, fair statement.",
        "Set one small, achievable goal and finish it.",
        "Treat yourself the way you'd treat a friend in the same spot.",
    ],
    "other": [
        "Keep a regular sleep and meal routine.",
        "Take short breaks and move a little every day.",
        "Stay connected with at least one person you trust.",
    ],
}


def make_plan(concern: str) -> str:
    steps = PLANS.get(concern, PLANS["other"])
    return "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
