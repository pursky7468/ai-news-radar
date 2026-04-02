"use client";
import type { Post } from "@/lib/api";

interface Props {
  post: Post;
}

const SOURCE_BADGE: Record<string, { label: string; className: string }> = {
  hackernews: { label: "HN", className: "bg-orange-100 text-orange-800" },
  reddit: { label: "Reddit", className: "bg-red-100 text-red-700" },
  github: { label: "GitHub", className: "bg-gray-800 text-white" },
};

export function PostCard({ post }: Props) {
  const truncated =
    post.content.length > 280 ? post.content.slice(0, 280) + "…" : post.content;

  const badge = SOURCE_BADGE[post.source] ?? {
    label: post.source,
    className: "bg-gray-100 text-gray-700",
  };

  return (
    <article className="border border-gray-200 rounded-lg p-4 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.className}`}
          aria-label={`source ${post.source}`}
        >
          {badge.label}
        </span>
        {post.points != null && post.points > 0 && (
          <span
            className="bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded-full"
            aria-label={`${post.points} points`}
          >
            ▲ {post.points}
          </span>
        )}
        <span className="font-semibold text-sm">@{post.author_handle}</span>
        <span
          className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full"
          aria-label={`score ${post.relevance_score}`}
        >
          {post.relevance_score?.toFixed(1) ?? "—"}
        </span>
        {post.labels.map((l) => (
          <span
            key={l}
            className="bg-gray-100 text-gray-700 text-xs px-2 py-0.5 rounded-full"
          >
            {l}
          </span>
        ))}
      </div>
      <p className="text-sm text-gray-800">{truncated}</p>
      <div className="flex gap-3">
        <a
          href={post.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-600 underline"
          aria-label={post.source === "hackernews" ? "View article" : "View source"}
        >
          {post.source === "hackernews" ? "View article →" : "View source →"}
        </a>
        {post.source === "hackernews" && post.discussion_url && (
          <a
            href={post.discussion_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-orange-600 underline"
            aria-label="HN discussion"
          >
            HN discussion →
          </a>
        )}
      </div>
    </article>
  );
}
