import Link from "next/link";
import { FilterBar } from "@/components/FilterBar";
import { ItemGrid } from "@/components/ItemGrid";
import { listItems, type ListItemsParams } from "@/lib/api";

export const dynamic = "force-dynamic";

function firstValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

interface HomePageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const params = await searchParams;
  const category = firstValue(params.category);
  const color = firstValue(params.color);
  const pattern = firstValue(params.pattern);
  const material = firstValue(params.material);
  const page = Number(firstValue(params.page) ?? "1") || 1;

  const query: ListItemsParams = { category, color, pattern, material, page, page_size: 20 };

  const currentQuery = new URLSearchParams();
  if (category) currentQuery.set("category", category);
  if (color) currentQuery.set("color", color);
  if (pattern) currentQuery.set("pattern", pattern);
  if (material) currentQuery.set("material", material);

  let data: Awaited<ReturnType<typeof listItems>> | null = null;
  let errorMessage: string | null = null;
  try {
    data = await listItems(query);
  } catch {
    errorMessage = "アイテムの取得に失敗しました。しばらく待ってから再度お試しください。";
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">クローゼット</h1>
      <FilterBar />
      {errorMessage ? (
        <p className="text-sm text-red-600">{errorMessage}</p>
      ) : data && data.total === 0 ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <p className="text-zinc-500 dark:text-zinc-400">衣服を登録しましょう</p>
          <Link
            href="/upload"
            className="rounded-full bg-zinc-900 px-5 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            衣服を登録する
          </Link>
        </div>
      ) : data ? (
        <ItemGrid
          items={data.items}
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          searchParams={currentQuery.toString()}
        />
      ) : null}
    </main>
  );
}
