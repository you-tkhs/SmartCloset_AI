"use client";

import { useState } from "react";

interface SuggestFormProps {
  onSubmit: (requestText: string) => void;
  submitting: boolean;
}

export function SuggestForm({ onSubmit, submitting }: SuggestFormProps) {
  const [requestText, setRequestText] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = requestText.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-sm">
        どんなコーデがいいですか?
        <textarea
          value={requestText}
          onChange={(e) => setRequestText(e.target.value)}
          maxLength={500}
          rows={3}
          placeholder="例: 明日の面接に着ていく服を提案してください"
          className="rounded border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
      </label>
      <button
        type="submit"
        disabled={submitting || !requestText.trim()}
        className="self-start rounded-full bg-zinc-900 px-5 py-2 text-sm text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {submitting ? "提案を作成中..." : "コーデを提案してもらう"}
      </button>
    </form>
  );
}
