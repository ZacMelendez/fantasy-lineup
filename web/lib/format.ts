import type { Confidence } from "./types";

export const points = (value: number | null | undefined, digits = 1) =>
  value === null || value === undefined ? "—" : value.toFixed(digits);

export const signed = (value: number, digits = 1) =>
  `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;

export const percent = (value: number | null | undefined, digits = 0) =>
  value === null || value === undefined ? "—" : `${(value * 100).toFixed(digits)}%`;

export const record = (team: { wins: number; losses: number; ties: number }) =>
  team.ties > 0
    ? `${team.wins}-${team.losses}-${team.ties}`
    : `${team.wins}-${team.losses}`;

export const relativeDate = (epochMillis: number | null) => {
  if (!epochMillis) return "";
  return new Date(epochMillis).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
};

export const confidenceClass: Record<Confidence, string> = {
  high: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  medium: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
  low: "bg-slate-500/15 text-slate-300 ring-slate-500/30",
};

const INJURY_LABELS: Record<string, string> = {
  OUT: "OUT",
  INJURY_RESERVE: "IR",
  SUSPENSION: "SUSP",
  NOT_ACTIVE: "OUT",
  QUESTIONABLE: "Q",
  DOUBTFUL: "D",
  DAY_TO_DAY: "DTD",
};

/** Short badge text for an injury designation, or null when healthy. */
export const injuryLabel = (status: string) =>
  status && status !== "ACTIVE" && status !== "NORMAL"
    ? (INJURY_LABELS[status] ?? status.slice(0, 4))
    : null;

export const isSeriousInjury = (status: string) =>
  ["OUT", "INJURY_RESERVE", "SUSPENSION", "NOT_ACTIVE"].includes(status);
