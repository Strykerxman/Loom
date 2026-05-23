from app.services.evaluator import detect_pii_entities, evaluate_pii
from app.pii import PIIEval

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


def test_detect_pii_entities_returns_email_metadata():
    text = "Email Jane at Jane.Doe@Example.com please."

    entities = detect_pii_entities(text)

    assert len(entities) == 1

    entity = entities[0]
    assert entity.type == "email"
    assert entity.value == "Jane.Doe@Example.com"
    assert entity.normalized_value == "jane.doe@example.com"
    assert entity.start_idx == text.index("Jane.Doe@Example.com")
    assert entity.end_idx == entity.start_idx + len("Jane.Doe@Example.com")
    assert entity.confidence == 0.9
    assert entity.source == "regex"


def test_detect_pii_entities_dedupes_normalized_email_values():
    text = "Jane.Doe@Example.com jane.doe@example.com"

    entities = detect_pii_entities(text)

    assert len(entities) == 1
    assert entities[0].value == "Jane.Doe@Example.com"