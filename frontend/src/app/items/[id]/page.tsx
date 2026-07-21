"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useCallback, useEffect, useState } from "react";
import { MetadataEditForm } from "@/components/MetadataEditForm";
import { ApiError, deleteItem, getItem, updateItem } from "@/lib/api";
import type { ItemResponse, ItemUpdateRequest } from "@/lib/types";

type ImageKind = "transparent" | "original";

export default function ItemDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();

  const [item, setItem] = useState<ItemResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [imageKind, setImageKind] = useState<ImageKind>("transparent");
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const loadItem = useCallback(async () => {
    try {
      const res = await getItem(id);
      setItem(res);
      setImageKind(res.transparent_image_url ? "transparent" : "original");
    } catch (err) {
      setLoadError(
        err instanceof ApiError ? err.message : "アイテムの取得に失敗しました。",
      );
    }
  }, [id]);

  useEffect(() => {
    loadItem();
  }, [loadItem]);

  const handleSave = useCallback(
    async (update: ItemUpdateRequest) => {
      setSubmitting(true);
      setToastMessage(null);
      try {
        const updated = await updateItem(id, update);
        setItem(updated);
        setToastMessage("保存しました。");
      } catch (err) {
        setToastMessage(
          err instanceof ApiError ? err.message : "保存に失敗しました。",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [id],
  );

  const handleDelete = useCallback(async () => {
    setDeleting(true);
    setToastMessage(null);
    try {
      await deleteItem(id);
      router.push("/");
    } catch (err) {
      setToastMessage(
        err instanceof ApiError ? err.message : "削除に失敗しました。",
      );
      setDeleting(false);
      setConfirmingDelete(false);
    }
  }, [id, router]);

  if (loadError) {
    return (
      <main className="mx-auto flex w-full max-w-2xl flex-col gap-4 p-6">
        <p className="text-sm text-red-600">{loadError}</p>
        <Link href="/" className="text-sm font-medium underline">
          クローゼットへ戻る
        </Link>
      </main>
    );
  }

  if (!item) {
    return <main className="mx-auto w-full max-w-2xl p-6 text-sm text-zinc-500">読み込み中...</main>;
  }

  const imageUrl = imageKind === "transparent" ? item.transparent_image_url : item.original_image_url;

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">アイテム詳細</h1>
        <Link href="/" className="text-sm text-zinc-500 underline">
          クローゼットへ戻る
        </Link>
      </div>

      {toastMessage && (
        <p className="rounded border border-zinc-300 bg-zinc-50 px-3 py-2 text-sm text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
          {toastMessage}
        </p>
      )}

      <div className="flex flex-col gap-2">
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={item.category ?? "衣服アイテム"}
            className="max-h-96 w-full rounded-lg border border-zinc-200 object-contain dark:border-zinc-800"
          />
        ) : (
          <div className="flex h-64 w-full items-center justify-center rounded-lg border border-zinc-200 text-sm text-zinc-400 dark:border-zinc-800">
            画像なし
          </div>
        )}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setImageKind("transparent")}
            disabled={!item.transparent_image_url}
            className={`rounded-full border px-3 py-1 text-xs disabled:opacity-40 ${
              imageKind === "transparent"
                ? "border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900"
                : "border-zinc-300 dark:border-zinc-700"
            }`}
          >
            透過画像
          </button>
          <button
            type="button"
            onClick={() => setImageKind("original")}
            disabled={!item.original_image_url}
            className={`rounded-full border px-3 py-1 text-xs disabled:opacity-40 ${
              imageKind === "original"
                ? "border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900"
                : "border-zinc-300 dark:border-zinc-700"
            }`}
          >
            原画像
          </button>
        </div>
      </div>

      <MetadataEditForm item={item} onSubmit={handleSave} submitting={submitting} />

      <div className="border-t border-zinc-200 pt-4 dark:border-zinc-800">
        {!confirmingDelete ? (
          <button
            type="button"
            onClick={() => setConfirmingDelete(true)}
            className="rounded-full border border-red-300 px-5 py-2 text-sm text-red-600"
          >
            削除
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-sm text-zinc-700 dark:text-zinc-300">
              本当に削除しますか?この操作は取り消せません。
            </span>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-full bg-red-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {deleting ? "削除中..." : "削除する"}
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDelete(false)}
              disabled={deleting}
              className="rounded-full border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700"
            >
              キャンセル
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
