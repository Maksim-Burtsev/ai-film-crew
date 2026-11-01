---
name: sound-mix
description: Sound for short AI videos - checks in numbers for what an agent can't hear (hum, clicks at cuts, chatter between lines, dull "cheap mic" generated voices, loudness and true peak), effects on their frames, music placement, and mastering without loudnorm. Use before anyone hears a cut, when adding effects or music, mixing dialogue, mastering to a loudness target, or when a mix sounds like a fan, clicks, pumps or "sounds cheap".
---

# Sound mix

The agent that cuts a video can't hear it. Generated voices come out band-limited, a room-tone bed reads as a fan, a
voice changer turns a model's murmur between lines into chatter, and cuts leave clicks. A viewer hears all of it in
the first seconds, and the video sounds cheap. These checks measure what can be measured, so a cut that fails never
reaches a person's ears. Everything else is the owner's ear.

## Check every cut before anyone hears it
`uv run scripts/sound_check.py <cut_nomusic.mp4> --words words.json --end <s>`

Run it on the mix without music: music hides hum and pauses. Word times come from any Whisper with word timestamps
(openai-whisper, mlx-whisper); without them the pauses check is skipped. `--end` is where the body ends, before an
end card: a silent card hides a hum, and a card's voice-over is the brand voice, not a generated one. Run the
loudness check again on the final master (`--skip hum,clicks,voice_hf`).

| Check | FAIL when | Calibrated on |
|---|---|---|
| `loudness` | integrated loudness more than 1 LU off `--target` (default -14 LUFS), or true peak above -1 dBTP | social video delivery |
| `hum` | the steady floor (the quietest tenth of 50 ms frames) is above -55 dBFS | a reel a client rejected because the room tone sounded like a fan: -33 dBFS |
| `clicks` | sound above -35 dBFS drops more than 30 dB within 5 ms | a rejected cut with 4, all at edits; the client's published reels had none |
| `pauses` | a pause between words isn't 15 dB under the speech, or a 20 ms burst in it comes within 6 dB of it | chatter a voice changer made of a model's murmur, a laugh under a cut, an ad-lib after the last line |
| `voice_hf` | speech energy above 5 kHz is more than 12 dB under the whole | a generated voice whose "s" was heard as "sh": -14.4 dB; the brand's studio voice-over: -6.7 dB |

A FAIL stops the cut: fix it, or send the owner one fix-or-accept question with the time. A FLAG means the number
can't decide: `hum` flags a cut where over a tenth is digital silence (gaps between clips), because the floor then
reads -120 and hides any bed under the rest. Listen to it. `voice_hf` judges generated speech. A dark TTS voice-over
can sit under -12 on its own: check it by ear once, then run with `--skip voice_hf`.

## When a check fails
- **hum**: find the bed (an ambience track, a room tone, a generated clip's own noise) and drop it. A varied location
  ambience (wind, birds, a distant road) low under the lines works; a constant room tone doesn't.
- **clicks**: put every in and out point in silence, with a 30 ms fade. Never move a cut only to turn a check green:
  move it to where it sounds right.
- **pauses**: clean each generated take with a speech enhancer (DeepFilterNet) first; raw generated audio never
  reaches a mix. End each voice window at the last scripted word, with a short fade.
- **voice_hf**: revoice the take. One voice-changer call per character (join their lines with short gaps, convert
  once, cut back), so the timbre holds across takes. No second enhancer pass after it: every pass costs high end.

## Effects
- **One sound per thing the picture shows, placed on its frame.** Find each footstep, contact or crack frame by
  frame and place one generated hit there. A 5 s "walking" texture over a shot with one step reads as a mechanical
  rustle.
- A still or push-in insert gets no action sound, at most one on the cut.
- Every effect plays over the shot that shows its source. A sound cue the script names gets its shot.
- Set an effect's level by its 50 ms peak in the master (~10 dB under the voices). LUFS reads a 0.1 s thud 15-20 dB
  under its peak.

## Music
- Library or trending tracks work. Clients rejected AI-generated music more often than not; if you generate it, ask
  for "no lead melody" and show raw beds first. Avoid models with non-commercial weights for paid work.
- **A talking head**: the bed sits under the voice, ducked hard (sidechain), so it fills every pause. A track with a
  big dynamic jump gets compressed flat first.
- **A dialogue comedy**: no music under the lines; a 3-5 s button after the punchline into the end card.
- **Land the peak on the payoff**: the music's peak sits on the onset of the final line's first word, both measured on
  the waveform. Offset = the track's peak time - the line's time in the video.
- Take a button from where the track really ends. A generated 20 s track can go silent seconds before its end.
- Measure music level in the master, not by the mix number: a limiter lifts music several dB against limited voices.

## Mastering
`uv run scripts/master.py <mix> <out.wav> [-14]`: a linear gain plus a 4x-oversampled true-peak limiter, corrected
until it lands on target, then measured. Social video: -14 LUFS, true peak ≤ -1 dBTP. Never master with ffmpeg
`loudnorm`: it silently switches to a dynamic mode when a linear gain would break its peak target, and the mix pumps.

Always deliver a no-music master too, and the stems (voices, effects, music) as WAVs from 0 s, when an editor might
re-cut it.

## Limits
- No taste: whether the music fits, whether an effect lands on its frame, whether a voice suits the character.
- `hum` and `voice_hf` read the whole body up to `--end`. A deliberate ambience bed fails `hum`: skip it and judge
  it by ear.
- The thresholds were set on a handful of 9:16 dialogue reels. Re-check them on your own approved and rejected cuts.
