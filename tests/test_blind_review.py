"""grade.py: answers against the accepted ones."""
import grade

Q = [{"id": "F1", "options": ["same", "a lookalike", "someone else", "can't tell"], "fail": ["a lookalike", "someone else"]},
     {"id": "H6", "options": ["same", "changed", "can't tell"], "fail": ["changed"]},
     {"id": "C1", "options": ["bigger", "same", "smaller", "can't tell"], "accept": ["same"]}]


def tags(answers):
    return {qid: tag for tag, qid, _ in grade.grade(Q, answers)}


def test_pass_fail_flag():
    assert tags({"F1": "same", "H6": "changed", "C1": "same"}) == {"F1": "PASS", "H6": "FAIL", "C1": "PASS"}
    assert tags({"F1": "can't tell", "H6": "same", "C1": "bigger"}) == {"F1": "FLAG", "H6": "PASS", "C1": "FAIL"}


def test_missing_or_invented_answers_fail():
    assert tags({"F1": "same", "C1": "same"})["H6"] == "FAIL"
    assert tags({"F1": "probably her", "H6": "same", "C1": "same"})["F1"] == "FAIL"
