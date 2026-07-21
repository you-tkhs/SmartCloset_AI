"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { Category, Material, Pattern } from "@/lib/types";

const CATEGORIES: Category[] = [
  "outer",
  "tops",
  "bottoms",
  "dress",
  "shoes",
  "bag",
  "hat",
  "watch",
  "glasses",
];

const PATTERNS: Pattern[] = [
  "無地",
  "ストライプ",
  "ボーダー",
  "チェック",
  "ドット",
  "花柄",
  "ロゴ",
  "プリント",
  "カモフラ",
  "その他",
];

const MATERIALS: Material[] = [
  "コットン",
  "デニム",
  "ニット",
  "レザー",
  "ナイロン",
  "フリース",
  "ウール",
  "スウェット",
  "ファー",
  "ボア",
  "金属",
  "樹脂",
  "その他",
];

const SELECT_CLASS =
  "rounded border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900";

export function FilterBar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function updateParam(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.delete("page");
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap gap-3">
      <select
        value={searchParams.get("category") ?? ""}
        onChange={(e) => updateParam("category", e.target.value)}
        className={SELECT_CLASS}
      >
        <option value="">カテゴリ(すべて)</option>
        {CATEGORIES.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <input
        type="text"
        placeholder="色"
        defaultValue={searchParams.get("color") ?? ""}
        onBlur={(e) => updateParam("color", e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") updateParam("color", e.currentTarget.value);
        }}
        className={SELECT_CLASS}
      />

      <select
        value={searchParams.get("pattern") ?? ""}
        onChange={(e) => updateParam("pattern", e.target.value)}
        className={SELECT_CLASS}
      >
        <option value="">柄(すべて)</option>
        {PATTERNS.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>

      <select
        value={searchParams.get("material") ?? ""}
        onChange={(e) => updateParam("material", e.target.value)}
        className={SELECT_CLASS}
      >
        <option value="">素材(すべて)</option>
        {MATERIALS.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    </div>
  );
}
