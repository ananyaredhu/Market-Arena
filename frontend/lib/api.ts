const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Turn an error response into a readable message: the server's own reason (FastAPI "detail") when it sent one. */
async function failure(res: Response, init: RequestInit | undefined, path: string): Promise<Error> {
  let detail: string | null = null;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
    else if (Array.isArray(body?.detail)) detail = body.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ");
  } catch {
    // not JSON: fall through to the generic message
  }
  return new Error(detail ?? `${init?.method ?? "GET"} ${path} failed: ${res.status}`);
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) throw await failure(res, init, path);
  return res.json() as Promise<T>;
}

export const post = <T,>(path: string, body?: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export const del = <T,>(path: string) => api<T>(path, { method: "DELETE" });
