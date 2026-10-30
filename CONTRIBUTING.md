# Contributing

Three kinds of contribution, smallest first.

1. **A lesson.** One line in the right `SKILL.md`: what failed, what worked instead, and how you know (how many
   takes, which model, which month). Model behaviour changes fast, so always name the model and the date. For example:
   "Seedance 2.0 (2026-10): without a silent head beat, 5 of 6 takes started speech on frame 0."
2. **A golden case.** A frame or a take that a check must fail (or pass), and the line it must print. Use only
   frames you have the rights to: no client material, and no real person without their consent. Open an issue first
   and we'll agree where it lives.
3. **A new check.** A script in a skill's `scripts/` that:
   - reads only the files it's given and prints one `PASS|FAIL|FLAG|INFO  <check>  <detail>` line per item,
     exiting 1 on a FAIL;
   - pins its packages in a [uv script header](https://docs.astral.sh/uv/guides/scripts/) and downloads models from
     a pinned URL, checked by sha256;
   - says in its docstring how to run it, what it catches, where it fails and what its thresholds were calibrated on;
   - comes with a test in `tests/` for every part that needs no model.

## Ground rules
- No client names, briefs, faces, voices or brand assets anywhere in the repo. The pictures are drawn in code.
- Every threshold says what it was calibrated on.
- A check that measures a number (millimetres, seconds, decibels) can stop a piece. A check that judges how a picture
  looks is a lead for the blind review, not a verdict.
- Plain words, short sentences, no hype.

## Develop

```sh
uv run --python 3.12 --with pytest==8.4.2 --with numpy==2.5.3 --with pillow==12.3.0 \
  --with opencv-python-headless==5.0.0.93 pytest -q tests
claude plugin validate .
python3 docs/pictures/render.py      # after changing a picture
```

Before a pull request that changes an instrument, run it on real frames before and after the change and write in
the PR what moved.
