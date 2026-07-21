"use client";

import { useState } from "react";
import type { Category, ItemResponse, ItemUpdateRequest, Material, Pattern } from "@/lib/types";

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

const INPUT_CLASS =
  "rounded border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900";

interface MetadataEditFormProps {
  item: ItemResponse;
  onSubmit: (update: ItemUpdateRequest) => Promise<void>;
  submitting: boolean;
}

export function MetadataEditForm({ item, onSubmit, submitting }: MetadataEditFormProps) {
  const [category, setCategory] = useState<Category>(item.category ?? "tops");
  const [colorPrimary, setColorPrimary] = useState(item.color_primary ?? "");
  const [colorSecondary, setColorSecondary] = useState(item.color_secondary ?? "");
  const [pattern, setPattern] = useState<Pattern>(item.pattern ?? "無地");
  const [material, setMaterial] = useState<Material>(item.material ?? "その他");
  const [silhouette, setSilhouette] = useState(item.silhouette ?? "");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      category,
      color_primary: colorPrimary,
      color_secondary: colorSecondary || null,
      pattern,
      material,
      silhouette,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <label className="flex flex-col gap-1 text-sm">
        カテゴリ
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as Category)}
          className={INPUT_CLASS}
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        主色
        <input
          type="text"
          value={colorPrimary}
          onChange={(e) => setColorPrimary(e.target.value)}
          required
          minLength={1}
          maxLength={30}
          className={INPUT_CLASS}
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        副色(任意)
        <input
          type="text"
          value={colorSecondary}
          onChange={(e) => setColorSecondary(e.target.value)}
          maxLength={30}
          className={INPUT_CLASS}
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        柄
        <select
          value={pattern}
          onChange={(e) => setPattern(e.target.value as Pattern)}
          className={INPUT_CLASS}
        >
          {PATTERNS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        素材
        <select
          value={material}
          onChange={(e) => setMaterial(e.target.value as Material)}
          className={INPUT_CLASS}
        >
          {MATERIALS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        シルエット
        <input
          type="text"
          value={silhouette}
          onChange={(e) => setSilhouette(e.target.value)}
          required
          minLength={1}
          maxLength={50}
          className={INPUT_CLASS}
        />
      </label>

      <button
        type="submit"
        disabled={submitting}
        className="self-start rounded-full bg-zinc-900 px-5 py-2 text-sm text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {submitting ? "保存中..." : "保存"}
      </button>
    </form>
  );
}
