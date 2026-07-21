import Link from "next/link";
import type { ItemResponse } from "@/lib/types";

const STATUS_BADGE: Record<string, string> = {
  processing: "解析中",
  failed: "解析失敗",
};

export function ItemCard({ item }: { item: ItemResponse }) {
  const badge = STATUS_BADGE[item.status];

  return (
    <Link
      href={`/items/${item.id}`}
      className="group relative flex flex-col overflow-hidden rounded-lg border border-zinc-200 bg-white transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="relative aspect-square w-full bg-zinc-100 dark:bg-zinc-800">
        {item.transparent_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.transparent_image_url}
            alt={item.category ?? "衣服アイテム"}
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-sm text-zinc-400">
            画像なし
          </div>
        )}
        {badge && (
          <span className="absolute right-2 top-2 rounded-full bg-black/70 px-2 py-1 text-xs text-white">
            {badge}
          </span>
        )}
      </div>
      <div className="flex flex-col gap-1 p-3">
        <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
          {item.category ?? "-"}
        </span>
        <span className="text-xs text-zinc-500 dark:text-zinc-400">
          {[item.color_primary, item.color_secondary].filter(Boolean).join(" / ") || "-"}
        </span>
      </div>
    </Link>
  );
}
