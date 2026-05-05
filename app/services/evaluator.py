import re
from app.schemas import PIIEval
# {
#        "has_pii": true/false,
#        "types": {"email", "credit_card"},
#        "matches": {"email": ["a@b.com"]},
#        "risk_score": 0.0-1.0
# }

        

def evaluate_pii(text: str) -> PIIEval:
    has_pii: bool = False
    types: list[str] = []
    matches: dict[str, list[str]] = {}
    risk_score: float = 0.0

    _found_emails = _regex_has_email(text)
    
    if unique_emails := _dedupe_preserve_order(_found_emails, normalise=lambda s: s.lower()):
        matches["email"] = unique_emails
    
    has_pii = bool(matches)
    types = sorted(list(matches.keys()))
    risk_score = 1.0 if has_pii else 0.0

    return PIIEval(
        has_pii=has_pii,
        types=types,
        matches=matches,
        risk_score=risk_score
    )

def _regex_has_email(text: str) -> list[str]:
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    return re.findall(pattern, text)

def _dedupe_preserve_order(items: list[str], normalise=str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    for item in items:
        key = normalise(item)
        if key not in seen:
            seen.add(key)
            out.append(item)

    return out