"use client";
import { useState } from "react";
import { triggerDigest } from "@/lib/api";

export function DigestButton() {
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleClick = async () => {
    setStatus("loading");
    try {
      const result = await triggerDigest();
      setMessage(`Digest sent: ${result.posts_included} posts`);
      setStatus("success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessage(`Error: ${msg}`);
      setStatus("error");
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        disabled={status === "loading"}
        className="px-4 py-2 bg-blue-600 text-white rounded text-sm disabled:opacity-50"
      >
        {status === "loading" ? "Sending…" : "Send Digest Now"}
      </button>
      {status === "success" && (
        <p role="status" className="mt-2 text-green-700 text-sm">
          {message}
        </p>
      )}
      {status === "error" && (
        <p role="alert" className="mt-2 text-red-700 text-sm">
          {message}
        </p>
      )}
    </div>
  );
}
