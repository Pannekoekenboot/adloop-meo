import { cn } from "@/lib/cn";
import type { PlanStatus } from "@/lib/api";

const STYLES: Record<PlanStatus, string> = {
  PENDING: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  APPLIED: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  REJECTED: "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300",
  FAILED: "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200",
  DRY_RUN_SUCCESS:
    "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-200",
};

export function StatusBadge({ status }: { status: PlanStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium tracking-tight",
        STYLES[status] ?? "bg-stone-200 text-stone-700",
      )}
    >
      {status}
    </span>
  );
}
