---
name: blind-review
description: Blind review of AI-generated stills, takes and cuts by a fresh subagent that never made them, answering fixed-option questions in JSON that code grades. Use before any still, take or cut reaches a person, after any change to a reviewed file, or to judge whether a fix is better than the current version.
---

# Blind review

The agent that made a piece never grades it, and never on a metric of the effect it wanted. A fresh subagent sees
only the pictures, the people, the script and the questions. Vision models are poor at "does this look right?" and
decent at a narrow question with fixed answers ("how many fingers are on that hand?"), so the reviewer answers facts
and code decides.

## Run it
1. **Code first.** Run the measuring checks (scene-set's `frame_check.py`, product-size's `size.py`,
   recurring-cast's `identity.py`). Their numbers go to the reviewer as leads, not verdicts.
2. **Make the sheets**: face crops every 0.25 s, the whole frame every 0.5 s, the stills of one person side by side,
   the reference photos, and for a cut the story frames at 2 fps with the timed lines. Number the tiles and put the
   time on each.
3. **Write the questions** for this piece from [references/checklist.md](references/checklist.md) into
   `questions.json`: id, question, options (always with "can't tell"), and the answers that fail it.
4. **Brief one subagent per piece**, with its own crop folder (it may zoom only there). One line per person (what
   they wear, where they should look), the script, what the set says this camera sees, then the questions. The
   answer is JSON only: `{"<id>": "<option>", "notes": {"<id>": "<tile or time>: <one phrase>"}}`. For a hand that
   works an object, the reviewer describes the mechanics in its own words before it reads the script's. End the
   brief with "Be honest in your response."
5. **Grade in code:** `uv run scripts/grade.py questions.json answers.json`. A FAIL stops the piece: fix it, or ask
   the owner one fix-or-accept question with the frame. Quote the reviewer's notes in the report as they are.
6. **Then look yourself, at full size**: a second mic, an earbud and doubled bracelets once passed the questions and
   were caught only at full size.

Every question in the bank was born from a defect a client or the owner saw after the automated checks had passed.
Add your own from every note a client sends.

## Model choice
Use a cheaper model (Sonnet) per piece and the strongest (Opus) only on what goes to a person: the plan checkpoint, a
fix, the final. On four saved reviews Sonnet gave the same verdicts as Opus; four is a small sample, so re-check on
your own pieces. Repeat a review only on a changed file.

## "Is the fix better?"
Ask pairwise, not by a score: A against B, then again with the order swapped, and count it only when both runs
agree. This comes from published judge research and isn't measured on our pieces yet; calibrate it on choices the
owner already made before you trust it.

## Calibrate the reviewers
Once in a while, run the brief on past defects you kept (the golden set of your QA) and count what the reviewer
catches. A question it never fails on a known defect needs rewording.
