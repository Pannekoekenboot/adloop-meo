"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { AccountSwitcher } from "./AccountSwitcher";

interface Props {
  customerId: string;
  onCustomerChange: (id: string) => void;
}

const LINKS = [
  { href: "/", label: "Queue" },
  { href: "/history", label: "History" },
];

export function Header({ customerId, onCustomerChange }: Props) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--background)]/85 backdrop-blur">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-6 py-3">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-sm bg-[var(--primary)]" />
            <span className="text-sm font-semibold tracking-tight">AdLoop</span>
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            {LINKS.map((l) => {
              const active =
                l.href === "/" ? pathname === "/" : pathname?.startsWith(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={cn(
                    "rounded-md px-2.5 py-1.5 transition-colors",
                    active
                      ? "bg-[var(--muted-bg)] text-[var(--foreground)]"
                      : "text-[var(--muted)] hover:text-[var(--foreground)]",
                  )}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <AccountSwitcher value={customerId} onChange={onCustomerChange} />
      </div>
    </header>
  );
}
