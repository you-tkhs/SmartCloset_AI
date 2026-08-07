import type {
  ErrorResponse,
  HealthResponse,
  ItemListResponse,
  ItemResponse,
  ItemStatusResponse,
  ItemUpdateRequest,
  SuggestRequest,
  SuggestResponse,
  UploadAcceptedResponse,
  WeatherInfo,
} from "./types";

const API_BASE_URL =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "")
    : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "");

export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: ErrorResponse["error_code"];
  readonly retryable: boolean;

  constructor(status: number, body: ErrorResponse) {
    super(body.detail);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = body.error_code;
    this.retryable = body.retryable;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, init);

  if (!res.ok) {
    const body = (await res.json()) as ErrorResponse;
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

function toQueryString(params: object): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      query.set(key, String(value));
    }
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export interface ListItemsParams {
  category?: string;
  color?: string;
  pattern?: string;
  material?: string;
  status?: string;
  sort?: "created_at_desc" | "created_at_asc";
  page?: number;
  page_size?: number;
}

export function uploadItem(
  file: File,
  idempotencyKey: string,
): Promise<UploadAcceptedResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<UploadAcceptedResponse>("/api/upload", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: formData,
  });
}

export function getItemStatus(itemId: string): Promise<ItemStatusResponse> {
  return request<ItemStatusResponse>(`/api/items/${itemId}/status`);
}

export function listItems(params: ListItemsParams = {}): Promise<ItemListResponse> {
  return request<ItemListResponse>(`/api/items${toQueryString(params)}`);
}

export function getItem(itemId: string): Promise<ItemResponse> {
  return request<ItemResponse>(`/api/items/${itemId}`);
}

export function updateItem(
  itemId: string,
  update: ItemUpdateRequest,
): Promise<ItemResponse> {
  return request<ItemResponse>(`/api/items/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
}

export function deleteItem(itemId: string): Promise<void> {
  return request<void>(`/api/items/${itemId}`, { method: "DELETE" });
}

export function suggest(body: SuggestRequest): Promise<SuggestResponse> {
  return request<SuggestResponse>("/api/suggest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getWeather(city?: string): Promise<WeatherInfo> {
  return request<WeatherInfo>(`/api/weather${toQueryString({ city })}`);
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}
