---
name: recurring-cast
description: Keep a recurring AI character the same person across shots and videos (face, age, body, props, voice), and check it with a face model calibrated on your own judged stills. Use before the first paid still of a person, when a face drifts or a lookalike appears, when someone says "that's not her", or when picking a face, gesture or voice for a character.
---

# Recurring cast

A viewer forgives a lot, but not a face that changes. Each failure below once reached a client.

## One card per person, before the first paid still
The card holds: the face's source, the look (hair, glasses, garments, jewellery, which wrist), height and build,
posture and gestures (in and out), the voice and its direction. A taste the owner or client states in chat ("he
takes up space", "never a plain tee") goes into the card the same day. One unwritten taste once cost two hours of
gesture rounds.

## Where a face comes from
- **Real photos, or a still the client approved.** Never an earlier video's stray frame, which compounds drift.
  At most one edit pass away from that source.
- **A turnaround sheet** for a person who appears from many angles: six head angles (front, both 3/4, both
  profiles, back) plus full length front, side and back, with height. Pass the view nearest the camera's angle, the
  real photo (it decides face and age), and the front; never the sheet itself (a multi-view sheet gets copied as
  twins). Image models read about four character images at most.
- **Mark flawed views** (one reads older, one has the wrong hair) and never pass them.
- **Age only at the client's own number**, one pass. Never "younger" or "fresher" on your own.

## Check the face with a model, calibrated on your stills
`scripts/identity.py` turns each face into numbers with a face model and compares them with the person's real
photos (5 to 20, in one folder).

1. **Calibrate once per person:** `uv run scripts/identity.py calibrate --refs photos/ana --same approved/ --other
   rejected/`. It scores stills you judged "the same person" and "someone else", prints both ranges and a threshold
   in the gap, or says this model can't tell them apart on your stills.
2. **Score every still:** `identity.py score stills/*.png --refs photos/ana --min <threshold>`.
3. **Score every take against its own first still:** `identity.py score take.mp4 --against first_still.png --min
   0.80`. Video and lip-sync models drift a face mid-take; 0.80 held on lip-sync clips, re-check it on yours.

A score screens. It never picks the winner and never excuses a reject: the side-by-side look and the blind review
decide. Faces under ~250 px tall, profiles and covered eyes score like strangers.

**Which face model.** SFace, the default (Apache 2.0), catches a different person. On one cast it scored the other
characters 0.10-0.27 against 0.86 for the person herself, but it scored a lookalike actor 0.52-0.55, where ArcFace
gave 0.38-0.41. ArcFace (InsightFace w600k_r50) separates lookalikes better, but its published weights are licensed
for non-commercial research only: for client work, license it or use a commercial face-comparison service, and pass
`--model arcface --arcface <path>` only with a copy you're allowed to use. Whatever the model, calibrate on your own
stills: thresholds don't carry over between models.

## More checks
- **All stills of one person side by side** before any lip-sync, on the face and on the background. Each pose can
  pass alone while the final shows three slightly different people.
- **Face size**: a face under ~250 px tall in a 1080x1920 frame doesn't hold. Video models morph it, and image
  models draw a different person. Redraw a small head on a 4x crop from the refs and paste it back. A close-up is its
  own still, never an upscaled crop.
- **One quality tier per video**: every face gets the same model, resolution and framing floor. A visible
  difference costs more than the dollar it saves.
- **Props on people are identical in every shot**: glasses whole (both rims, bridge, temples), the same jewellery.
  Check at full size, both sides of the head; contact sheets hide these.

## Taste on raw candidates
A choice of face, gesture or voice goes to the owner as cheap raw candidates, labelled raw. Checks and polish run
only on the pick: one pose was polished through four reviews, then dropped in two minutes.
