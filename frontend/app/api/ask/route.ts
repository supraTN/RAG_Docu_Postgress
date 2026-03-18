import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const API_KEY = process.env.API_KEY ?? "";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const backendRes = await fetch(`${BACKEND_URL}/ask/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY && { "X-API-Key": API_KEY }),
    },
    body: JSON.stringify(body),
  });

  if (!backendRes.ok) {
    return NextResponse.json(
      { error: "Backend error" },
      { status: backendRes.status }
    );
  }

  return new Response(backendRes.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
