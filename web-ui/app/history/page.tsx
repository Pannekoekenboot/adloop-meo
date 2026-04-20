"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Plan, type PlanStatus } from "@/lib/api";
import { PlanCard } from "@/components/PlanCard";
import { useShell } from "@/components/ClientShell";
import { cn } from "@/lib/cn";

const FILTERS: Array<{ label: string; value: PlanStatus | "ALL" }> = [
  { label: "All", value: "ALL" },
  { label: "Applied", value: "APPLIED" },
  { label: "Rejected", value: "REJECTED" },
  { label: "Failed", value: "FAILED" },
  { label: "Dry run", value: "DRY_RUN_SUCCESS" },
];

export default function HistoryPage() {
  const { customerId } = useShell();
  const [filter, setFilter] = useState<PlanStatus | "ALL">("ALL");
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setPlans(null);
    setError(null);
    const loader =
      filter === "ALL"
        ? api.listPlans({ customer_id: customerId || undefined, limit: 500 })
        : api.listPlans({
            status: filter,
            customer_id: customerId || undefined,
            limit: 500,
          });
    loader
      .then((r) =>
        setPlans(
          filter === "ALL"
            ? r.plans.filter((p) => p.status !== "PENDING")
            : r.plans,
        ),
      )
      .catch((e: Error) => setError(e.message));
  }, [filter, customerId]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(reload, [reload]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">History</h1>
        <p className="text-sm text-[var(--muted)]">
          Everything that was applied, rejected, or failed.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              filter === f.value
                ? "border-[var(--foreground)] bg-[var(--foreground)] text-[var(--background)]"
                : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
          Failed to load plans: {error}
        </div>
      ) : plans === null ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : plans.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[var(--border)] p-12 text-center text-sm text-[var(--muted)]">
          No plans match this filter.
        </div>
      ) : (
        <ul className="space-y-3">
          {plans.map((p) => (
            <li key={p.plan_id}>
              <PlanCard plan={p} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
