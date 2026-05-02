import { Suspense, type ReactNode } from "react";

export default function IncidentsLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<p style={{ padding: 24 }}>Loading…</p>}>{children}</Suspense>
  );
}
