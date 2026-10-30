---
name: scene-set
description: Lock the geometry of a multi-shot AI video in one set file before any picture: room, furniture, props, every person's seat and facing, one camera per setup. Use when planning shots or stills, writing image prompts for a scene, or when shots of one scene disagree (a moved table, flipped eyelines, wrong heights).
---

# Set first

Every shot is a view of one set. People, furniture and light never move between shots; only the camera does.
Stills prompted one by one, without a set, drifted: they turned the table, moved people across the room, stood up
someone who should sit and flipped eyelines between the wide and the singles.

`scripts/scene.py` does the work: `uv run scripts/scene.py <command> ...`, from the project root. Its docstring
documents the set file (TOML, metres, top view) and the optional cast file.

1. **Write `set.toml` from a real reference.** Walls, window, light side, the table and its axis, every prop, each
   person's place, posture, facing and garment colours, one camera per setup (`talk = true` on cameras that carry
   lines). For a podcast, start from `examples/` (geometry of top real shows). For a video that already exists,
   read the set off its widest approved frame, then check it against every approved shot.
2. **`scene.py plan set.toml plan.png`**: top view, cameras, the 180° line. It fails a camera across the line or a
   face into the lens. The owner reads the room from this picture, shown with the storyboard.
3. **Prompts come from the set.** Each still prompt opens with `scene.py card set.toml <cam>` verbatim and passes
   `scene.py block set.toml <cam> block.png` as the layout image (text alone never held a layout).
   `scene.py refs` adds each person's cast images and the sentence that numbers them.
4. **Check stills against the set.** `scene.py ask` writes fact questions for one frame ("which side is the
   window on?"); a blind reviewer answers them (see blind-review), and `scene.py grade` compares. Vision models are
   poor at "are these shots consistent?" and fair at "which side is the window?": the reviewer answers facts, the
   set decides. `scene.py sheet` puts plan, blockout, candidate and neighbours in one image.

Done when: every planned shot names its camera, `plan` prints no warnings, and every approved still passes `grade`.

## Props are part of the set
Write where each person's mic, mug, notes and glasses are, which hand holds what, and the mount of every mic. A
prop's side can turn the model's eyeline: a mic on the outer side turned a speaker away from the host in 7 of 11
stills. Make a person's second still an edit of the first so mounts and props match. Give the blind review the prop
questions (how many mics, which side, what the hands hold).

## Coverage that holds up
- One single per speaker, all on one side of the line. Lines only in singles, never in a wide.
- A silent wide only for an action the story needs (≤ 1.5 s, nobody facing the lens).
- Two people the set puts far apart share a frame only in a wide.
