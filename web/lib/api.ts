import type {
  Activity,
  Advice,
  Dashboard,
  League,
  MatchupContext,
  Matchup,
  TeamDetail,
  Trades,
  Waivers,
} from "./types";

// Inside Docker the API is reachable on the compose network; running the web app
// directly on a host falls back to localhost.
const BASE = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
  }
}

type Options = {
  // ESPN data changes slowly and the API caches it already; a short revalidate
  // window keeps navigation snappy without serving stale scores.
  revalidate?: number;
  method?: "GET" | "POST";
};

async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { revalidate = 60, method = "GET" } = options;

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { method, next: { revalidate } });
  } catch (cause) {
    throw new ApiError(
      503,
      `Cannot reach the API at ${BASE}. Is the api container running?`,
    );
  }

  if (!response.ok) {
    const body = await response.text();
    let detail = body;
    try {
      detail = (JSON.parse(body) as { detail?: string }).detail ?? body;
    } catch {
      // Non-JSON error body; use it as-is.
    }
    throw new ApiError(response.status, detail || response.statusText);
  }

  return response.json() as Promise<T>;
}

const weekQuery = (week?: number) => (week ? `?week=${week}` : "");

export const api = {
  league: () => request<League>("/league"),
  dashboard: (week?: number) => request<Dashboard>(`/dashboard${weekQuery(week)}`),
  optimize: (teamId?: number, week?: number) => {
    const params = new URLSearchParams();
    if (teamId) params.set("team_id", String(teamId));
    if (week) params.set("week", String(week));
    const query = params.toString();
    return request<MatchupContext>(`/optimize${query ? `?${query}` : ""}`);
  },
  matchups: (week?: number) =>
    request<{ week: number; matchups: Matchup[] }>(`/matchups${weekQuery(week)}`),
  team: (teamId: number) => request<TeamDetail>(`/team/${teamId}`),
  waivers: (limit = 15) => request<Waivers>(`/waivers?limit=${limit}`),
  trades: (limit = 12) => request<Trades>(`/trades?limit=${limit}`),
  activity: (size = 25) => request<Activity[]>(`/activity?size=${size}`),
  advice: (week?: number) =>
    request<Advice>(`/advice${weekQuery(week)}`, { method: "POST", revalidate: 0 }),
};
