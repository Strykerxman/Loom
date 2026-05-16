from app.services.redteam_prompts import generate_redteam_prompts

SEED = 42
COUNT = 5

prompts = generate_redteam_prompts(COUNT, seed=SEED)

for p in prompts:
    print(p.category)
    print(p.prompt)
    print("-----")