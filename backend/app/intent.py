import json
import os
import re

import httpx

PROMPT = (
    "Extract a shopping intent from the user's sentence. Reply with JSON only: "
    '{"query": <short product search query>, "maxPrice": <number in USD or null>}.'
)


def regex_parse(text: str) -> dict:
    m = re.search(r"(?:under|below|less than|max(?:imum)?|up to|<)\s*\$?\s*(\d+(?:\.\d+)?)", text, re.I) or re.search(
        r"\$\s*(\d+(?:\.\d+)?)", text
    )
    max_price = float(m.group(1)) if m else None
    query = text
    if m:
        query = text[: m.start()] + text[m.end():]
    query = re.sub(r"^\s*(please\s+)?(buy|get|find|order|purchase)(\s+me)?\s+", "", query, flags=re.I)
    query = re.sub(r"\b(for|,|and)\s*$", "", query.strip(" ,.")).strip(" ,.")
    return {"query": query or text, "maxPrice": max_price}


async def _llm(text: str, key: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        if key.startswith("sk-ant-"):
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={
                    "model": os.environ.get("LLM_MODEL", "claude-3-5-haiku-latest"),
                    "max_tokens": 200,
                    "system": PROMPT,
                    "messages": [{"role": "user", "content": text}],
                },
            )
            r.raise_for_status()
            out = r.json()["content"][0]["text"]
        else:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": text}],
                },
            )
            r.raise_for_status()
            out = r.json()["choices"][0]["message"]["content"]
    data = json.loads(out[out.find("{"): out.rfind("}") + 1])
    mp = data.get("maxPrice")
    return {"query": str(data["query"]), "maxPrice": float(mp) if mp is not None else None}


async def parse_intent(text: str) -> dict:
    key = os.environ.get("LLM_API_KEY")
    if key:
        try:
            return {**await _llm(text, key), "parser": "llm"}
        except Exception as e:  # noqa: BLE001
            print(f"LLM parse failed, falling back to regex: {e!r}")
    return {**regex_parse(text), "parser": "regex"}
