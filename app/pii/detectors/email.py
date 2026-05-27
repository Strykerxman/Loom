from .base import BaseDetector
from app.pii.schemas import DetectedPII
import re


_OBFUSCATED_AT = r"(?:\[\s*at\s*\]|\(\s*at\s*\))"
_OBFUSCATED_DOT = r"(?:\[\s*dot\s*\]|\(\s*dot\s*\))"
_OBFUSCATED_LOCAL_PART = rf"[A-Za-z0-9_%+-]+(?:\s*{_OBFUSCATED_DOT}\s*[A-Za-z0-9_%+-]+)*"

class EmailDetector(BaseDetector):
    def __init__(self) -> None:
        self._type = "email"
        self._pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
        self._obf_pattern = re.compile(
            rf"""
       (?<![A-Za-z0-9._%+-])
       (?P<local>{_OBFUSCATED_LOCAL_PART})
       \s*{_OBFUSCATED_AT}\s*
       (?P<domain>
           [A-Za-z0-9-]+
           (?:
               \s*{_OBFUSCATED_DOT}\s*
               [A-Za-z0-9-]+
           )*
       )
       \s*{_OBFUSCATED_DOT}\s*
       (?P<tld>[A-Za-z]{{2,}})
       (?![A-Za-z0-9-])
       """,
       re.IGNORECASE | re.VERBOSE,
        )


    @property
    def type(self) -> str:
        return self._type
    

    @property
    def pattern(self) -> re.Pattern:
        return self._pattern
    

    @property
    def obf_pattern(self) -> re.Pattern:
        return self._obf_pattern
    
    
    def detect(self, text) -> list[DetectedPII]:
        """
        Performs detection over standard email types (e.g., john.doe@example.com) and
        over obfuscated email types (jane[dot]doe[at]example[dot]com)

        Inputs:
        - text: the string of text to be scanned for emails.
        """
        def _detect_standard_emails() -> list[DetectedPII]:
            emails = []
            for email in re.finditer(self.pattern, text):
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
                        source="regex.email"
                    ))
            
            return emails
        
        
        def _detect_obfuscated_emails() -> list[DetectedPII]:
            emails = []

            for email in re.finditer(self.obf_pattern, text):
                raw_email = email.group(0)

                local = email.group("local")
                domain = email.group("domain")
                tld = email.group("tld")

                local = re.sub(_OBFUSCATED_DOT, ".", local, flags=re.IGNORECASE)
                local = re.sub(r"\s+", "", local)
                domain = re.sub(_OBFUSCATED_DOT, ".", domain, flags=re.IGNORECASE)
                domain = re.sub(r"\s+", "", domain)

                norm_email = f"{local}@{domain}.{tld}".lower()

                emails.append(
                    DetectedPII(
                        type="email",
                        value=raw_email,
                        normalized_value=norm_email,
                        start_idx=email.start(),
                        end_idx=email.end(),
                        confidence=0.75,
                        source="regex.email_obfuscated"
                    )
                )

            return emails

        entities = []
        entities.extend(_detect_standard_emails())
        entities.extend(_detect_obfuscated_emails())

        return entities

