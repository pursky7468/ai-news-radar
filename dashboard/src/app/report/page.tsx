"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { fetchLatestReport, triggerDigest, type Report } from "@/lib/api";

type State =
  | { status: "loading" }
  | { status: "ok"; report: Report }
  | { status: "empty" }
  | { status: "error"; message: string };

export default function ReportPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [generating, setGenerating] = useState(false);

  const loadReport = () => {
    setState({ status: "loading" });
    fetchLatestReport()
      .then((r) => setState({ status: "ok", report: r }))
      .catch((e: Error) => {
        if (e.message.includes("404")) {
          setState({ status: "empty" });
        } else {
          setState({ status: "error", message: e.message });
        }
      });
  };

  useEffect(() => { loadReport(); }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await triggerDigest();
      // Wait briefly for summarization to complete before reloading
      await new Promise((r) => setTimeout(r, 2000));
      loadReport();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setState({ status: "error", message: msg });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">每日 AI 新聞彙整</h2>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="text-xs px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {generating ? "生成中…" : "重新生成"}
        </button>
      </div>

      {state.status === "loading" && (
        <p className="text-sm text-gray-500">載入中…</p>
      )}

      {state.status === "empty" && (
        <div className="border border-dashed border-gray-300 rounded-lg p-8 text-center space-y-3">
          <p className="text-gray-500 text-sm">尚未生成任何報告</p>
          <p className="text-gray-400 text-xs">
            請先在 <code className="bg-gray-100 px-1 rounded">.env</code> 設定{" "}
            <code className="bg-gray-100 px-1 rounded">GEMINI_API_KEY</code>，<br />
            再點「重新生成」觸發 digest 並生成中文摘要。
          </p>
        </div>
      )}

      {state.status === "error" && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">
          {state.message}
        </div>
      )}

      {state.status === "ok" && (
        <div className="space-y-2">
          <div className="flex gap-3 text-xs text-gray-400">
            <span>生成時間：{new Date(state.report.generated_at).toLocaleString("zh-TW")}</span>
            <span>·</span>
            <span>{state.report.post_count} 篇文章</span>
            <span>·</span>
            <span>{state.report.model_used}</span>
          </div>
          <article className="prose prose-sm max-w-none bg-white border border-gray-200 rounded-lg p-6">
            <ReactMarkdown>{state.report.content}</ReactMarkdown>
          </article>
        </div>
      )}
    </div>
  );
}
