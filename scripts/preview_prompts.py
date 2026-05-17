from app.services.redteam_prompts import generate_redteam_prompts

SEED = 42


prompts = generate_redteam_prompts(seed=SEED)

for p in prompts:
    print(p.category)
    print(p.prompt)
    print(f"Expected PII Types: {p.expected_pii_types}")
    print("-----")