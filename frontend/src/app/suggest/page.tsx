"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { SuggestForm } from "@/components/SuggestForm";
import { SuggestionResult } from "@/components/SuggestionResult";
import { WeatherBadge } from "@/components/WeatherBadge";
import { ApiError, suggest } from "@/lib/api";
import type { SuggestResponse } from "@/lib/types";

export default function SuggestPage() {
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SuggestResponse | null>(null);
  const [noCompletedItems, setNoCompletedItems] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = useCallback(async (requestText: string) => {
    setSubmitting(true);
    setErrorMessage(null);
    setNoCompletedItems(false);
    try {
      const res = await suggest({ request_text: requestText });
      setResult(res);
    } catch (err) {
      setResult(null);
      if (err instanceof ApiError && err.errorCode === "no_completed_items") {
        setNoCompletedItems(true);
      } else {
        setErrorMessage(
          err instanceof ApiError ? err.message : "提案の生成に失敗しました。しばらく待ってから再度お試しください。",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">コーデ提案</h1>

      <WeatherBadge />

      <SuggestForm onSubmit={handleSubmit} submitting={submitting} />

      {noCompletedItems && (
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

      {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}

      {result && <SuggestionResult result={result} />}
    </main>
  );
}
