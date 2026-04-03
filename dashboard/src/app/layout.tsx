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
        <header className="bg-white border-b px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-bold">AI News Researcher</h1>
          <nav className="flex gap-4 text-sm">
            <a href="/" className="text-gray-600 hover:text-gray-900">📰 新聞 Feed</a>
            <a href="/report" className="text-gray-600 hover:text-gray-900">📋 每日彙整</a>
          </nav>
        </header>
        <main className="max-w-2xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
