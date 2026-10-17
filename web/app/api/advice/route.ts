import { NextResponse } from "next/server";

const BASE = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const week = new URL(request.url).searchParams.get("week");
  const query = week ? `?week=${week}` : "";

  try {
    const response = await fetch(`${BASE}/advice${query}`, {
      method: "POST",
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json(
      { enabled: true, narrative: null, detail: "Cannot reach the API." },
      { status: 503 },
    );
  }
}
