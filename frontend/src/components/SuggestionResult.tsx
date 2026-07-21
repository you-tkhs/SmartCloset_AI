import { ItemCard } from "./ItemCard";
import type { SuggestResponse } from "@/lib/types";

interface SuggestionResultProps {
  result: SuggestResponse;
}

export function SuggestionResult({ result }: SuggestionResultProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <p className="text-base text-zinc-900 dark:text-zinc-100">{result.suggestion_text}</p>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">{result.styling_reason}</p>
        {!result.weather_available && (
          <p className="text-xs text-zinc-400">天気情報を取得できませんでした</p>
        )}
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
