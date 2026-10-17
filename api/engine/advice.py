"""Optional AI narrative layer.

Takes the already-computed deterministic output as context and asks a model to talk
through the close calls. It never produces numbers of its own, and the whole feature
is inert when no API key is configured.
"""

import json
from typing import Any

import httpx

from config import Config

SYSTEM_PROMPT = """You are a fantasy football analyst advising one manager.

You will receive JSON containing that manager's roster, their current week matchup, an
optimal-lineup analysis, ranked trade proposals, and waiver targets. Every number in it
was computed from ESPN's own projections.

Rules:
- Never invent statistics, injuries, or projections. Use only what is in the JSON.
- Lead with the single most consequential decision this week.
- Call out where the numbers are close enough that the recommendation is weak.
- Be concise and concrete. No preamble, no restating the data back.
- Write plain prose in markdown. At most four short paragraphs.
"""

TIMEOUT = httpx.Timeout(60.0)


def generate_advice(cfg: Config, context: dict[str, Any]) -> dict:
    if not cfg.ai_enabled:
        return {
            "enabled": False,
            "narrative": None,
            "detail": "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable AI commentary.",
        }

    payload = json.dumps(_trim(context), default=str)

    try:
        if cfg.openai_api_key:
            narrative = _call_openai(cfg, payload)
        else:
            narrative = _call_anthropic(cfg, payload)
    except httpx.HTTPStatusError as exc:
        return {
            "enabled": True,
            "narrative": None,
            "detail": f"Model request failed with {exc.response.status_code}.",
        }
    except httpx.HTTPError as exc:
        return {"enabled": True, "narrative": None, "detail": f"Model request failed: {exc}"}

    return {"enabled": True, "narrative": narrative, "detail": None}


def _call_openai(cfg: Config, payload: str) -> str:
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {cfg.openai_api_key}"},
            json={
                "model": cfg.llm_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": payload},
                ],
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


def _call_anthropic(cfg: Config, payload: str) -> str:
    model = cfg.llm_model if "claude" in cfg.llm_model else "claude-sonnet-4-20250514"
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": cfg.anthropic_api_key or "",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": payload}],
            },
        )
        response.raise_for_status()
        return "".join(
            block.get("text", "") for block in response.json().get("content", [])
        ).strip()


def _trim(context: dict[str, Any]) -> dict[str, Any]:
    """Keep the prompt small: only the fields that inform a recommendation."""
    lineup = context.get("lineup") or {}
    return {
        "week": context.get("week"),
        "team": context.get("team"),
        "record": context.get("record"),
        "matchup": context.get("matchup"),
        "winProbability": context.get("winProbability"),
        "lineup": {
            "currentProjected": lineup.get("currentProjected"),
            "optimalProjected": lineup.get("optimalProjected"),
            "pointsLeftOnBench": lineup.get("pointsLeftOnBench"),
            "swaps": lineup.get("swaps"),
            "starters": [
                {k: p.get(k) for k in ("name", "position", "slot", "effectiveProjection", "injuryStatus", "proOpponent")}
                for p in (lineup.get("currentLineup") or [])
            ],
            "bench": [
                {k: p.get(k) for k in ("name", "position", "effectiveProjection", "injuryStatus", "onByeWeek")}
                for p in (lineup.get("bench") or [])
            ],
        },
        "trades": (context.get("trades") or [])[:5],
        "waivers": (context.get("waivers") or [])[:5],
    }
