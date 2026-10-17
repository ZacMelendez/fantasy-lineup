export type Player = {
  playerId: number;
  name: string;
  position: string;
  proTeam: string;
  eligibleSlots: string[];
  lineupSlot: string;
  injuryStatus: string;
  injured: boolean;
  positionRank: number | null;
  percentOwned: number;
  percentStarted: number;
  totalPoints: number;
  avgPoints: number;
  projectedAvgPoints: number;
  projectedTotalPoints: number;
  seasonProjection: number;
};

export type BoxPlayer = Player & {
  slot: string;
  started: boolean;
  points: number;
  projectedPoints: number;
  effectiveProjection: number;
  proOpponent: string | null;
  proPositionRank: number | null;
  onByeWeek: boolean;
  gamePlayed: number;
  slotProjection?: number;
};

export type ValuedPlayer = Player & {
  replacementLevel: number;
  valueOverReplacement: number;
};

export type TeamSummary = {
  teamId: number;
  name: string;
  abbrev: string;
  logo: string | null;
  owners: string[];
  wins: number;
  losses: number;
  ties: number;
  pointsFor: number;
  pointsAgainst: number;
  standing: number | null;
  divisionName: string | null;
  streakType: string | null;
  streakLength: number;
  playoffPct: number;
};

export type Swap = {
  start: BoxPlayer;
  sit: BoxPlayer;
  gain: number;
  confidence: Confidence;
  reason: string;
};

export type Confidence = "high" | "medium" | "low";

export type LineupAnalysis = {
  currentProjected: number;
  optimalProjected: number;
  pointsLeftOnBench: number;
  isOptimal: boolean;
  optimalLineup: BoxPlayer[];
  currentLineup: BoxPlayer[];
  bench: BoxPlayer[];
  swaps: Swap[];
};

export type MatchupContext = {
  week: number;
  team: TeamSummary;
  score?: number;
  lineup: LineupAnalysis | null;
  opponent:
    | (TeamSummary & {
        score: number;
        projected: number;
        optimalProjected: number;
        lineup: BoxPlayer[];
        bench: BoxPlayer[];
      })
    | null;
  winProbability: number | null;
  winProbabilityIfOptimal?: number | null;
  note?: string;
};

export type ActionItem = {
  kind: "lineup" | "waiver" | "trade";
  headline: string;
  impact: number;
  unit: string;
  confidence: Confidence;
  detail: string;
};

export type WaiverTarget = ValuedPlayer & {
  lineupGain: number;
  dropCandidate: ValuedPlayer | null;
  reason: string;
};

export type TradeProposal = {
  withTeamId: number;
  withTeamName: string;
  give: ValuedPlayer[];
  get: ValuedPlayer[];
  myGain: number;
  theirGain: number;
  fairness: "favors you" | "favors them" | "even";
  confidence: Confidence;
  reason: string;
};

export type Dashboard = MatchupContext & {
  aiEnabled: boolean;
  topWaivers: WaiverTarget[];
  topTrades: TradeProposal[];
  actions: ActionItem[];
};

export type League = {
  leagueId: number;
  year: number;
  myTeamId: number;
  currentWeek: number;
  nflWeek: number | null;
  slotCounts: Record<string, number>;
  scoringFormat: { abbr: string; label: string; points: number }[];
  teams: TeamSummary[];
  standings: TeamSummary[];
  powerRankings: { score: number; team: TeamSummary }[];
};

export type MatchupSide = TeamSummary & {
  score: number;
  projectedScore: number;
  lineup: BoxPlayer[];
};

export type Matchup = {
  week: number;
  isPlayoff: boolean;
  matchupType: string;
  home: MatchupSide | null;
  away: MatchupSide | null;
};

export type TeamDetail = TeamSummary & {
  roster: Player[];
  valuedRoster: ValuedPlayer[];
};

export type Waivers = {
  teamId: number;
  replacementLevels: Record<string, number>;
  baselineLineupValue: number;
  targets: WaiverTarget[];
};

export type Trades = {
  teamId: number;
  baselineLineupValue: number;
  candidatesConsidered: number;
  proposals: TradeProposal[];
};

export type Activity = {
  date: number | null;
  actions: {
    team: string | null;
    teamId: number | null;
    action: string | null;
    player: string | null;
    bidAmount: number | null;
  }[];
};

export type Advice = {
  enabled: boolean;
  narrative: string | null;
  detail: string | null;
};
