"""voice_check.py on synthetic voices (no ffmpeg)."""
import numpy as np

import voice_check as vc

SR = vc.SR


def voice(hz, seconds, amp=0.1):
    """A buzzy tone with a pitch: the first five harmonics."""
    t = np.arange(int(seconds * SR)) / SR
    return (amp * sum(np.sin(2 * np.pi * hz * k * t) / k for k in range(1, 6))).astype(np.float32)


def test_pitch_a_line_five_semitones_under_the_picked_take_fails():
    tag, st, f, f0 = vc.pitch(voice(224, 2), voice(161, 2))
    assert tag == "FAIL" and -6.2 < st < -5.2 and abs(f0 - 224) < 3
    assert vc.pitch(voice(224, 2), voice(205, 2))[0] == "PASS"
    assert vc.pitch(voice(224, 2), voice(205, 2), max_st=1.0)[0] == "FAIL"


def test_pitch_silence_has_no_pitch_and_fails():
    assert vc.pitch(voice(224, 2), np.zeros(2 * SR, np.float32))[0] == "FAIL"


def read(pause):
    """Six phrases of 1 s on moving pitches, with `pause` seconds between them."""
    gap = np.zeros(int(pause * SR), np.float32)
    return np.concatenate([np.concatenate([voice(hz, 1.0), gap]) for hz in (180, 220, 200, 240, 190, 210)])[:-len(gap) or None]


def test_pace_a_read_without_pauses_is_rushed():
    assert vc.pace(read(0.5))[0] == "PASS"
    tag, detail = vc.pace(read(0.02))
    assert tag == "FAIL" and "rushed" in detail


def test_pace_too_many_words_per_pause_is_a_run_on():
    assert vc.pace(read(0.5), n_words=40)[0] == "PASS"              # five pauses
    assert "run-on" in vc.pace(read(0.5), n_words=90)[1]


def word(burst):
    """Silence, then a word at -15 dBFS; with `burst`, a 10 ms pulse at -24 and a 20 ms dip before it."""
    lv = lambda db: 10 ** (db / 20) * np.sqrt(2)
    x = np.zeros(SR, np.float32)
    t = np.arange(SR) / SR
    tone = np.sin(2 * np.pi * 200 * t).astype(np.float32)
    a = int(0.4 * SR)
    if burst:
        x[a:a + 160] = tone[:160] * lv(-24)
        x[a + 160:a + 480] = tone[:320] * lv(-40)
        x[a + 480:a + 5000] = tone[:4520] * lv(-15)
    else:
        ramp = np.linspace(0, 1, 800)
        x[a:a + 800] = tone[:800] * lv(-15) * ramp
        x[a + 800:a + 5000] = tone[:4200] * lv(-15)
    return x


def test_stutter_two_attacks_for_one_word():
    assert len(vc.stutter(word(burst=True))) == 1
    assert vc.stutter(word(burst=False)) == []
