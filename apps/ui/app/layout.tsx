import type { ReactNode } from "react";
import Link from "next/link";

export const metadata = {
  title: "SpaceOps UI",
  description: "Incidents, approvals, and replay operator UI",
};

const navLink = {
  marginRight: 20,
  color: "#9ecfff",
  textDecoration: "none",
  fontWeight: 500,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          fontFamily:
            "Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
          margin: 0,
          background: "#0b1220",
          color: "#e7edf7",
        }}
      >
        <header
          style={{
            borderBottom: "1px solid #1f2a40",
            padding: "12px 24px",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <strong style={{ marginRight: 24 }}>SpaceOps</strong>
          <nav>
            <Link href="/incidents" style={navLink}>
              Incidents
            </Link>
            <Link href="/approvals" style={navLink}>
              Approvals
            </Link>
            <Link href="/replays" style={navLink}>
              Replay
            </Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
