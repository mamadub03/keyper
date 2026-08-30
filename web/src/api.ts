import type { FixRequest, ScanRequest, ScanResult } from "./types";

// Vite dev proxy rewrites /api -> the FastAPI backend (see vite.config.ts).
const BASE = "/api";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json();
}

export function scanService(request: ScanRequest): Promise<ScanResult> {
  return postJson<ScanResult>("/scan", request);
}

export function fixService(request: FixRequest): Promise<ScanResult> {
  return postJson<ScanResult>("/fix", request);
}
