import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-[var(--primary)] text-[var(--primary-fg)] hover:opacity-90 disabled:opacity-50",
  secondary:
    "border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--muted-bg)] disabled:opacity-50",
  danger:
    "bg-[var(--danger)] text-white hover:opacity-90 disabled:opacity-50",
  ghost:
    "text-[var(--foreground)] hover:bg-[var(--muted-bg)] disabled:opacity-50",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = "primary", className, ...rest }: Props) {
  return (
    <button
      {...rest}
      className={cn(
        "inline-flex items-center justify-center rounded-md px-3.5 py-2 text-sm font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
        VARIANTS[variant],
        className,
      )}
    />
  );
}
