"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchNews, type Post, type NewsQueryParams } from "@/lib/api";
import { PostCard } from "./PostCard";
import { SearchBox } from "./SearchBox";

interface Props {
  pollIntervalMs?: number;
  filters?: NewsQueryParams;
}

export function NewsFeed({ pollIntervalMs = 5 * 60 * 1000, filters = {} }: Props) {
  const [posts, setPosts] = useState<Post[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [hasBanner, setHasBanner] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const lastFetchedAtRef = useRef<string | null>(null);

  const activeFilters: NewsQueryParams = {
    ...filters,
    ...(searchQuery ? { q: searchQuery } : {}),
  };

  const load = useCallback(async (p: number, params: NewsQueryParams) => {
    setLoading(true);
    try {
      const data = await fetchNews({ ...params, page: p, per_page: 20 });
      if (p === 1) {
        setPosts(data.items);
        if (data.items[0]?.fetched_at) {
          lastFetchedAtRef.current = data.items[0].fetched_at;
        }
      } else {
        setPosts((prev) => [...prev, ...data.items]);
      }
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, []);

  // Reload when filters or search query changes
  useEffect(() => {
    setPage(1);
    load(1, activeFilters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, JSON.stringify(activeFilters)]);

  // Polling using ?since= to detect new posts
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const since = lastFetchedAtRef.current;
        if (!since) return;
        const data = await fetchNews({ ...filters, since, per_page: 1 });
        if (data.total > 0) {
          setHasBanner(true);
        }
      } catch {
        // ignore poll errors
      }
    }, pollIntervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollIntervalMs, JSON.stringify(filters)]);

  const handleLoadMore = () => {
    const next = page + 1;
    setPage(next);
    load(next, activeFilters);
  };

  const handleBannerClick = () => {
    setHasBanner(false);
    setPage(1);
    load(1, activeFilters);
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

      <SearchBox onSearch={setSearchQuery} />

      {loading && posts.length === 0 ? (
        <div className="space-y-4 mt-4">
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
