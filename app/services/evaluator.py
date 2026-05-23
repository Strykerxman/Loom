import re
from app.pii.schemas import PIIEval, DetectedPII


def evaluate_pii(text: str) -> PIIEval:
    """
    Public API function to get a PII evaluation from a string of text.
    """
    entities = detect_pii_entities(text)
    return _entities_to_pii_eval(entities)
    

def detect_pii_entities(text: str) -> list[DetectedPII]:
    entities = []

    # loop through detectors
    email_entities = _detect_emails(text)
    entities.extend(email_entities)

    return _dedupe_entities(entities)   


def _entities_to_pii_eval(entities: list[DetectedPII]) -> PIIEval:
    has_pii: bool = False
    types: list[str] = []
    matches: dict[str, list[str]] = {}
    risk_score: float = 0.0
    
    for entity in entities:
        if entity.type not in matches.keys():
            matches[entity.type] = []
        
        matches[entity.type].append(entity.value)

    has_pii = bool(matches)
    types = sorted(list(matches.keys()))
    risk_score = min(1.0, len(entities) * 0.1)

    return PIIEval(
        has_pii=has_pii,
        types=types,
        matches=matches,
        risk_score=risk_score
    )


def _detect_emails(text: str) -> list[DetectedPII]:
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    emails = []

    for email in re.finditer(pattern, text):
        raw_email = email.group(0)
        norm_email = raw_email.lower()

        emails.append(
            DetectedPII(
                type="email",
                value=raw_email,
                normalized_value=norm_email,
                start_idx=email.start(),
                end_idx=email.end(),
                confidence=0.9,
                source="regex"
            ))
        
    return emails


def _dedupe_entities(entities: list[DetectedPII]) -> list[DetectedPII]:
    seen: set[tuple[str, str]] = set()
    out: list[DetectedPII] = []

    for entity in entities:
        if (entity.normalized_value, entity.type) not in seen:
            seen.add((entity.normalized_value, entity.type))
            out.append(entity)

    return out