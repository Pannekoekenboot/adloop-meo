"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError, type Plan, formatRelativeTime } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/Button";

type Health = { require_dry_run: boolean };

export default function PlanDetailPage() {
  return (
    <Suspense
      fallback={<div className="text-sm text-[var(--muted)]">Loading…</div>}
    >
      <PlanDetail />
    </Suspense>
  );
}

function PlanDetail() {
  const params = useSearchParams();
  const id = params.get("id") ?? "";
  const [plan, setPlan] = useState<Plan | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [confirmApply, setConfirmApply] = useState(false);

  const reload = useCallback(() => {
    if (!id) return;
    setLoadError(null);
    api
      .getPlan(id)
      .then(setPlan)
      .catch((e: Error) => setLoadError(e.message));
    api
      .health()
      .then(setHealth)
      .catch(() => {
        /* silent — dry-run gate is re-checked server-side */
      });
  }, [id]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(reload, [reload]);

  async function approve() {
    if (!confirmApply) {
      setConfirmApply(true);
      return;
    }
    setBusy("approve");
    setActionError(null);
    try {
      await api.approvePlan(id);
      reload();
    } catch (e) {
      setActionError(extractError(e));
    } finally {
      setBusy(null);
      setConfirmApply(false);
    }
  }

  async function reject() {
    setBusy("reject");
    setActionError(null);
    try {
      await api.rejectPlan(id);
      reload();
    } catch (e) {
      setActionError(extractError(e));
    } finally {
      setBusy(null);
    }
  }

  if (!id) {
    return (
      <div className="rounded-md border border-[var(--border)] bg-[var(--card)] p-4 text-sm">
        No plan selected.{" "}
        <Link href="/" className="underline">
          Back to queue
        </Link>
        .
      </div>
    );
  }
  if (loadError) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
        Failed to load plan: {loadError}
      </div>
    );
  }
  if (!plan) {
    return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  }

  const pending = plan.status === "PENDING";
  const dryRunGate = health?.require_dry_run === true;

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/"
          className="text-xs text-[var(--muted)] hover:text-[var(--foreground)]"
        >
          ← Back to queue
        </Link>
      </div>

      <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <StatusBadge status={plan.status} />
              <span className="font-mono text-xs text-[var(--muted)]">
                {plan.plan_id}
              </span>
            </div>
            <h1 className="mt-2 text-xl font-semibold tracking-tight">
              {plan.operation}
            </h1>
            <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
              <dt className="text-[var(--muted)]">Entity</dt>
              <dd>{plan.entity_type || "—"}</dd>
              {plan.entity_id ? (
                <>
                  <dt className="text-[var(--muted)]">Entity ID</dt>
                  <dd className="font-mono text-xs">{plan.entity_id}</dd>
                </>
              ) : null}
              <dt className="text-[var(--muted)]">Customer</dt>
              <dd className="font-mono text-xs">{plan.customer_id}</dd>
              <dt className="text-[var(--muted)]">Created</dt>
              <dd>{formatRelativeTime(plan.created_at)}</dd>
              {plan.updated_at !== plan.created_at ? (
                <>
                  <dt className="text-[var(--muted)]">Updated</dt>
                  <dd>{formatRelativeTime(plan.updated_at)}</dd>
                </>
              ) : null}
              {plan.requires_double_confirm ? (
                <>
                  <dt className="text-[var(--muted)]">Safety</dt>
                  <dd className="text-[var(--warning)]">
                    requires double confirmation
                  </dd>
                </>
              ) : null}
            </dl>
          </div>

          {pending ? (
            <div className="flex flex-col items-end gap-2">
              {dryRunGate ? (
                <div className="max-w-xs rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                  Approving is disabled: <code>safety.require_dry_run</code> is{" "}
                  <strong>true</strong> in <code>~/.adloop/config.yaml</code>.
                </div>
              ) : null}
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={reject}
                  disabled={busy !== null}
                >
                  {busy === "reject" ? "Rejecting…" : "Reject"}
                </Button>
                <Button
                  variant={confirmApply ? "danger" : "primary"}
                  onClick={approve}
                  disabled={busy !== null || dryRunGate}
                  title={
                    dryRunGate
                      ? "Disabled while require_dry_run is true"
                      : undefined
                  }
                >
                  {busy === "approve"
                    ? "Applying…"
                    : confirmApply
                    ? "Confirm apply"
                    : "Approve & apply"}
                </Button>
              </div>
              {confirmApply && !busy ? (
                <div className="text-xs text-[var(--muted)]">
                  This will mutate Google Ads. Click again to confirm.{" "}
                  <button
                    onClick={() => setConfirmApply(false)}
                    className="underline"
                  >
                    Cancel
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        {actionError ? (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
            {actionError}
          </div>
        ) : null}
      </div>

      <Section title="Proposed changes">
        <JsonBlock value={plan.changes} />
      </Section>

      {plan.dry_run_result ? (
        <Section title="Dry run result">
          <JsonBlock value={plan.dry_run_result} />
        </Section>
      ) : null}

      {plan.result ? (
        <Section title="Apply result">
          <JsonBlock value={plan.result} />
        </Section>
      ) : null}

      {plan.error ? (
        <Section title="Error">
          <pre className="whitespace-pre-wrap rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
            {plan.error}
          </pre>
        </Section>
      ) : null}
    </div>
  );
}

function extractError(e: unknown): string {
  if (e instanceof ApiError) {
    return typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail);
  }
  if (e instanceof Error) return e.message;
  return String(e);
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
        {title}
      </h2>
      {children}
    </section>
  );
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="overflow-auto rounded-md border border-[var(--border)] bg-[var(--muted-bg)] p-4 font-mono text-xs leading-relaxed">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
