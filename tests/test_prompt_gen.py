from app.services.evaluator import evaluate_pii
from app.services.redteam_prompts import generate_redteam_prompts, PROMPT_BUILDERS
from app.schemas import PIIEval


def test_generate_rt_prompts_all_categories():
    prompts = generate_redteam_prompts(seed=42)

    generated_categories = {p.category for p in prompts}
    expected_categories = set(PROMPT_BUILDERS.keys())

    assert generated_categories == expected_categories
    

def test_generated_rt_prompts_have_expected_pii():
    prompts = generate_redteam_prompts(seed=42)

    for p in prompts:
        eval_result = evaluate_pii(p.prompt)

        assert p.prompt.strip()
        assert p.expected_pii_types
        assert eval_result.has_pii is True

        for pii_type in p.expected_pii_types:
            assert pii_type in eval_result.types