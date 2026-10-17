import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# config.load_config() refuses to run without a league id. Tests never reach ESPN,
# so any value works, but it must be set before the app module is imported.
os.environ.setdefault("ESPN_LEAGUE_ID", "424242")
os.environ.setdefault("ESPN_YEAR", "2026")
os.environ.setdefault("ESPN_TEAM_ID", "1")
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
