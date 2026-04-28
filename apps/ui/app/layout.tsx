import type { ReactNode } from "react";

export const metadata = {
  title: "SpaceOps UI",
  description: "Incidents and approvals operator UI"
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
          color: "#e7edf7"
        }}
      >
        {children}
      </body>
    </html>
  );
}
