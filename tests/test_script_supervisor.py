"""script_check.py on word lists and synthetic sound (no ffmpeg, no Whisper)."""
import numpy as np

import script_check as sc

SR = sc.SR
rng = np.random.default_rng(3)


def noise(seconds, dbfs):
    return (rng.standard_normal(int(seconds * SR)) * 10 ** (dbfs / 20)).astype(np.float32)


def said(text, start=0.0, each=0.3, gap=0.1):
    """Whisper-like words, one every each + gap seconds."""
    return [{"word": " " + w, "start": start + i * (each + gap), "end": start + i * (each + gap) + each}
            for i, w in enumerate(text.split())]


def test_numbers_and_split_apostrophes_read_as_the_script_writes_them():
    assert sc.norm("On the 11th floor, at 9 o 'clock.") == sc.norm("on the eleventh floor at nine o'clock")
    assert sc.norm("21st and 40th") == ["twenty", "first", "and", "fortieth"]


def test_script_a_cut_off_last_word_fails_even_when_the_rest_is_clean():
    ref = sc.norm("one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
                  "seventeen eighteen nineteen twenty one more line to say")
    assert sc.script(said(" ".join(ref)), ref)[0] == "PASS"
    assert sc.wer(ref[:-1], ref) <= sc.WER_MAX                      # one word of 25: under the WER limit
    assert sc.script(said(" ".join(ref[:-1])), ref)[0] == "FAIL"


def test_script_a_wordless_video_fails_on_any_word():
    assert sc.script([], [])[0] == "PASS"
    assert sc.script(said("thank you"), [])[0] == "FAIL"


def take(after_dbfs=None):
    """2 s of 'speech' at -20 dBFS, then 2 s of silence, with an optional 0.4 s sound 0.5 s after the speech."""
    x = np.concatenate([noise(2, -20), np.zeros(2 * SR, np.float32)])
    if after_dbfs is not None:
        x[int(2.5 * SR):int(2.9 * SR)] += noise(0.4, after_dbfs)
    return x


def test_tail_an_ad_lib_after_the_last_heard_word_fails():
    words = said("see you there on monday", each=0.4)              # the last word ends at 1.9 s
    assert sc.tail(take(), words)[0] == "PASS"
    assert sc.tail(take(-28), words)[0] == "FAIL"                   # 8 dB under the speech
    assert sc.tail(take(-45), words)[0] == "PASS"                   # a room tone


def test_tail_stops_at_the_end_of_the_body():
    words = said("see you there on monday", each=0.4)
    assert sc.tail(take(-28), words, end=2.4)[0] == "PASS"          # the sound at 2.5 s belongs to the end card


def test_dead_air_a_planned_pause_is_named_or_allowed():
    words = said("one two") + said("three four", start=2.5)         # no voice from 0.7 to 2.5 s
    assert sc.dead_air(words)[0] == "FAIL"
    assert sc.dead_air(words, quiet=[(0.5, 2.6)])[0] == "PASS"
    assert sc.dead_air(words, max_gap=2.5)[0] == "PASS"
    assert sc.dead_air(words, end=2.0)[0] == "PASS"                 # past the body


def test_pacing_slow_cuts_or_a_long_reel_fail():
    assert sc.pacing([2, 4, 6, 8, 10, 12, 14, 16], 18.0)[0] == "PASS"
    assert sc.pacing([6, 12], 18.0)[0] == "FAIL"                    # 6 s a shot
    assert sc.pacing(list(range(2, 30, 2)), 30.0)[0] == "FAIL"      # too long


def test_edges_a_cut_inside_speech_or_inside_a_word_fails():
    x = np.zeros(4 * SR, np.float32)
    x[1 * SR:2 * SR] = noise(1, -20)                                # one line, from 1 to 2 s
    assert sc.edges(x, 0.5, 2.5)[0] == "PASS"
    assert sc.edges(x, 1.2, 2.5)[0] == "FAIL"                       # in while he speaks
    assert sc.edges(x, 0.5, 1.8)[0] == "FAIL"                       # out while he speaks
    x[int(2.1 * SR):int(2.3 * SR)] = noise(0.2, -20)                # the word's last consonant after a closure
    assert sc.edges(x, 0.5, 2.09)[0] == "FAIL"
