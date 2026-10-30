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
