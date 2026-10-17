# Fantasy Lineup

A self-hosted dashboard for an ESPN fantasy football league. Reads your league through
[cwendt94/espn-api](https://github.com/cwendt94/espn-api) and computes optimal lineups,
trade targets, and waiver pickups.

Two containers:

- `api` — FastAPI service wrapping `espn_api`, plus the optimization engine
- `web` — Next.js dashboard

## Screenshots

<!-- Add images to docs/screenshots/ and uncomment:
![Home](docs/screenshots/home.png)
![Optimal lineup](docs/screenshots/lineup.png)
![Trade finder](docs/screenshots/trades.png)
-->

## Tech stack

| Area | Tools |
| --- | --- |
| API | Python, FastAPI, uvicorn, [espn-api](https://github.com/cwendt94/espn-api) |
| Optimization | NumPy, SciPy (`linear_sum_assignment`) |
| AI layer (optional) | OpenAI or Anthropic, via `httpx` |
| Web | Next.js (App Router), React, TypeScript, Tailwind CSS |
| Infra | Docker Compose (two containers, internal network) |
| Tests | pytest |

## Setup

1. Copy the env template and fill it in:

   ```sh
   cp .env.example .env
   ```

2. `ESPN_LEAGUE_ID` and `ESPN_TEAM_ID` come from your league URL. When you view your own
   team, the URL looks like:

   ```
   https://fantasy.espn.com/football/team?leagueId=123456&teamId=4
   ```

3. If your league is private, you also need two cookies. In a browser logged into
   ESPN, open devtools on <https://fantasy.espn.com>, go to
   **Application → Storage → Cookies → https://fantasy.espn.com**, and copy:

   - `espn_s2` → `ESPN_S2` (a long URL-encoded string)
   - `SWID` → `ESPN_SWID` (a GUID including the curly braces, e.g. `{ABC-123-...}`)

   Public leagues work without these.

4. Start it:

   ```sh
   docker compose up --build
   ```

   Then open <http://localhost:3000>.

## Development

For hot reload on both services:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

The API is reachable directly at <http://localhost:8000> in dev mode, with interactive
docs at <http://localhost:8000/docs>.

## Pages

| Page        | What it shows                                                        |
| ----------- | -------------------------------------------------------------------- |
| `/`         | Record, this week's projection vs. opponent, win probability, actions |
| `/lineup`   | Current vs. optimal lineup with per-swap point deltas                |
| `/matchups` | Every box score for the week, with full lineups                      |
| `/league`   | Standings, power rankings, recent activity                           |
| `/trades`   | Mutually beneficial trade packages, ranked                           |
| `/waivers`  | Free agent targets by value over replacement                         |

## How the recommendations work

Everything is computed from ESPN's own projections — no external projection source.

**Optimal lineup.** Each player's `eligibleSlots` is matched against the league's
`position_slot_counts` to build a players-by-slots value matrix, then solved as a
maximum-weight assignment problem (`scipy.optimize.linear_sum_assignment`). Comparing
the optimal assignment to your actual lineup gives the sit/start list.

**Value over replacement.** Replacement level for a position is the projection of the
best freely available player at that position. A player's value is their projection
minus that baseline, so a mid-tier RB in a shallow pool outranks a similar-scoring WR in
a deep one.

**Trades.** For each opposing team, 1-for-1 and 2-for-2 packages are enumerated and
each side is scored by the change in its *optimal lineup total*, not by raw player
value. Only trades where both sides gain are kept, ranked by your own surplus.

**Win probability.** Normal distribution over the projected margin, using a fixed
weekly standard deviation (`WEEKLY_STDEV` in `api/engine/lineup.py`).

The optional AI layer (`POST /advice`) receives this computed output as context and
writes a narrative read on the close calls. It never changes the numbers, and the UI
hides the panel entirely when no API key is configured.

## Tests

```sh
cd api
pip install -r requirements-dev.txt
pytest
```
