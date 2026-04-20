import Link from "next/link";
import type { Plan } from "@/lib/api";
import { formatRelativeTime } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

function summarizeChanges(plan: Plan): string {
  const c = plan.changes as Record<string, unknown>;
  switch (plan.operation) {
    case "add_keywords": {
      const kws = (c.keywords as Array<{ text?: string }> | undefined) ?? [];
      return `${kws.length} keyword${kws.length === 1 ? "" : "s"}`;
    }
    case "add_negative_keywords": {
      const kws = (c.keywords as unknown[] | undefined) ?? [];
      return `${kws.length} negative keyword${kws.length === 1 ? "" : "s"}`;
    }
    case "draft_responsive_search_ad": {
      const h = (c.headlines as unknown[] | undefined)?.length ?? 0;
      const d = (c.descriptions as unknown[] | undefined)?.length ?? 0;
      return `RSA · ${h} headlines / ${d} descriptions`;
    }
    case "draft_campaign": {
      const name = (c.campaign_name as string) ?? "new campaign";
      return `Campaign · ${name}`;
    }
    case "draft_ad_group": {
      return `Ad group · ${(c.ad_group_name as string) ?? ""}`;
    }
    case "draft_sitelinks": {
      const n = (c.sitelinks as unknown[] | undefined)?.length ?? 0;
      return `${n} sitelink${n === 1 ? "" : "s"}`;
    }
    default:
      return plan.entity_type || "—";
  }
}

export function PlanCard({ plan }: { plan: Plan }) {
  return (
    <Link
      href={`/plans/${plan.plan_id}`}
      className="block rounded-lg border border-[var(--border)] bg-[var(--card)] p-4 transition-colors hover:border-[var(--foreground)]/30 hover:bg-[var(--muted-bg)]"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-[var(--muted)]">
              {plan.plan_id.slice(0, 8)}
            </span>
            <StatusBadge status={plan.status} />
          </div>
          <div className="mt-1 truncate text-base font-medium">
            {plan.operation}
          </div>
          <div className="mt-0.5 truncate text-sm text-[var(--muted)]">
            {summarizeChanges(plan)}
          </div>
        </div>
        <div className="shrink-0 text-right text-xs text-[var(--muted)]">
          <div>{plan.customer_id}</div>
          <div className="mt-1">{formatRelativeTime(plan.created_at)}</div>
        </div>
      </div>
      {plan.error ? (
        <div className="mt-3 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
          {plan.error}
        </div>
      ) : null}
    </Link>
  );
}
