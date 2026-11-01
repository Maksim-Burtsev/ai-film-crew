"""The set geometry and the frame check's rules, on the example sets (no models needed)."""
from pathlib import Path

import pytest

import frame_check
import scene

EXAMPLES = sorted((Path(__file__).resolve().parent.parent / "skills/scene-set/examples").glob("*.toml"))


def views(name, cam):
    s = scene.load(str(EXAMPLES[0].parent / f"{name}.toml"))
    return {e["id"]: e for e in scene.view(s, scene.Cam(s, scene.find(s, cam)))}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_every_example_plan_is_clean(path):
    warnings, _ = scene.warnings(scene.load(str(path)))
    assert warnings == []


def test_couch_everyone_looks_screen_left_at_the_tv():
    v = views("couch", "W")
    assert {v[p]["looks"] for p in ("jo", "ana", "leo")} == {"screen-left"}
    assert v["jo"]["u"] < v["ana"]["u"] < v["leo"]["u"]


def test_meeting_close_ups_look_across_the_table():
    assert views("meeting", "A")["ana"]["looks"] == "screen-right"
    assert views("meeting", "B")["leo"]["looks"] == "screen-left"


def face(u=0.5, yaw=0.0, face_px=270.0, lit=0.0):
    return {"u": u, "v": 0.4, "face_px": face_px, "face_w": 0.3, "yaw": yaw, "iris": 0.0, "lit": lit}


def test_frame_check_eyelines():
    exp = list(views("meeting", "A").values())
    ok = frame_check.judge(exp, [face(yaw=0.2)])
    assert ok["faces"][0] and ok["eyelines"][0] is True
    assert frame_check.judge(exp, [face(yaw=-0.2)])["eyelines"][0] is False      # looks the other way
    assert frame_check.judge(exp, [face(yaw=0.0)])["eyelines"][0] is None        # into the lens: look yourself


def test_frame_check_counts_faces():
    exp = list(views("meeting", "A").values())
    assert frame_check.judge(exp, [face(), face(u=0.8)])["faces"][0] is False


OVER_THE_SHOULDER = """
room = [5.0, 4.5]
[[person]]
id = "host"
at = [1.5, 2.6]
pose = "sits"
faces = "guest"
[[person]]
id = "guest"
at = [3.5, 2.6]
pose = "sits"
faces = "host"
[[camera]]
id = "R"
at = [0.5, 2.85]
h = 1.25
aim = "guest"
lens = 115
"""


def test_over_the_shoulder_back_is_in_frame_and_the_look_is_just_past_the_lens(tmp_path):
    # Behind the host's shoulder on a long lens, the host's head centre falls off the frame while the head fills its
    # right edge; the guest, looking at the host 4.8 deg off the lens, is not looking into it.
    (tmp_path / "ots.toml").write_text(OVER_THE_SHOULDER)
    s = scene.load(str(tmp_path / "ots.toml"))
    v = {e["id"]: e for e in scene.view(s, scene.Cam(s, scene.find(s, "R")))}
    assert v["host"]["face"] == "back" and v["host"]["u"] > 1.05 and v["host"]["visible"]
    assert v["guest"]["looks"] == "just past the lens, screen-right,"
    card = scene.card(s, "R")
    assert "close to the lens and out of focus, filling the frame's right edge (about 24% of its width)" in card
    assert "off frame" not in card
    assert scene.warnings(s) == ([], [])
