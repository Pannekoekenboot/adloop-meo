"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Plan } from "@/lib/api";
import { PlanCard } from "@/components/PlanCard";
import { useShell } from "@/components/ClientShell";

export default function QueuePage() {
  const { customerId } = useShell();
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setPlans(null);
    setError(null);
    api
      .listPlans({ status: "PENDING", customer_id: customerId || undefined })
      .then((r) => setPlans(r.plans))
      .catch((e: Error) => setError(e.message));
  }, [customerId]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(reload, [reload]);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Pending approvals
          </h1>
          <p className="text-sm text-[var(--muted)]">
            Plans drafted via Claude, waiting for a human to apply or reject.
          </p>
        </div>
        <button
          onClick={reload}
          className="text-sm text-[var(--muted)] hover:text-[var(--foreground)]"
        >
          Refresh
        </button>
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
          Failed to load plans: {error}
        </div>
      ) : plans === null ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : plans.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[var(--border)] p-12 text-center">
          <div className="text-base font-medium">Nothing to approve</div>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Draft a change in Claude and it will appear here.
          </p>
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
