from src.llm.gpt_oss import ask_llm
from src.utils.json_parse import safe_json_loads
from src.core.prompts import SYSTEM_PROMPT
from src.utils.icd_extract import extract_icd_codes


def _dedup_keep_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def diagnose_symptoms(symptoms: str, retriever, top_k: int, icd_limit: int, chunk_limit: int) -> dict:
    # 1) retrieval
    hits = retriever.search(symptoms, k=top_k)
    if not hits:
        return {"diagnoses": []}

    # 2) extract candidate ICD from TEXT (не из icd_codes поля!)
    candidates: list[str] = []
    for h in hits:
        candidates.extend(extract_icd_codes(h["chunk_text"]))
        if len(candidates) >= icd_limit:
            break
    candidates = _dedup_keep_order(candidates)[:icd_limit]

    # если кандидатов мало — увеличим поиск контекста (чуть шире)
    if len(candidates) < 3:
        hits_more = retriever.search(symptoms, k=max(top_k, 20))
        more = []
        for h in hits_more:
            more.extend(extract_icd_codes(h["chunk_text"]))
            if len(more) >= 25:
                break
        more = _dedup_keep_order(more)
        # добьём candidates
        for c in more:
            if c not in candidates:
                candidates.append(c)
            if len(candidates) >= icd_limit:
                break

    # если всё равно пусто — тогда вообще нечего ранжировать
    if not candidates:
        return {"diagnoses": []}

    # 3) build compact context (важно для latency)
    context = "\n\n".join(
        f"[{h['protocol_id']}] {h['title']}\n{h['chunk_text'][:chunk_limit]}"
        for h in hits[:3]
    )

    # 4) hard constraint: choose only from candidates
    user_prompt = (
        f"СИМПТОМЫ:\n{symptoms}\n\n"
        f"КОНТЕКСТ ПРОТОКОЛОВ:\n{context}\n\n"
        f"ВЫБОР ICD-10 ТОЛЬКО ИЗ СПИСКА:\n{', '.join(candidates)}\n\n"
        "Верни РОВНО 3 объекта в diagnoses. "
        "icd10_code каждого диагноза ДОЛЖЕН быть строго из списка выше. "
        "Никаких других ICD. "
        "Ответ: СТРОГО валидный JSON, без markdown."
    )

    raw = ask_llm(SYSTEM_PROMPT, user_prompt)
    if not raw or not raw.strip():
        return {"diagnoses": []}

    try:
        parsed = safe_json_loads(raw)
    except Exception:
        parsed = {}

    diags = []
    if isinstance(parsed, dict):
        diags = parsed.get("diagnoses") or []

    # 5) normalize output: keep only allowed codes, fill gaps deterministically
    final = []
    used = set()

    for d in diags:
        code = str(d.get("icd10_code", "")).strip()
        if code in candidates and code not in used:
            used.add(code)
            final.append({
                "rank": len(final) + 1,
                "diagnosis": str(d.get("diagnosis", ""))[:120],
                "icd10_code": code,
                "explanation": str(d.get("explanation", ""))[:260],  # коротко = быстрее
            })
        if len(final) == 3:
            break

    # добиваем до 3: просто берём первые кандидаты
    if len(final) < 3:
        for code in candidates:
            if code not in used:
                used.add(code)
                final.append({
                    "rank": len(final) + 1,
                    "diagnosis": "",
                    "icd10_code": code,
                    "explanation": "",
                })
            if len(final) == 3:
                break

    return {"diagnoses": final}