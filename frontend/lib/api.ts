const API_BASE = "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new ApiError(`API error: ${res.status}`, res.status);
  return res.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(`API error: ${res.status}`, res.status);
  return res.json();
}

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function initialApiState<T>(): ApiState<T> {
  return { data: null, loading: true, error: null };
}

export function useFetchState<T>() {
  return {
    idle: () => ({ data: null as T | null, loading: true, error: null }),
    success: (data: T) => ({ data, loading: false, error: null }),
    failure: (error: string) => ({ data: null as T | null, loading: false, error }),
  };
}
