import json
import re
from typing import Any


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text.strip()).strip()


def _normalize_quotes(s: str) -> str:
    # smart quotes → normal quotes
    return (
        s.replace("“", '"')
         .replace("”", '"')
         .replace("„", '"')
         .replace("«", '"')
         .replace("»", '"')
         .replace("’", "'")
         .replace("‘", "'")
    )


def _remove_trailing_commas(s: str) -> str:
    # { "a": 1, } or [1,2,]
    return re.sub(r",\s*([}\]])", r"\1", s)


def _extract_first_json_object(s: str) -> str:
    """
    Достаём первый {...} блок даже если до/после есть мусор.
    """
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object found in LLM response")

    # грубый, но рабочий способ: идём по символам и считаем баланс скобок
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]

    # если не нашли закрытие — вернём до конца (потом попробуем repair)
    return s[start:]


def _repair_truncated_json(s: str) -> str:
    s = s.strip()

    # если оборвалось внутри строки — закроем кавычку
    if s.count('"') % 2 == 1:
        s += '"'

    # закроем скобки по балансу
    open_curly = s.count("{")
    close_curly = s.count("}")
    open_square = s.count("[")
    close_square = s.count("]")

    s += "]" * max(0, open_square - close_square)
    s += "}" * max(0, open_curly - close_curly)
    return s


def _regex_fallback_diagnoses(text: str) -> dict:
    """
    Последний шанс: вытащить хотя бы rank/diagnosis/icd10_code/explanation из текста,
    чтобы сервис не падал (и evaluate.py мог работать).
    """
    # очень терпимый парсер: ищем куски вида "rank": N ... "icd10_code": "..."
    blocks = re.findall(r"\{[^{}]*\"icd10_code\"\s*:\s*\"[^\"]+\"[^{}]*\}", text, flags=re.S)
    diags = []
    for b in blocks[:3]:
        b = _normalize_quotes(b)
        b = _remove_trailing_commas(b)
        try:
            obj = json.loads(b)
            diags.append({
                "rank": int(obj.get("rank", len(diags) + 1)),
                "diagnosis": str(obj.get("diagnosis", "")),
                "icd10_code": str(obj.get("icd10_code", "")),
                "explanation": str(obj.get("explanation", "")),
            })
        except Exception:
            continue

    # если вообще ничего не нашли — пустой
    return {"diagnoses": sorted(diags, key=lambda x: x["rank"])}


def _extract_diagnoses_array(text: str) -> str | None:
    """
    Пытаемся вытащить именно массив diagnoses: [ ... ]
    даже если весь объект кривой.
    """
    m = re.search(r'"diagnoses"\s*:\s*\[', text)
    if not m:
        return None

    start = m.end()  # позиция после '['
    depth = 1
    in_str = False
    esc = False

    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return text[m.start(): i + 1]  # "diagnoses": [...]

    return None

def safe_json_loads(text: str) -> Any:
    t = _strip_fences(text)
    t = _normalize_quotes(t)

    # 0) сначала попробуем нормально распарсить целый JSON объект
    candidate = _extract_first_json_object(t)
    candidate = _remove_trailing_commas(candidate)

    try:
        return json.loads(candidate)
    except Exception:
        pass

    # 1) попробуем repair обрезанного
    repaired = _repair_truncated_json(candidate)
    repaired = _remove_trailing_commas(repaired)
    try:
        return json.loads(repaired)
    except Exception:
        pass

    # 2) попробуем вытащить только diagnoses array и обернуть в объект
    diag_part = _extract_diagnoses_array(t)
    if diag_part:
        diag_part = _remove_trailing_commas(diag_part)
        try:
            # превращаем '"diagnoses": [...]' → '{"diagnoses":[...]}'
            return json.loads("{" + diag_part + "}")
        except Exception:
            pass

    # 3) regex fallback по объектам
    return _regex_fallback_diagnoses(t)