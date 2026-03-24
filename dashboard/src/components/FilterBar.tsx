"use client";
import { useState } from "react";
import type { NewsQueryParams } from "@/lib/api";

const LABELS = ["ai-agent", "ai-tool", "ai-model", "other"];

interface Props {
  onChange: (params: NewsQueryParams) => void;
}

export function FilterBar({ onChange }: Props) {
  const [activeLabel, setActiveLabel] = useState<string | null>(null);
  const [minScore, setMinScore] = useState<number>(0);

  const emit = (label: string | null, score: number) => {
    const params: NewsQueryParams = {};
    if (label) params.label = label;
    if (score > 0) params.min_score = score;
    onChange(params);
  };

  const toggleLabel = (label: string) => {
    const next = activeLabel === label ? null : label;
    setActiveLabel(next);
    emit(next, minScore);
  };

  const handleScore = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setMinScore(val);
    emit(activeLabel, val);
  };

  const handleClear = () => {
    setActiveLabel(null);
    setMinScore(0);
    onChange({});
  };

  return (
    <div className="flex flex-wrap items-center gap-2 p-2 border-b">
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
