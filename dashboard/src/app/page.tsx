"use client";
import { useState } from "react";
import { NewsFeed } from "@/components/NewsFeed";
import { FilterBar } from "@/components/FilterBar";
import { DigestButton } from "@/components/DigestButton";
import type { NewsQueryParams } from "@/lib/api";

export default function Home() {
  const [filters, setFilters] = useState<NewsQueryParams>({});

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-base font-semibold">AI News Feed</h2>
        <DigestButton />
      </div>
      <FilterBar onChange={setFilters} />
      <NewsFeed filters={filters} />
    </div>
  );
}
