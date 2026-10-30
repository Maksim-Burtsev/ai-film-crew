---
name: scene-set
description: Lock the geometry of a multi-shot AI video in one set file before any picture, then check every generated still against it - room, furniture, props, every person's seat and facing, one camera per setup. Use when planning shots or stills, writing image prompts for a scene, checking a still before paying for video, or when shots of one scene disagree (a moved table, swapped seats, flipped eyelines, wrong heights, light from the wrong side).
---

# Set first

Every shot is a view of one set. People, furniture and light never move between shots; only the camera does.
Stills prompted one by one, without a set, drifted: they turned the table, moved people across the room, stood up
someone who should sit and flipped eyelines between the wide and the close-ups.

Two scripts, run from the project root with `uv run`:
- `scripts/scene.py`: the set file in, the plan, prompt cards, layout images and fact questions out. Its docstring
  documents the set file (TOML, metres, top view) and the optional cast file.
- `scripts/frame_check.py`: a generated still or take in, one PASS/FAIL line per check out.

1. **Write `set.toml` from a real reference.** Walls, window, light side, the table and its axis, every prop, each
   person's place, posture, facing and garment colours, one camera per setup (`talk = true` on cameras that carry
   lines). Start from `examples/` (a podcast desk, a round podcast table, a couch, a meeting table). For a video that
   already exists, read the set off its widest approved frame, then check it against every approved shot.
2. **`scene.py plan set.toml plan.png`**: the top view, cameras, the 180° line. It fails a camera across the line or
   a face into the lens. Show this picture with the storyboard: people read a room from it.
3. **Prompts come from the set.** Each still prompt opens with `scene.py card set.toml <cam>` verbatim and passes
   `scene.py block set.toml <cam> block.png` as the layout image (text alone never held a layout).
   `scene.py refs` adds each person's cast images and the sentence that numbers them.
4. **Check every still before it becomes video.** `frame_check.py set.toml <cam> still.png` compares the faces in
   the still with what this camera should see: how many, which side, who is closer, whose head is higher, which way
   each looks, which side the light comes from, how big the speaker's face is. A FAIL stops the still. Re-roll it or
   fix the set; never buy a take from it.
5. **Ask the facts too.** `scene.py ask` writes fact questions for one frame ("which side is the window on?"); a
   blind reviewer answers them (see blind-review) and `scene.py grade` compares. Vision models are poor at "are these
   shots consistent?" and fair at "which side is the window?": the reviewer answers facts, the set decides.
   `scene.py sheet` puts plan, layout, candidate and neighbours in one image.

Done when: every planned shot names its camera, `plan` prints no warnings, and every approved still passes
`frame_check.py` and `grade` (or each FAIL was looked at and answered).

## What frame_check can't see
It measures faces, not meaning. It misses a medium shot drawn where the set wants a close-up, and a hand over a face
reads as no face. A FLAG means "look yourself". When it disagrees with your eye, the blind review decides.

## Props are part of the set
Write where each person's mic, mug, notes and glasses are, which hand holds what, and the mount of every mic. A
prop's side can turn the model's eyeline: a mic on the outer side turned a speaker away from the host in 7 of 11
stills. Make a person's second still an edit of the first so mounts and props match. Give the blind review the prop
questions (how many mics, which side, what the hands hold).

## Coverage that holds up
- One close-up per speaker, all from one side of the line. Lines only in close-ups, never in a wide.
- A silent wide only for an action the story needs (≤ 1.5 s, nobody facing the lens).
- Two people the set puts far apart share a frame only in a wide.
