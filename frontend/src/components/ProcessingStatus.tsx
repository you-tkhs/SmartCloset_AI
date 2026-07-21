import Link from "next/link";
import { FAILURE_REASON_MESSAGES, type UploadStatus } from "@/lib/upload";
import type { FailureReason, ItemResponse } from "@/lib/types";

interface ProcessingStatusProps {
  status: UploadStatus;
  errorMessage?: string | null;
  failureReason?: FailureReason | null;
  item?: ItemResponse | null;
  onRetryUpload?: () => void;
  onRestart?: () => void;
}

const BUTTON_CLASS =
  "self-start rounded-full bg-zinc-900 px-5 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900";

function StatusMessage({ spinner, text }: { spinner?: boolean; text: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-zinc-600 dark:text-zinc-400">
      {spinner && (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100" />
      )}
      {text}
    </div>
  );
}

export function ProcessingStatus({
  status,
  errorMessage,
  failureReason,
  item,
  onRetryUpload,
  onRestart,
}: ProcessingStatusProps) {
  switch (status) {
    case "uploading":
      return <StatusMessage spinner text="アップロード中..." />;

    case "accepted":
      return <StatusMessage spinner text="アップロード完了。AIが解析中..." />;

    case "processing":
      return <StatusMessage spinner text="AIが解析中..." />;

    case "upload_failed":
      return (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-red-600">
            {errorMessage ?? "アップロードに失敗しました。"}
          </p>
          {onRetryUpload && (
            <button type="button" onClick={onRetryUpload} className={BUTTON_CLASS}>
              再試行
            </button>
          )}
        </div>
      );

    case "processing_failed":
      return (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-red-600">
            {failureReason ? FAILURE_REASON_MESSAGES[failureReason] : "処理に失敗しました。"}
          </p>
          <button type="button" onClick={onRestart} className={BUTTON_CLASS}>
            別の写真でやり直す
          </button>
        </div>
      );

    case "polling_timeout":
      return (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            処理に時間がかかっています。処理は継続中の可能性があります。
          </p>
          <Link
            href="/"
            className="self-start text-sm font-medium text-zinc-900 underline dark:text-zinc-100"
          >
            クローゼットで確認
          </Link>
        </div>
      );

    case "completed":
      return (
        <div className="flex flex-col gap-4">
          {item?.transparent_image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={item.transparent_image_url}
              alt="抽出結果プレビュー"
              className="max-h-64 w-full rounded-lg border border-zinc-200 object-contain dark:border-zinc-800"
            />
          )}
          {item && (
            <div className="flex flex-col gap-1 text-sm text-zinc-600 dark:text-zinc-400">
              <span>カテゴリ: {item.category ?? "-"}</span>
              <span>
                色: {[item.color_primary, item.color_secondary].filter(Boolean).join(" / ") || "-"}
              </span>
              <span>柄: {item.pattern ?? "-"}</span>
              <span>素材: {item.material ?? "-"}</span>
            </div>
          )}
          <div className="flex gap-3">
            <Link
              href="/"
              className="rounded-full bg-zinc-900 px-5 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
            >
              クローゼットを見る
            </Link>
            <button
              type="button"
              onClick={onRestart}
              className="rounded-full border border-zinc-300 px-5 py-2 text-sm dark:border-zinc-700"
            >
              続けて登録
            </button>
          </div>
        </div>
      );

    default:
      return null;
  }
}
