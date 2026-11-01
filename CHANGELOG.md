# Changelog

## 0.2.0 (2026-11-01)

One more crew member, and a fix for over-the-shoulder shots.

- **sound-mix**: `sound_check.py` measures what an agent can't hear in a cut: a hum under the voices, clicks at cuts,
  chatter between lines, dull generated voices, loudness and true peak. `master.py` masters to a loudness target
  without `loudnorm`.
- **scene-set**: a back near the lens (an over-the-shoulder shot) now counts as in frame, and a look a few degrees past
  the lens at it no longer reads as "into the lens".

## 0.1.0 (2026-10-31)

The first four crew members.

- **product-size**: `size.py` measures a product in millimetres in stills and takes by the holder's pupils, and fails
  a product drawn too big or too small, a size that jumps between shots and a stretched product.
- **scene-set**: `scene.py` turns one set file into a top plan, prompt cards, layout images and fact questions;
  `frame_check.py` checks the faces in a generated still against what its camera should see. Four example sets.
- **recurring-cast**: `identity.py` scores faces against a person's real photos with a threshold calibrated on your
  own judged stills (SFace by default, ArcFace by path); `keepface.py` puts the original face back after an edit.
- **blind-review**: a bank of 46 questions born from real defects, and `grade.py` to grade the answers in code.
- One-command install as a Claude Code plugin.
