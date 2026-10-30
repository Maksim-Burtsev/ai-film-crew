# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Grade a blind reviewer's answers against the accepted ones: one line per question, exit 1 on a FAIL.

Usage: grade.py <questions.json> <answers.json>

questions.json, written by the agent from references/checklist.md for one piece:
  [{"id": "H6", "q": "Glasses: both rims, the bridge and both temples, the same in every tile?",
    "options": ["same", "changed", "can't tell"], "fail": ["changed"]}, ...]
  Each question lists the answers that stop the piece in "fail", or the only answers that pass it in "accept".
answers.json, the reviewer's reply (JSON only):
  {"H6": "changed", "notes": {"H6": "tile 14: the left temple is gone"}}

  PASS  F1   same
  FAIL  H6   changed (tile 14: the left temple is gone)
  FLAG  P3   can't tell: look yourself
  FAIL  A5   no answer
"""
import json, sys

CANT = "can't tell"


def grade(questions, answers):
    """[(tag, id, text)] for every question; tag is PASS, FAIL or FLAG."""
    notes = answers.get("notes", {}) or {}
    rows = []
    for q in questions:
        qid, a = q["id"], answers.get(q["id"])
        note = f" ({notes[qid]})" if qid in notes else ""
        if a is None:
            rows.append(("FAIL", qid, "no answer"))
        elif q.get("options") and a not in q["options"]:
            rows.append(("FAIL", qid, f"{a!r} is not one of the options{note}"))
        elif "accept" in q:
            rows.append(("PASS" if a in q["accept"] else ("FLAG" if a == CANT else "FAIL"), qid, a + note))
        elif a in q.get("fail", []):
            rows.append(("FAIL", qid, a + note))
        elif a == CANT:
            rows.append(("FLAG", qid, f"{CANT}: look yourself{note}"))
        else:
            rows.append(("PASS", qid, a + note))
    return rows


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    questions = json.load(open(argv[0]))
    answers = json.load(open(argv[1]))
    rows = grade(questions, answers)
    for tag, qid, text in rows:
        print(f"{tag}  {qid:4s} {text}")
    return 1 if any(tag == "FAIL" for tag, _, _ in rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
