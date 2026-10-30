"""The millimetre arithmetic behind size.py (no models needed)."""
import size


def test_pupils_are_the_ruler():
    assert size.to_mm(40, 40) == 63.0                  # as wide as the pupils are apart
    assert round(size.to_mm(85, 65)) == 82


def test_tolerance_and_jumps():
    assert size.in_range(66, 66, 0.8, 1.2)
    assert not size.in_range(96, 66, 0.8, 1.2)
    assert size.in_range(53, 66, 0.8, 1.2) and not size.in_range(52, 66, 0.8, 1.2)   # the floor is 0.8 x 66 = 52.8
    assert size.jumped(67, 82, 0.15) and not size.jumped(67, 70, 0.15)


def test_detector_words():
    assert size.words("a soda can") == ["soda", "can"]
    assert size.words("A Skincare Bottle with a pump") == ["skincare", "bottle", "pump"]
