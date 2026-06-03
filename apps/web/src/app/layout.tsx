import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "MeetingMind — Every commitment, tracked.",
  description: "AI meeting intelligence that automatically captures, extracts, and holds teams accountable.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-neutral-50 text-neutral-900 font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
