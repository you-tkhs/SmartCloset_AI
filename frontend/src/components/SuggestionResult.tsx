import { ItemCard } from "./ItemCard";
import { SparklesIcon } from "@/components/icons";
import type { SuggestResponse } from "@/lib/types";

interface SuggestionResultProps {
  result: SuggestResponse;
}

export function SuggestionResult({ result }: SuggestionResultProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900">
          <SparklesIcon className="h-5 w-5" />
        </div>
        <div className="flex max-w-[85%] flex-col gap-2 rounded-2xl rounded-tl-sm border border-zinc-200 bg-zinc-50 px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
          <p className="text-base text-zinc-900 dark:text-zinc-100">{result.suggestion_text}</p>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{result.styling_reason}</p>
          {!result.weather_available && (
            <p className="text-xs text-zinc-400">※天気情報は考慮されていません</p>
          )}
        </div>
      </div>

      {result.items.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            おすすめのアイテム
          </span>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            {result.items.map((item) => (
              <div
                key={item.id}
                className="rounded-lg ring-2 ring-zinc-900 dark:ring-zinc-100"
              >
                <ItemCard item={item} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
