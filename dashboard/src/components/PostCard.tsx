"use client";
import type { Post } from "@/lib/api";

interface Props {
  post: Post;
}

export function PostCard({ post }: Props) {
  const truncated =
    post.content.length > 280 ? post.content.slice(0, 280) + "…" : post.content;

  return (
    <article className="border border-gray-200 rounded-lg p-4 space-y-2">
      <div className="flex items-center gap-2">
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
      <a
        href={post.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-blue-600 underline"
        aria-label="View on X"
      >
        View on X →
      </a>
    </article>
  );
}
