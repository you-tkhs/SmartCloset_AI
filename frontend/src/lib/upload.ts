import type { FailureReason } from "./types";

// design.md 12.3節: アップロード状態機械(9状態)。定数名はdesign.mdの状態名と一致させる
export type UploadStatus =
  | "idle"
  | "validating"
  | "uploading"
  | "accepted"
  | "processing"
  | "completed"
  | "upload_failed"
  | "processing_failed"
  | "polling_timeout";

export const PENDING_UPLOAD_STORAGE_KEY = "smartcloset_pending_upload";

// design.md 12.5節: 2秒間隔・最大60秒(30回)
export const POLL_INTERVAL_MS = 2000;
export const POLL_MAX_ATTEMPTS = 30;

// design.md 5.2節 MAX_UPLOAD_SIZE_MB の既定値と一致させる
export const MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024;
export const ACCEPTED_MIME_TYPES = ["image/jpeg", "image/png"];

export interface PendingUpload {
  item_id: string;
  idempotency_key: string;
  saved_at: string;
}

// design.md 12.6節: failure_reason別のユーザー向けメッセージ
export const FAILURE_REASON_MESSAGES: Record<FailureReason, string> = {
  image_read_error: "画像を読み込めませんでした。別の写真をお試しください。",
  no_mask: "衣服を検出できませんでした。衣服がはっきり写った写真をお試しください。",
  llm_error: "AI解析に失敗しました。しばらく待ってから再度アップロードしてください。",
  processing_interrupted:
    "サーバーの再起動などにより処理が中断されました。もう一度アップロードしてください。",
  internal_error: "処理に失敗しました。もう一度アップロードしてください。",
};
