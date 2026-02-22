/**
 * Root layout — dark theme, fonts, global providers.
 * See: docs/architecture/LLD_frontend.md § 3
 */

import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Big4",
  description: "Multi-layer agent pipeline for strategic business analysis",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-bg-primary text-white antialiased">
        {children}
      </body>
    </html>
  );
}
