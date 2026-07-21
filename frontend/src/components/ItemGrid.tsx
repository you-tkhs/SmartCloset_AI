import Link from "next/link";
import { ItemCard } from "./ItemCard";
import type { ItemResponse } from "@/lib/types";

interface ItemGridProps {
  items: ItemResponse[];
  page: number;
  pageSize: number;
  total: number;
  searchParams: string;
}

export function ItemGrid({ items, page, pageSize, total, searchParams }: ItemGridProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  function pageHref(target: number) {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(target));
    return `/?${params.toString()}`;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
        {items.map((item) => (
          <ItemCard key={item.id} item={item} />
        ))}
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 text-sm">
          <Link
            href={pageHref(page - 1)}
            aria-disabled={page <= 1}
            className={
              page <= 1
                ? "pointer-events-none text-zinc-300 dark:text-zinc-700"
                : "text-zinc-900 dark:text-zinc-100"
            }
          >
            前へ
          </Link>
          <span className="text-zinc-500 dark:text-zinc-400">
            {page} / {totalPages}
          </span>
          <Link
            href={pageHref(page + 1)}
            aria-disabled={page >= totalPages}
            className={
              page >= totalPages
                ? "pointer-events-none text-zinc-300 dark:text-zinc-700"
                : "text-zinc-900 dark:text-zinc-100"
            }
          >
            次へ
          </Link>
        </div>
      )}
    </div>
  );
}
