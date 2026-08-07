"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { SuggestForm } from "@/components/SuggestForm";
import { SuggestionResult } from "@/components/SuggestionResult";
import { ApiError, suggest } from "@/lib/api";
import type { SuggestResponse } from "@/lib/types";

interface ConversationEntry {
  id: string;
  requestText: string;
  status: "loading" | "done" | "error" | "no_completed_items";
  result?: SuggestResponse;
  errorMessage?: string;
}

export default function SuggestPage() {
  const [entries, setEntries] = useState<ConversationEntry[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = useCallback(async (requestText: string) => {
    const id = crypto.randomUUID();
    setEntries((prev) => [...prev, { id, requestText, status: "loading" }]);
    setSubmitting(true);
    try {
      const res = await suggest({ request_text: requestText });
      setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, status: "done", result: res } : e)));
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === "no_completed_items") {
        setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, status: "no_completed_items" } : e)));
      } else {
        const errorMessage =
          err instanceof ApiError ? err.message : "提案の生成に失敗しました。しばらく待ってから再度お試しください。";
        setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, status: "error", errorMessage } : e)));
      }
    } finally {
      setSubmitting(false);
    }
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">コーデ提案</h1>

      <div className="flex flex-col gap-6">
        {entries.map((entry) => (
          <div key={entry.id} className="flex flex-col gap-3">
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-zinc-900 px-4 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900">
                {entry.requestText}
              </div>
            </div>

            {entry.status === "loading" && <p className="text-sm text-zinc-400">提案を作成中...</p>}

            {entry.status === "no_completed_items" && (
              <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  クローゼットに登録済みの衣服がありません。先に衣服を登録してください。
                </p>
                <Link
                  href="/upload"
                  className="self-start rounded-full bg-zinc-900 px-5 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
                >
                  衣服を登録する
                </Link>
              </div>
            )}

            {entry.status === "error" && <p className="text-sm text-red-600">{entry.errorMessage}</p>}

            {entry.status === "done" && entry.result && <SuggestionResult result={entry.result} />}
          </div>
        ))}
      </div>

      <SuggestForm onSubmit={handleSubmit} submitting={submitting} />
    </main>
  );
}
