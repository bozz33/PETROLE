/** Client HTTP centralisé avec authentification et renouvellement de session. */

export interface ApiProblem {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  code?: string;
  context?: Record<string, unknown>;
}

export interface SessionTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ApiProblem;

  constructor(status: number, problem: ApiProblem) {
    super(problem.detail ?? problem.title ?? "Erreur HTTP " + status);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const SESSION_KEY = "hydro.session";
const SESSION_ENDED_EVENT = "hydro:session-ended";

let refreshInProgress: Promise<SessionTokens | null> | null = null;

export function readSession(): SessionTokens | null {
  try {
    const raw = window.sessionStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as SessionTokens) : null;
  } catch {
    return null;
  }
}

export function storeSession(tokens: SessionTokens): void {
  window.sessionStorage.setItem(
    SESSION_KEY,
    JSON.stringify({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      expires_in: tokens.expires_in,
    }),
  );
}

export function clearSession(): void {
  window.sessionStorage.removeItem(SESSION_KEY);
}

function notifySessionEnded(): void {
  clearSession();
  window.dispatchEvent(new Event(SESSION_ENDED_EVENT));
}

export function listenForSessionEnd(listener: () => void): () => void {
  window.addEventListener(SESSION_ENDED_EVENT, listener);
  return () => window.removeEventListener(SESSION_ENDED_EVENT, listener);
}

async function problemFromResponse(response: Response): Promise<ApiProblem> {
  try {
    return (await response.json()) as ApiProblem;
  } catch {
    return { detail: "Le serveur a répondu avec le statut " + response.status + "." };
  }
}

async function renewSession(): Promise<SessionTokens | null> {
  const current = readSession();
  if (!current) {
    return null;
  }
  const response = await fetch(API_BASE + "/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: current.refresh_token }),
  });
  if (!response.ok) {
    notifySessionEnded();
    return null;
  }
  const tokens = (await response.json()) as SessionTokens;
  storeSession(tokens);
  return tokens;
}

async function activeRenewal(): Promise<SessionTokens | null> {
  if (!refreshInProgress) {
    refreshInProgress = renewSession().finally(() => {
      refreshInProgress = null;
    });
  }
  return refreshInProgress;
}

async function executeRequest(
  path: string,
  init: RequestInit,
  accessToken: string | null,
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) {
    headers.set("Authorization", "Bearer " + accessToken);
  }
  return fetch(API_BASE + path, { ...init, headers });
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const initialSession = readSession();
  let response = await executeRequest(path, init, initialSession?.access_token ?? null);

  const canRenew =
    response.status === 401 &&
    Boolean(initialSession?.refresh_token) &&
    path !== "/auth/login" &&
    path !== "/auth/bootstrap" &&
    path !== "/auth/refresh";

  if (canRenew) {
    const renewed = await activeRenewal();
    if (renewed) {
      response = await executeRequest(path, init, renewed.access_token);
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, await problemFromResponse(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function downloadApiFile(path: string, filename: string): Promise<void> {
  const session = readSession();
  let response = await executeRequest(path, {}, session?.access_token ?? null);
  if (response.status === 401 && session?.refresh_token) {
    const renewed = await activeRenewal();
    if (renewed) {
      response = await executeRequest(path, {}, renewed.access_token);
    }
  }
  if (!response.ok) {
    throw new ApiError(response.status, await problemFromResponse(response));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function jsonBody(value: unknown): string {
  return JSON.stringify(value);
}
