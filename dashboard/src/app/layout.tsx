import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "X AI News Researcher",
  description: "Curated AI news from X",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <header className="bg-white border-b px-4 py-3">
          <h1 className="text-lg font-bold">X AI News Researcher</h1>
        </header>
        <main className="max-w-2xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
