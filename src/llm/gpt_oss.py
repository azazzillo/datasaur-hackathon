import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("LLM_HOST") or os.getenv("llm_host")
key = os.getenv("LLM_KEY") or os.getenv("llm_key")
model = os.getenv("LLM_MODEL") or os.getenv("llm_model") or "oss-120b"

if not host or not key:
    raise RuntimeError("LLM_HOST or LLM_KEY not set in environment (.env)")

client = OpenAI(
    base_url=host,
    api_key=key,
)


def ask_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Единственная функция вызова LLM.
    Быстрая, детерминированная, без логов.
    """
    response = client.chat.completions.create(
        model=model,         
        temperature=0.0,      
        max_tokens=450,       
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content or ""