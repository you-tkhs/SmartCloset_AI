// design.md 6章のバックエンドスキーマと1:1で対応する型定義

export type ItemStatus = "processing" | "completed" | "failed";

export type FailureReason =
  | "image_read_error"
  | "no_mask"
  | "llm_error"
  | "internal_error"
  | "processing_interrupted";

export type Category =
  | "outer"
  | "tops"
  | "bottoms"
  | "dress"
  | "shoes"
  | "bag"
  | "hat"
  | "watch"
  | "glasses";

export type Pattern =
  | "無地"
  | "ストライプ"
  | "ボーダー"
  | "チェック"
  | "ドット"
  | "花柄"
  | "ロゴ"
  | "プリント"
  | "カモフラ"
  | "その他";

export type Material =
  | "コットン"
  | "デニム"
  | "ニット"
  | "レザー"
  | "ナイロン"
  | "フリース"
  | "ウール"
  | "スウェット"
  | "ファー"
  | "ボア"
  | "金属"
  | "樹脂"
  | "その他";

export type ErrorCode =
  | "file_too_large"
  | "unsupported_media_type"
  | "invalid_image"
  | "validation_error"
  | "idempotency_key_conflict"
  | "item_not_found"
  | "item_is_processing"
  | "item_not_editable"
  | "no_completed_items"
  | "insufficient_storage"
  | "storage_error"
  | "database_error"
  | "service_unavailable"
  | "internal_error";

// 6.5節: ItemResponse(共通スキーマ)
export interface ItemResponse {
  id: string;
  status: ItemStatus;
  failure_reason: FailureReason | null;
  category: Category | null;
  color_primary: string | null;
  color_secondary: string | null;
  pattern: Pattern | null;
  material: Material | null;
  silhouette: string | null;
  yolo_pred_class: string | null;
  yolo_confidence: number | null;
  num_instances: number | null;
  is_user_corrected: boolean;
  original_image_url: string | null;
  transparent_image_url: string | null;
  original_filename: string | null;
  created_at: string;
  updated_at: string;
}

// 6.4節: GET /api/items の応答
export interface ItemListResponse {
  items: ItemResponse[];
  total: number;
  page: number;
  page_size: number;
}

// 6.2節: POST /api/upload の応答
export interface UploadAcceptedResponse {
  item_id: string;
  status: ItemStatus;
  failure_reason?: FailureReason | null;
}

// 6.3節: GET /api/items/{item_id}/status の応答
export interface ItemStatusResponse {
  item_id: string;
  status: ItemStatus;
  failure_reason: FailureReason | null;
}

// 6.6節: PATCH /api/items/{item_id} のリクエスト(全フィールド任意)
export interface ItemUpdateRequest {
  category?: Category;
  color_primary?: string;
  color_secondary?: string | null;
  pattern?: Pattern;
  material?: Material;
  silhouette?: string;
}

// 6.8節: POST /api/suggest のリクエスト
export interface SuggestRequest {
  request_text: string;
  city?: string | null;
  use_weather?: boolean;
}

// 6.9節: GET /api/weather の応答
export interface WeatherInfo {
  city: string;
  temp: number;
  feels_like: number;
  description: string;
  humidity: number;
  wind_speed: number;
}

// 6.8節: POST /api/suggest の応答
export interface SuggestResponse {
  suggestion_text: string;
  styling_reason: string;
  items: ItemResponse[];
  weather: WeatherInfo | null;
  weather_available: boolean;
  log_id: string;
}

// 6.10節: GET /api/health の応答
export interface HealthResponse {
  status: "ok" | "degraded";
  model_loaded: boolean;
  database_available: boolean;
  storage_writable: boolean;
  storage_free_mb: number;
}

// 13.1節: 統一エラー応答
export interface ErrorResponse {
  detail: string;
  error_code: ErrorCode;
  retryable: boolean;
}
