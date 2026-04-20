"use client";

import { useEffect, useState } from "react";
import { api, type Account } from "@/lib/api";

interface Props {
  value: string;
  onChange: (customerId: string) => void;
}

const STORAGE_KEY = "adloop:customer_id";

export function readStoredCustomerId(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(STORAGE_KEY) ?? "";
}

export function AccountSwitcher({ value, onChange }: Props) {
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listAccounts()
      .then((res) => {
        if (cancelled) return;
        setAccounts(res.accounts ?? []);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-[var(--muted)]">Account</label>
      <select
        value={value}
        onChange={(e) => {
          const next = e.target.value;
          if (typeof window !== "undefined") {
            window.localStorage.setItem(STORAGE_KEY, next);
          }
          onChange(next);
        }}
        className="rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      >
        <option value="">All accounts</option>
        {accounts?.map((a) => (
          <option key={a.customer_id} value={a.customer_id}>
            {a.descriptive_name
              ? `${a.descriptive_name} · ${a.customer_id}`
              : a.customer_id}
          </option>
        ))}
      </select>
      {error ? (
        <span className="text-xs text-[var(--danger)]" title={error}>
          accounts unavailable
        </span>
      ) : null}
    </div>
  );
}
