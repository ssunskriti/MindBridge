"""Generate the synthetic, team-labelled training set for the concern classifier.

Synopsis: "The training set will mix appropriate public research datasets
(e.g. Dreaddit) with synthetic student messages written and manually labelled
by the team, and the origin of each sample will be recorded."

This script writes the SYNTHETIC part (source = 'synthetic_team').
Public data (e.g. Dreaddit) can be appended to data/concerns_train.csv later
with source = 'dreaddit' after mapping its labels.

The held-out test set (data/concerns_test.csv) is hand-written separately
and is NOT generated from these templates, to avoid inflated accuracy.

Run:  python scripts/make_dataset.py
"""
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mindbridge.config import TRAIN_CSV  # noqa: E402

random.seed(42)

CORE = {
    "academic_stress": [
        "my exams start next week and I haven't studied anything",
        "I am so stressed about my end semester exams",
        "I failed my mid term and I'm scared about my CGPA",
        "there are too many assignments and deadlines this week",
        "I can't focus while studying for my exams",
        "placement season is coming and I feel totally unprepared",
        "my project submission is tomorrow and nothing is working",
        "I keep worrying about getting a back paper",
        "my parents expect a high CGPA and I can't keep up",
        "I panic every time I open the syllabus",
        "I have viva tomorrow and my mind goes blank",
        "the coding round for internship is stressing me out",
        "I am behind in every subject this semester",
        "attendance shortage might stop me from sitting in exams",
        "I'm worried I'll fail the DSA paper",
    ],
    "sleep_difficulty": [
        "I can't fall asleep at night",
        "I lie awake till 4 am every night",
        "I wake up many times during the night",
        "my sleep schedule is completely messed up",
        "I only get three or four hours of sleep",
        "even when I am tired I can't sleep",
        "I keep scrolling my phone till late and can't sleep",
        "I feel sleepy in class because I don't sleep at night",
        "I have been having insomnia for weeks",
        "my mind keeps racing when I try to sleep",
        "I sleep the whole day and stay awake all night",
        "I wake up feeling exhausted even after sleeping",
        "nightmares keep waking me up",
        "my roommate's noise keeps me awake every night",
        "I haven't slept properly in days",
    ],
    "loneliness": [
        "I feel so lonely in the hostel",
        "I don't have any friends in college",
        "everyone has their group and I'm always alone",
        "I miss my family and home a lot",
        "I eat alone in the mess every day",
        "nobody texts me or asks how I am",
        "I moved to a new city and I don't know anyone",
        "I feel isolated even when people are around",
        "I spend weekends alone in my room",
        "I have no one to talk to",
        "I feel invisible in my class",
        "all my school friends have moved on and I'm alone",
        "I feel left out when others go out",
        "I'm homesick and lonely",
        "it feels like nobody would notice if I was not there",
    ],
    "relationship_social": [
        "I had a big fight with my best friend",
        "my girlfriend broke up with me",
        "my boyfriend and I keep arguing",
        "my roommate and I don't get along at all",
        "my friends are ignoring me after an argument",
        "there is a lot of conflict with my parents at home",
        "I feel awkward talking to people in my class",
        "my group project members are not cooperating and we keep fighting",
        "someone in my friend group spread rumours about me",
        "I don't know how to deal with my breakup",
        "I get very anxious in social situations",
        "my parents don't understand my career choice",
        "my friend betrayed my trust",
        "I feel pressured by my friends to do things I don't like",
        "I'm in a toxic relationship and don't know what to do",
    ],
    "burnout": [
        "I feel completely burnt out",
        "I am exhausted all the time and have no motivation",
        "I have been working nonstop and I'm drained",
        "I don't care about anything in college anymore",
        "I'm mentally exhausted from classes, clubs and internship",
        "I feel like a robot just going through the motions",
        "I have no energy left to do anything",
        "even things I used to enjoy feel like work now",
        "I'm tired of everything and can't keep going like this",
        "I've been overworking for months and I'm empty",
        "I can't get out of bed to attend classes, I'm so drained",
        "I'm juggling too many responsibilities and I'm worn out",
        "I feel emotionally numb and exhausted",
        "studying has become meaningless, I'm just tired",
        "I keep procrastinating because I have zero energy",
    ],
    "emotional_distress": [
        "I feel sad all the time",
        "I keep crying without any reason",
        "I feel anxious and my heart races",
        "I feel overwhelmed and can't control my emotions",
        "I've been feeling very low for weeks",
        "everything feels heavy and dark",
        "I feel empty inside",
        "I get panic attacks often",
        "I feel hopeless about my life",
        "my anxiety is getting worse every day",
        "I feel like I'm falling apart",
        "I can't stop overthinking and feeling bad",
        "I feel down and nothing makes me happy",
        "I'm always on edge and restless",
        "I feel like I'm drowning in my emotions",
    ],
    "self_esteem": [
        "I feel like I'm not good enough",
        "everyone is smarter than me",
        "I hate the way I look",
        "I feel like a failure compared to my batchmates",
        "I don't believe in myself",
        "I always doubt my abilities",
        "I feel useless and worthless in class",
        "I compare myself to others on instagram all the time",
        "I think I don't deserve my seat in this college",
        "I'm scared people will find out I'm a fraud",
        "I feel ugly and unconfident",
        "I can never do anything right",
        "I feel inferior to my friends",
        "I'm too shy to speak because I think I'll sound stupid",
        "I have no confidence in myself",
    ],
    "other": [
        "how do I book an appointment with the counsellor",
        "what is the timing of the counselling centre",
        "can you tell me some healthy breakfast ideas",
        "what are some good study techniques",
        "how do I manage my time better",
        "what is mindfulness",
        "tell me a breathing exercise",
        "how much water should I drink in a day",
        "what does this app do",
        "hi, how are you",
        "can you suggest a good daily routine",
        "what is the helpline number",
        "how can I improve my focus",
        "is my data private on this app",
        "thank you for the help",
    ],
}

PREFIXES = ["", "", "honestly ", "lately ", "these days ", "hi, ", "I don't know, ", "bro ", "ugh "]
SUFFIXES = ["", "", ".", " and I don't know what to do", " please help", " what should I do?", "..."]


def main(per_label: int = 45) -> None:
    rows = []
    for label, sents in CORE.items():
        seen = set()
        for s in sents:  # always include the original sentence
            seen.add(s)
            rows.append((s, label, "synthetic_team"))
        while len(seen) < per_label:
            s = random.choice(PREFIXES) + random.choice(sents) + random.choice(SUFFIXES)
            if s not in seen:
                seen.add(s)
                rows.append((s, label, "synthetic_team"))
    random.shuffle(rows)
    TRAIN_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(TRAIN_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "label", "source"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {TRAIN_CSV}")


if __name__ == "__main__":
    main()
