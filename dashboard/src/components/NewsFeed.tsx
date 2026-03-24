"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchNews, type Post } from "@/lib/api";
import { PostCard } from "./PostCard";

interface Props {
  pollIntervalMs?: number;
}

export function NewsFeed({ pollIntervalMs = 5 * 60 * 1000 }: Props) {
  const [posts, setPosts] = useState<Post[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [hasBanner, setHasBanner] = useState(false);
  const latestIdRef = useRef<number | null>(null);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const data = await fetchNews({ page: p, per_page: 20 });
      if (p === 1) {
        setPosts(data.items);
        latestIdRef.current = data.items[0]?.id ?? null;
      } else {
        setPosts((prev) => [...prev, ...data.items]);
      }
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(1);
  }, [load]);

  // Polling
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const data = await fetchNews({ page: 1, per_page: 20 });
        const newestId = data.items[0]?.id ?? null;
        if (newestId && latestIdRef.current && newestId !== latestIdRef.current) {
          setHasBanner(true);
        }
      } catch {
        // ignore poll errors
      }
    }, pollIntervalMs);
    return () => clearInterval(id);
  }, [pollIntervalMs]);

  const handleLoadMore = () => {
    const next = page + 1;
    setPage(next);
    load(next);
  };

  const handleBannerClick = () => {
    setHasBanner(false);
    setPage(1);
    load(1);
  };

  const hasMore = posts.length < total;

  return (
    <div>
      {hasBanner && (
        <button
          onClick={handleBannerClick}
          className="w-full bg-blue-600 text-white py-2 text-sm"
        >
          New posts available — Click to refresh
        </button>
      )}

      {loading && posts.length === 0 ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-100 rounded animate-pulse" />
          ))}
        </div>
      ) : posts.length === 0 ? (
        <p className="text-gray-500 text-center py-8">No posts found.</p>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}

      {hasMore && (
        <button
          onClick={handleLoadMore}
          disabled={loading}
          className="mt-4 w-full py-2 border rounded text-sm"
        >
          {loading ? "Loading…" : "Load more"}
        </button>
      )}
    </div>
  );
}
