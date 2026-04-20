"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { Header } from "./Header";
import { readStoredCustomerId } from "./AccountSwitcher";

interface ShellContextValue {
  customerId: string;
  setCustomerId: (id: string) => void;
}

const ShellContext = createContext<ShellContextValue | null>(null);

export function useShell(): ShellContextValue {
  const ctx = useContext(ShellContext);
  if (!ctx) throw new Error("useShell must be used inside <ClientShell>");
  return ctx;
}

export function ClientShell({ children }: { children: React.ReactNode }) {
  const [customerId, setCustomerId] = useState("");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    // Hydrate once from localStorage after mount. setState-in-effect is
    // unavoidable for reading browser-only state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCustomerId(readStoredCustomerId());
    setHydrated(true);
  }, []);

  return (
    <ShellContext.Provider value={{ customerId, setCustomerId }}>
      <Header customerId={customerId} onCustomerChange={setCustomerId} />
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">
        {hydrated ? children : null}
      </main>
    </ShellContext.Provider>
  );
}
