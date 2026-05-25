import app.services.evaluator as eval
from app.pii import PIIEval

def test_no_pii():
    prompt1 = "hello"
    prompt2 = "foo @ bar"
    prompt3 = "let's meet @ 3:00"

    res1: PIIEval = eval.evaluate_pii(prompt1)
    res2: PIIEval = eval.evaluate_pii(prompt2)
    res3: PIIEval = eval.evaluate_pii(prompt3)

    assert res1.has_pii is False
    assert res2.has_pii is False
    assert res3.has_pii is False
    assert res1.risk_score == 0.0 == res2.has_pii == res3.has_pii

def test_single_email_pii():
    prompt = "email me at: john.doe@foo.bar"

    res: PIIEval = eval.evaluate_pii(prompt)

    assert res.has_pii is True
    assert res.risk_score > 0.0
    assert res.matches["email"] is not None


def test_detect_pii_entities_returns_email_metadata():
    text = "Email Jane at Jane.Doe@Example.com please."

    entities = eval.detect_pii_entities(text)

    assert len(entities) == 1

    entity = entities[0]
    assert entity.type == "email"
    assert entity.value == "Jane.Doe@Example.com"
    assert entity.normalized_value == "jane.doe@example.com"
    assert entity.start_idx == text.index("Jane.Doe@Example.com")
    assert entity.end_idx == entity.start_idx + len("Jane.Doe@Example.com")
    assert entity.confidence == 0.9
    assert entity.source == "regex"


def test_detect_pii_entities_keeps_duplicate_normalized_occurences():
    text = "Jane.Doe@Example.com jane.doe@example.com"

    entities = eval.detect_pii_entities(text)

    assert len(entities) == 2
    assert entities[0].value == "Jane.Doe@Example.com"


def test_find_leaked_entities_detects_same_email():
    input_entities = eval.detect_pii_entities("User email is jane@example.com")
    output_entities = eval.detect_pii_entities("Contact jane@example.com for help")

    leaked = eval.find_leaked_entities(input_entities, output_entities)

    assert len(leaked) == 1
    assert leaked[0].value == "jane@example.com"


def test_duplicate_email_in_output_is_in_leaked():
    input_entities = eval.detect_pii_entities("User email is jane@example.com")
    output_entities = eval.detect_pii_entities("Contact jane@example.com for help. The email is Jane@Example.Com")

    leaked = eval.find_leaked_entities(input_entities, output_entities)

    assert len(leaked) == 2
    assert leaked[0].value == "jane@example.com"
    assert leaked[0].normalized_value == "jane@example.com"
    assert leaked[1].value == "Jane@Example.Com"
    assert leaked[1].normalized_value == "jane@example.com"


def test_find_leaked_entities_empty_with_input_email_diff_output_email():
    input_entities = eval.detect_pii_entities("User email is jane@example.com")
    output_entities = eval.detect_pii_entities("Contact support@example.com for help.")

    leaked = eval.find_leaked_entities(input_entities, output_entities)

    assert len(leaked) == 0


def test_evaluate_task_pii_distinguishes_output_pii_from_leaked_pii():
    task_pii_eval = eval.evaluate_task_pii(
        input_text="email me at: john.doe@foo.bar",
        output_text="email support@example.com for assistance.",
    )

    assert task_pii_eval.input_eval.has_pii is True
    assert task_pii_eval.input_eval.matches["email"] == ["john.doe@foo.bar"]
    assert task_pii_eval.output_eval.has_pii is True
    assert task_pii_eval.output_eval.matches["email"] == ["support@example.com"]
    assert task_pii_eval.output_leaked_pii is False


def test_evaluate_task_pii_marks_same_normalized_email_as_leaked():
    task_pii_eval = eval.evaluate_task_pii(
        input_text="email me at: Jane.Doe@Example.com",
        output_text="Contact jane.doe@example.com for assistance.",
    )

    assert task_pii_eval.input_eval.has_pii is True
    assert task_pii_eval.output_eval.has_pii is True
    assert task_pii_eval.output_leaked_pii is True

