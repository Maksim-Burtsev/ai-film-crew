---
name: script-supervisor
description: The script supervisor for AI video - checks a take or a cut against its script in code (the words said, a cut-off last line, an ad-lib after it, dead air, the pace of the cuts, a take cut mid-word) and runs the continuity pass that catches goofs between shots (a shelf with other bottles, two people with one backdrop, a prop where nobody would put it). Use before a take is cut in, before any cut reaches a person, when a line sounds cut off or the reel drags, or when shots of one scene don't match.
---

# Script supervisor

On a film set one person holds the script and watches for what no department owns: a line that changed, a glass
that was full in the last shot, a cut that lands in the middle of a word. In generated video nobody has that job.
The agent that cuts the reel can't hear it, a video model ad-libs after the last line, and every still is drawn
without knowing what the one before it showed. Half of one reel's review notes were goofs of this kind, and they got past
every check that existed.

Two passes: code for the words and the clock, a blind reviewer for the continuity.

## The words and the clock
Transcribe the take or the cut with any Whisper that writes word times (openai-whisper, mlx-whisper), then:

`uv run scripts/script_check.py <video|audio> script.txt --words words.json --end <s>`

`script.txt` holds every spoken word in order. `--end` is where the words end, before a wordless end card (Whisper
writes words over a card's silence). If the script has brand or character names, transcribe twice, once with the
names as Whisper's prompt, and pass both files (`--words plain.json,primed.json`): the one nearer the script counts
and both are printed, so the prompt can't hide a real mishearing.

| Check | FAIL when | Calibrated on |
|---|---|---|
| `script` | word error rate over 5 %, or the last heard word isn't the script's last word | a voice-over cut off before its last word reads clean everywhere else |
| `tail` | there is sound after the last heard word, within 15 dB of the speech's loudest moment | a take that ad-libbed three words after its line, 8 dB under the speech: Whisper dropped them and the transcript matched |
| `dead_air` | no voice for over `--max-gap` (1.0 s) between two words | dialogue reels; an approved voice-over paused up to 2.5 s between lines on purpose |
| `pacing` | average shot length over `--max-asl` (3.0 s) or the file over `--max-len` (25 s) | one brand's published 9:16 comedy reels: 2.3-2.4 s a shot |

A FAIL stops the piece: fix it, or send the owner one fix-or-accept question with the time.

- **`tail` fails**: transcribe the audio from the time it prints. If it is words, re-take or end the voice window at
  the last scripted word with a short fade. If it is an effect, pass `--end` before it.
- **`dead_air` fails on a pause you planned**: name the stretch (`--quiet 15.0-16.5`) or raise `--max-gap`. A pause
  inside a phrase is still dead air.
- **Set the pace from your own references.** `uv run scripts/script_check.py pace <reel> [...]` prints the shots,
  average shot length and length of reels you want to sound like. Use those for `--max-asl` and `--max-len`. The
  defaults are one brand's taste, not a rule.

### Before a take goes into the cut
`uv run scripts/script_check.py edges <the take's dialogue> <in s> <out s>`

It fails when the take isn't quiet in the 80 ms after the in point or before the out point, or sounds again within
0.2 s past the out point. An out point can sit in the silence inside a word: "six" cut in the closure of its "k"
was heard as "si-k". A take whose speech starts on its first frame fails too: the generator clipped the first word.
Never move a cut only to turn the check green: move it to where the line ends.

## The continuity pass
Code can't see that a shelf changed. A fresh reviewer can, when the question is narrow. Run the blind-review skill
with the K questions from its question bank, on the stills before any take is bought and again on the cut:

1. Give the reviewer every still of the scene (or the cut's frames at 2 fps), in order, numbered.
2. Before the questions, it writes one line per shot: what stands on each shelf, counter and table, and in what
   state. This is what makes the comparison possible; without it the reviewer answers from a general impression.
3. It answers K1-K9 with their fixed options. `grade.py` prints a FAIL line per failing answer.
4. Each FAIL is fixed, or stands on the owner's page as a choice with the frame. Never as prose in a report: on the
   reel this pass comes from, two of the goofs had been written down in an earlier review as free text, nobody had
   to act on them, and both reached the owner, one in the final.

What the questions cover: the same things on a surface seen twice (K1), two people with one backdrop (K2), a prop's
state from shot to shot (K3), things where nobody would put them (K4), dressing that reads as a real place (K5), the
subject cut by the frame (K6), the surface under the product from every camera (K7), people standing as the script
casts them (K8), a pose that jumps at a cut inside one beat (K9).

## Watch the story before paying for it
Cut the checked stills to the real timing with the lines and watch it as an animatic before any take is bought.
A weak beat is visible on stills; found in the final, it costs a re-shoot. A fix round that adds a shot names the
shot that goes: one reel grew from 15 s to 29 s over its fix rounds.

In an animatic, a person whose voice is already picked is never played in a stand-in voice. A line with no take in
the picked voice stays silent, its words on screen for its timed length. Scratch reads time the cut and are never
heard: a stand-in "for timing" was heard as "you changed his voice".

## Limits
- It reads words and time, not delivery. Whether a line lands is the ear's call.
- `script` is as good as the transcript. Whisper mishears names and drops short tails: that's why `tail` exists and
  why two transcripts are compared.
- `pacing` finds hard cuts only. A dissolve or a whip pan isn't counted; give the cut times in `--cuts`.
- An end card counts as a shot, so the average shot length reads a little long on a short reel.
- Only `tail` has a real failing case we kept. `script`, `dead_air` and `pacing` are tested on approved reels that
  must pass and on synthetic cases; `edges` on synthetic sound only. The cuts that first failed them are gone.
  Cut detection matched the edit lists of two reels by shot count; it wasn't compared cut by cut.
