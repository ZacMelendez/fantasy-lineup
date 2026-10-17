import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

// The browser cannot reach the API directly on the compose network, so the refresh
// button posts here and this handler forwards it, then drops the Next data cache so
// the next render pulls the new numbers.
const BASE = process.env.INTERNAL_API_URL ?? "http://localhost:8000";

export async function POST() {
  try {
    const response = await fetch(`${BASE}/refresh`, {
      method: "POST",
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: `API returned ${response.status}` },
        { status: 502 },
      );
    }

    revalidatePath("/", "layout");
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Cannot reach the API" }, { status: 503 });
  }
}
