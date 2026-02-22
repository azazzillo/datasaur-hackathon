import re

ICD_RE = re.compile(r"\b([A-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?)\b")

def extract_icd_codes(text: str) -> list[str]:
    # можно дополнительно фильтровать: убирать мусор, оставлять уникальные
    codes = ICD_RE.findall(text.upper())
    # уникальные с сохранением порядка
    seen = set()
    out = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out