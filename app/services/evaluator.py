import re
from app.pii.schemas import PIIEval, DetectedPII, TaskEvaluationResult


def evaluate_task_pii(input_text: str, output_text: str) -> TaskEvaluationResult:
    input_entities = detect_pii_entities(input_text)
    output_entities = detect_pii_entities(output_text)

    leaks = find_leaked_entities(input_entities, output_entities)

    return TaskEvaluationResult(
        input_eval=_entities_to_pii_eval(input_entities),
        output_eval=_entities_to_pii_eval(output_entities),
        output_leaked_pii=bool(leaks)
    )



def evaluate_pii(text: str) -> PIIEval:
    """
    Public API function to get a PII evaluation from a string of text.

    Leakage is not tocuhed here as a signle string cannot PII by itself.
    """
    entities: list[DetectedPII] = detect_pii_entities(text)
    return _entities_to_pii_eval(entities)
    

def detect_pii_entities(text: str) -> list[DetectedPII]:
    entities = []

    # loop through detectors
    email_entities = _detect_emails(text)
    entities.extend(email_entities)

    return entities


def find_leaked_entities( # check if inputted entities match any output entities = leaked pii -> PIIEval.has_pii = True
    input_entities: list[DetectedPII],
    output_entities: list[DetectedPII],
) -> list[DetectedPII]:
    
    idty_set: set[tuple[str, str]] = set() # format: type (e.g. "email"), norm_value (e.g. "john.doe@foo.bar")
    leaks: list[DetectedPII] = []

    for entity in input_entities:
        idty_set.add(_entity_identity(entity))

    for entity in output_entities:
        idty = _entity_identity(entity)

        if idty in idty_set:
            leaks.append(entity)

    return leaks


def _entities_to_pii_eval(entities: list[DetectedPII]) -> PIIEval:
    has_pii: bool = False
    types: list[str] = []
    matches: dict[str, list[str]] = {}
    risk_score: float = 0.0
    
    for entity in _dedupe_entities(entities):
        if entity.type not in matches.keys():
            matches[entity.type] = []
        
        matches[entity.type].append(entity.normalized_value)

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
        e_identity = _entity_identity(entity)

        if e_identity not in seen:
            seen.add(e_identity)
            out.append(entity)

    return out


def _entity_identity(e: DetectedPII) -> tuple[str, str]:
    return (e.type, e.normalized_value)