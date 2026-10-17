import os
from dataclasses import dataclass


def _clean(value: str | None) -> str | None:
    """ESPN cookies are often pasted with surrounding quotes or whitespace."""
    if value is None:
        return None
    value = value.strip().strip('"').strip("'")
    return value or None


@dataclass(frozen=True)
class Config:
    league_id: int
    year: int
    team_id: int
    espn_s2: str | None
    swid: str | None
    cache_ttl: int
    openai_api_key: str | None
    anthropic_api_key: str | None
    llm_model: str

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key or self.anthropic_api_key)


def load_config() -> Config:
    league_id = _clean(os.environ.get("ESPN_LEAGUE_ID"))
    if not league_id:
        raise RuntimeError("ESPN_LEAGUE_ID is not set. Copy .env.example to .env and fill it in.")

    return Config(
        league_id=int(league_id),
        year=int(_clean(os.environ.get("ESPN_YEAR")) or 2026),
        team_id=int(_clean(os.environ.get("ESPN_TEAM_ID")) or 1),
        espn_s2=_clean(os.environ.get("ESPN_S2")),
        swid=_clean(os.environ.get("ESPN_SWID")),
        cache_ttl=int(_clean(os.environ.get("CACHE_TTL_SECONDS")) or 300),
        openai_api_key=_clean(os.environ.get("OPENAI_API_KEY")),
        anthropic_api_key=_clean(os.environ.get("ANTHROPIC_API_KEY")),
        llm_model=_clean(os.environ.get("LLM_MODEL")) or "gpt-4o-mini",
    )
