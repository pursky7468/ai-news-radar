"use client";
import { useState } from "react";
import type { Post } from "@/lib/api";
import { PostCard } from "./PostCard";

interface Props {
  posts: Post[];
}

export function SearchBox({ posts }: Props) {
  const [query, setQuery] = useState("");

  const filtered = query.trim()
    ? posts.filter((p) =>
        p.content.toLowerCase().includes(query.toLowerCase())
      )
    : posts;

  return (
    <div>
      <input
        role="searchbox"
        type="search"
        placeholder="Search posts…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full border rounded px-3 py-2 text-sm mb-4"
      />
      {filtered.length === 0 ? (
        <p className="text-gray-500 text-center py-6">No posts match your search</p>
      ) : (
        <div className="space-y-4">
          {filtered.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </div>
  );
}
