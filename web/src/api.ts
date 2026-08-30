import type { DemoConfig, FixRequest, ScanRequest, ScanResult } from "./types";

// Vite dev proxy rewrites /api -> the FastAPI backend (see vite.config.ts).
const BASE = "/api";

// Pre-fill data for the form. `service_urls` is populated only when the
// launcher (run.sh / run.ps1) started a tunnel to the local auth lab;
// otherwise it comes back empty and the form starts blank.
export async function getDemoConfig(): Promise<DemoConfig> {
  const res = await fetch(`${BASE}/demo-config`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

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
