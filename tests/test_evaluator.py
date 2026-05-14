from app.services.evaluator import evaluate_pii
from app.schemas import PIIEval

def test_no_pii():
    prompt1 = "hello"
    prompt2 = "foo @ bar"
    prompt3 = "let's meet @ 3:00"

    res1: PIIEval = evaluate_pii(prompt1)
    res2: PIIEval = evaluate_pii(prompt2)
    res3: PIIEval = evaluate_pii(prompt3)

    assert res1.has_pii is False
    assert res2.has_pii is False
    assert res3.has_pii is False
    assert res1.risk_score == 0.0 == res2.has_pii == res3.has_pii

def test_single_email_pii():
    prompt = "email me at: john.doe@foo.bar"

    res: PIIEval = evaluate_pii(prompt)

    assert res.has_pii is True
    assert res.risk_score > 0.0
    assert res.matches["email"] is not None