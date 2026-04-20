/**
 * Tiny typed client for the FastAPI approval-UI backend.
 *
 * Paths are always relative — dev uses the `rewrites()` in
 * next.config.ts to proxy /api/* to :8787, and in production the Next
 * export is served from the same origin as FastAPI so /api/* works
 * unchanged.
 */

export type PlanStatus =
  | "PENDING"
  | "APPLIED"
  | "REJECTED"
  | "FAILED"
  | "DRY_RUN_SUCCESS";

export interface Plan {
  plan_id: string;
  operation: string;
  entity_type: string;
  entity_id: string;
  customer_id: string;
  changes: Record<string, unknown>;
  requires_double_confirm: boolean;
  dry_run_result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  status: PlanStatus;
  result: Record<string, unknown> | null;
  error: string;
}

export interface ListPlansResponse {
  plans: Plan[];
  count: number;
}

export interface Account {
  customer_id: string;
  descriptive_name?: string;
  currency_code?: string;
  time_zone?: string;
  [key: string]: unknown;
}

export interface AccountsResponse {
  accounts: Account[];
  [key: string]: unknown;
}

export interface HealthResponse {
  status: string;
  require_dry_run: boolean;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { query?: Record<string, string | undefined> },
): Promise<T> {
  const { query, ...rest } = init ?? {};
  let url = path;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== "") params.set(k, v);
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }
  const res = await fetch(url, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(rest.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body;
    } catch {
      // keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  // 204 / empty body
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),

  listPlans: (opts: {
    status?: PlanStatus;
    customer_id?: string;
    limit?: number;
  } = {}) =>
    request<ListPlansResponse>("/api/plans", {
      query: {
        status: opts.status,
        customer_id: opts.customer_id,
        limit: opts.limit?.toString(),
      },
    }),

  getPlan: (id: string) => request<Plan>(`/api/plans/${encodeURIComponent(id)}`),

  approvePlan: (id: string) =>
    request<Record<string, unknown>>(
      `/api/plans/${encodeURIComponent(id)}/approve`,
      { method: "POST" },
    ),

  rejectPlan: (id: string) =>
    request<{ status: string; plan: Plan }>(
      `/api/plans/${encodeURIComponent(id)}/reject`,
      { method: "POST" },
    ),

  listAccounts: () => request<AccountsResponse>("/api/accounts"),
};

export function formatRelativeTime(iso: string): string {
  const d = new Date(iso);
  const now = Date.now();
  const diff = Math.round((now - d.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
