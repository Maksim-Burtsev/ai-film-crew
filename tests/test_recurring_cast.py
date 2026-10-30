"""The calibration arithmetic behind identity.py (no models needed)."""
import identity


def test_threshold_sits_in_the_gap():
    t, gap = identity.threshold([0.51, 0.62, 0.75], [0.14, 0.30, 0.45])
    assert round(gap, 2) == 0.06 and round(t, 2) == 0.48


def test_overlap_gives_no_threshold():
    t, gap = identity.threshold([0.30, 0.44], [0.29, 0.38])
    assert t is None and gap < 0
