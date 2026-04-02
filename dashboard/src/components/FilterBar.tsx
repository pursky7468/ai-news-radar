"use client";
import { useState } from "react";
import type { NewsQueryParams } from "@/lib/api";

const LABELS = ["ai-agent", "ai-tool", "ai-model", "other"];
const SOURCES: Array<{ value: NewsQueryParams["source"]; label: string }> = [
  { value: undefined, label: "All" },
  { value: "hackernews", label: "HN" },
  { value: "reddit", label: "Reddit" },
  { value: "github", label: "GitHub" },
];

interface Props {
  onChange: (params: NewsQueryParams) => void;
}

export function FilterBar({ onChange }: Props) {
  const [activeLabel, setActiveLabel] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<NewsQueryParams["source"]>(undefined);
  const [minScore, setMinScore] = useState<number>(0);

  const emit = (
    label: string | null,
    source: NewsQueryParams["source"],
    score: number,
  ) => {
    const params: NewsQueryParams = {};
    if (label) params.label = label;
    if (source) params.source = source;
    if (score > 0) params.min_score = score;
    onChange(params);
  };

  const toggleLabel = (label: string) => {
    const next = activeLabel === label ? null : label;
    setActiveLabel(next);
    emit(next, activeSource, minScore);
  };

  const selectSource = (src: NewsQueryParams["source"]) => {
    setActiveSource(src);
    emit(activeLabel, src, minScore);
  };

  const handleScore = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setMinScore(val);
    emit(activeLabel, activeSource, val);
  };

  const handleClear = () => {
    setActiveLabel(null);
    setActiveSource(undefined);
    setMinScore(0);
    onChange({});
  };

  return (
    <div className="flex flex-wrap items-center gap-2 p-2 border-b">
      {SOURCES.map(({ value, label }) => (
        <button
          key={label}
          onClick={() => selectSource(value)}
          aria-pressed={activeSource === value}
          className={`px-3 py-1 rounded-full text-xs border ${
            activeSource === value
              ? "bg-indigo-600 text-white border-indigo-600"
              : "bg-white text-gray-700 border-gray-300"
          }`}
        >
          {label}
        </button>
      ))}

      <span className="text-gray-300 text-xs">|</span>

      {LABELS.map((label) => (
        <button
          key={label}
          onClick={() => toggleLabel(label)}
          aria-pressed={activeLabel === label}
          className={`px-3 py-1 rounded-full text-xs border ${
            activeLabel === label
              ? "bg-blue-600 text-white border-blue-600"
              : "bg-white text-gray-700 border-gray-300"
          }`}
        >
          {label}
        </button>
      ))}

      <label className="flex items-center gap-1 text-xs">
        <span>Min score</span>
        <input
          type="range"
          min={0}
          max={10}
          value={minScore}
          onChange={handleScore}
          aria-label="min score"
          className="w-24"
        />
        <span>{minScore}</span>
      </label>

      <button
        onClick={handleClear}
        className="px-3 py-1 text-xs border rounded text-gray-600"
      >
        Clear
      </button>
    </div>
  );
}
