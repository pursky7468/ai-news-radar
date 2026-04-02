"use client";
import { useEffect, useState } from "react";

interface Props {
  onSearch: (q: string) => void;
}

export function SearchBox({ onSearch }: Props) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      onSearch(query.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [query, onSearch]);

  return (
    <input
      role="searchbox"
      type="search"
      placeholder="Search posts…"
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      className="w-full border rounded px-3 py-2 text-sm mb-4"
    />
  );
}
