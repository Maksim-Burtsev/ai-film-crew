---
name: voice-takes
description: The voice coach for AI video - keeps one voice per person across takes and catches bad reads in numbers (a line that came back in another pitch than the picked take, a rushed read with no pauses, a word that starts twice after a voice changer), plus how to audition and pick a voice. Use when choosing a voice for a character, before a line take or a TTS take is cut in, when a voice sounds different from shot to shot, or when a read sounds rushed or stutters.
---

# Voice takes

A video model doesn't hold a voice. Given the same voice description word for word, it spoke the next line 5.7
semitones lower than the take the owner had picked: the same face, another woman's voice. The agent that orders the
takes can't hear that. These checks measure what can be measured, so a wrong take is re-made before anyone listens.
Which voice is right is never measured: the ear decides, on the moving face.

## Pick the voice on the moving face
- **Audition a new voice as a short speaking take, not as audio clips under a still.** Sixteen library reads under
  five stills lost on four of five characters; the voice a video model gave one of them in a 4 s test take was right
  at first hearing. A voice picked as a standalone clip and laid over another read through a voice changer reached
  the final with the wrong tone: "the voices don't fit her or him at all".
- **The read the owner approves is the read on screen.** Drive the lips from the approved read where the model can,
  or re-take with the delivery written into the prompt.
- **Every line has a delivery, written down from a reference**: calm or loud, as the real person or the character
  plays it. A deadpan face is not a deadpan voice. It goes into the take prompt and the TTS direction. A voice
  changer at high stability flattens it.
- **One person, one voice in every shot**: the same voice block in every prompt, their lines in one take where the
  camera allows, and every later take measured against the picked one.

## Hold the pitch of the picked take
`uv run scripts/voice_check.py pitch <picked take> <take>[@<from>-<to>] [...]`

It compares each take's median pitch with the picked take's and fails a take more than 3 semitones away. Give the
words' own window (`take.mp4@1.04-3.52`, from Whisper's word times) when a take holds more than the line: room tone
and other voices pull the number.

When it fails, name the pitch in the prompt in plain positive words: "a light, bright soprano speaking voice,
clearly higher than an average woman's" brought re-takes back to 205 and 222 Hz against the pick's 224, where the
voice block alone had given 161. Measure every line before anything else is paid for on that take.

The 3 semitones come from one reel and two voices. Run it on takes you already judged and set `--max-st` between
what you heard as the same voice and what you didn't.

## Catch a rushed read
`uv run scripts/voice_check.py pace <take> [<words.json>] [...]`

A TTS read with no pauses is "rushed, one tone, impossible to listen to" however good the voice. The check fails a
take whose inner pauses (0.3 s or more) are under 12 % of its length, and, with a words file, one with fewer than a
pause per 12 words. Picked takes had 14-19 % and a pause per 10-11 words; rejected ones 0-8 % and a pause per 21-135.
Words per second did not separate them. Don't speed a take up to make it "livelier": the sped-up variants failed too.

## Catch a word that starts twice
`uv run scripts/voice_check.py stutter <dialogue stem> [...]`

A voice changer fed a take that speaks from its first frame gives the first word a burst, a dip and a second attack:
"W-wait". Run it on stems, before mastering (gain moves the thresholds). Fix it at the source: give the changer a
window that starts in silence, or a clean read of that word in the same changer call. Cutting the burst out after
the changer was still heard.

## What didn't work
- **A speaker-similarity score as a judge.** On our takes one voice in two takes scored 0.41-0.76 and two different
  voices up to 0.49 (ECAPA embeddings): the bands overlap, and the score once ranked first the voices the owner
  called "not even close". It can screen out an obvious miss. It never picks a winner, so it isn't shipped here.
- **The same voice description as a lock.** It doesn't hold pitch. Measure.
- **A second enhancer pass after a voice changer.** Every pass costs high end (sound-mix's `voice_hf` shows it).

## Limits
- Pitch is one number. Two voices can share a pitch and still be two people: the ear decides.
- A take with music or two speakers in the window reads wrong. Give the line's own window, on the dialogue stem.
- `pace` is calibrated on English TTS reads of 10 s and longer. A one-line take has no inner pauses to count.
- `pitch` comes from one reel: on its seven saved takes it gives the numbers of the tool it was lifted from. `stutter`
  has a kept failing case from a real reel. `pace`'s kept failing case is a made one (a good take with its pauses cut
  out); the takes it was calibrated on are gone.
