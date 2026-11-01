"""The sound checks on synthetic arrays (no ffmpeg), and a master round trip when ffmpeg is there."""
import json, shutil, wave

import numpy as np
import pytest

import sound_check as sc

SR = sc.SR
rng = np.random.default_rng(7)


def noise(seconds, dbfs, sr=SR):
    """White noise at an RMS level."""
    return (rng.standard_normal(int(seconds * sr)) * 10 ** (dbfs / 20)).astype(np.float32)


def lowpass(x, hz, sr=SR):
    X = np.fft.rfft(x)
    X[np.fft.rfftfreq(len(x), 1 / sr) > hz] = 0
    return np.fft.irfft(X, len(x)).astype(np.float32)


def speech_with_floor(floor_dbfs):
    """Bursts of 'speech' with gaps, over a constant bed."""
    x = noise(6, floor_dbfs)
    for t in (0.5, 2.5, 4.5):
        x[int(t * SR):int((t + 1) * SR)] += noise(1, -20)
    return x


def test_hum_a_fan_fails_a_clean_floor_passes():
    assert sc.hum(speech_with_floor(-33))[0] == "FAIL"           # the room tone a client heard as a fan
    assert sc.hum(speech_with_floor(-85))[0] == "PASS"


def test_hum_flags_digital_silence_it_cannot_see_through():
    x = np.concatenate([speech_with_floor(-33), np.zeros(2 * SR, np.float32)])     # a silent card: 25% of it
    assert sc.hum(x)[0] == "FLAG"


def test_an_abrupt_stop_is_a_click_and_a_30_ms_fade_is_not():
    line, tail = noise(0.5, -20), np.zeros(SR // 4, np.float32)
    tag, detail = sc.clicks(np.concatenate([line, tail]))
    assert tag == "FAIL" and "0.50s" in detail
    faded = line.copy()
    faded[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))
    assert sc.clicks(np.concatenate([faded, tail]))[0] == "PASS"


def test_voice_hf_band_limited_fails_full_band_passes():
    assert sc.voice_hf(lowpass(noise(2, -20), 4000))[0] == "FAIL"   # a cheap-mic voice
    assert sc.voice_hf(noise(2, -20))[0] == "PASS"
    assert sc.voice_hf(np.zeros(SR, np.float32))[0] == "INFO"


def pause_case(burst_db=None, sr=sc.PAUSE_SR):
    """Two words with a 1.2 s pause between them; optionally a 40 ms burst in its middle."""
    x = noise(3, -70, sr)
    x[int(0.2 * sr):int(1.0 * sr)] = noise(0.8, -20, sr)
    x[int(2.2 * sr):int(2.9 * sr)] = noise(0.7, -20, sr)
    if burst_db is not None:
        x[int(1.6 * sr):int(1.64 * sr)] = noise(0.04, burst_db, sr)
    words = [{"word": "one", "start": 0.2, "end": 1.0}, {"word": "two", "start": 2.2, "end": 2.9}]
    return x, words


def test_pauses_a_burst_fails_a_quiet_pause_passes():
    assert sc.pauses(*pause_case())[0] == "PASS"
    tag, detail = sc.pauses(*pause_case(burst_db=-22))                # a laugh or chatter between the lines
    assert tag == "FAIL" and "1.6" in detail
    assert sc.pauses(*pause_case(burst_db=-22), end=0.9)[0] == "PASS"  # after --end: the card isn't judged


def test_pauses_skips_a_word_s_own_decay():
    x, words = pause_case()
    x[int(1.0 * sc.PAUSE_SR):int(1.3 * sc.PAUSE_SR)] = noise(0.3, -24, sc.PAUSE_SR)   # the tail Whisper cut off
    assert sc.pauses(x, words)[0] == "PASS"


def test_words_loader_reads_whisper_and_flat_lists(tmp_path):
    ws = [{"word": " Hi", "start": 0.0, "end": 0.3}, {"word": " there", "start": 0.4, "end": 0.8}]
    (tmp_path / "w.json").write_text(json.dumps({"text": "Hi there", "segments": [
        {"start": 0, "end": 0.8, "words": ws}, {"start": 0.8, "end": 1, "words": []}]}))
    (tmp_path / "flat.json").write_text(json.dumps(ws[::-1] + [{"word": "x", "start": 1.0, "end": 1.0}]))
    assert sc.load_words(tmp_path / "w.json") == ws
    assert sc.load_words(tmp_path / "flat.json") == ws                 # sorted, the zero-length word dropped


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_master_round_trip(tmp_path):
    import master
    x = speech_with_floor(-90) * 0.5
    with wave.open(str(tmp_path / "mix.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    master.master(tmp_path / "mix.wav", tmp_path / "out.wav", -14.0)
    assert sc.loudness(tmp_path / "out.wav", -14.0)[0] == "PASS"
    assert sc.main([str(tmp_path / "out.wav"), "--skip", "clicks,voice_hf"]) == 0   # its bursts stop dead
