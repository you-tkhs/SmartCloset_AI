"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ImagePreview, resizeImageIfNeeded } from "@/components/ImagePreview";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { UploadDropzone } from "@/components/UploadDropzone";
import { ApiError, getItem, getItemStatus, uploadItem } from "@/lib/api";
import type { FailureReason, ItemResponse } from "@/lib/types";
import {
  PENDING_UPLOAD_STORAGE_KEY,
  POLL_INTERVAL_MS,
  POLL_MAX_ATTEMPTS,
  type PendingUpload,
  type UploadStatus,
} from "@/lib/upload";

interface UploadState {
  status: UploadStatus;
  file: File | null;
  idempotencyKey: string | null;
  itemId: string | null;
  item: ItemResponse | null;
  failureReason: FailureReason | null;
  errorMessage: string | null;
}

const initialState: UploadState = {
  status: "idle",
  file: null,
  idempotencyKey: null,
  itemId: null,
  item: null,
  failureReason: null,
  errorMessage: null,
};

export default function UploadPage() {
  const [state, setState] = useState<UploadState>(initialState);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollAttemptsRef = useRef(0);
  const submittingRef = useRef(false);

  const clearPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  useEffect(() => clearPolling, [clearPolling]);

  const clearPendingUpload = useCallback(() => {
    localStorage.removeItem(PENDING_UPLOAD_STORAGE_KEY);
  }, []);

  const startPolling = useCallback(
    (itemId: string) => {
      clearPolling();
      pollAttemptsRef.current = 0;

      pollTimerRef.current = setInterval(async () => {
        pollAttemptsRef.current += 1;

        try {
          const statusRes = await getItemStatus(itemId);

          setState((s) => (s.status === "accepted" ? { ...s, status: "processing" } : s));

          if (statusRes.status === "completed") {
            clearPolling();
            clearPendingUpload();
            const item = await getItem(itemId);
            setState((s) => ({ ...s, status: "completed", item }));
            return;
          }

          if (statusRes.status === "failed") {
            clearPolling();
            clearPendingUpload();
            setState((s) => ({
              ...s,
              status: "processing_failed",
              failureReason: statusRes.failure_reason,
            }));
            return;
          }
        } catch {
          // ネットワーク瞬断はポーリング継続。60秒超過でタイムアウト扱いにする
        }

        if (pollAttemptsRef.current >= POLL_MAX_ATTEMPTS) {
          clearPolling();
          setState((s) => ({ ...s, status: "polling_timeout" }));
        }
      }, POLL_INTERVAL_MS);
    },
    [clearPolling, clearPendingUpload],
  );

  // design.md 12.4節: 202受信後の切断からの再開。ページ再訪問時にpending_uploadが残っていればポーリング再開
  useEffect(() => {
    const raw = localStorage.getItem(PENDING_UPLOAD_STORAGE_KEY);
    if (!raw) return;

    try {
      const pending: PendingUpload = JSON.parse(raw);
      setState((s) => ({
        ...s,
        status: "processing",
        itemId: pending.item_id,
        idempotencyKey: pending.idempotency_key,
      }));
      startPolling(pending.item_id);
    } catch {
      clearPendingUpload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = useCallback(
    async (file: File, idempotencyKey: string) => {
      if (submittingRef.current) return;
      submittingRef.current = true;
      setState((s) => ({ ...s, status: "uploading", errorMessage: null }));

      try {
        const uploadFile = await resizeImageIfNeeded(file);
        const res = await uploadItem(uploadFile, idempotencyKey);

        const pending: PendingUpload = {
          item_id: res.item_id,
          idempotency_key: idempotencyKey,
          saved_at: new Date().toISOString(),
        };
        localStorage.setItem(PENDING_UPLOAD_STORAGE_KEY, JSON.stringify(pending));

        if (res.status === "completed") {
          clearPendingUpload();
          const item = await getItem(res.item_id);
          setState((s) => ({ ...s, status: "completed", itemId: res.item_id, item }));
        } else if (res.status === "failed") {
          clearPendingUpload();
          setState((s) => ({
            ...s,
            status: "processing_failed",
            itemId: res.item_id,
            failureReason: res.failure_reason ?? null,
          }));
        } else {
          setState((s) => ({ ...s, status: "accepted", itemId: res.item_id }));
          startPolling(res.item_id);
        }
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : "通信エラーが発生しました。ネットワークを確認して再試行してください。";
        setState((s) => ({ ...s, status: "upload_failed", errorMessage: message }));
      } finally {
        submittingRef.current = false;
      }
    },
    [clearPendingUpload, startPolling],
  );

  const handleFileAccepted = useCallback(
    (file: File) => {
      const idempotencyKey = crypto.randomUUID();
      setState({ ...initialState, status: "validating", file, idempotencyKey });
      submit(file, idempotencyKey);
    },
    [submit],
  );

  const handleValidationError = useCallback((message: string) => {
    setState({ ...initialState, status: "upload_failed", errorMessage: message });
  }, []);

  const handleRetryUpload = useCallback(() => {
    if (!state.file || !state.idempotencyKey) return;
    submit(state.file, state.idempotencyKey);
  }, [state.file, state.idempotencyKey, submit]);

  const handleRestart = useCallback(() => {
    clearPolling();
    clearPendingUpload();
    setState(initialState);
  }, [clearPolling, clearPendingUpload]);

  const showDropzone = state.status === "idle" || (state.status === "upload_failed" && !state.file);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">衣服を登録</h1>

      {showDropzone && (
        <>
          {state.errorMessage && (
            <p className="text-sm text-red-600">{state.errorMessage}</p>
          )}
          <UploadDropzone
            onFileAccepted={handleFileAccepted}
            onValidationError={handleValidationError}
          />
        </>
      )}

      {!showDropzone && (
        <div className="flex flex-col gap-4">
          {state.file && state.status !== "completed" && <ImagePreview file={state.file} />}
          <ProcessingStatus
            status={state.status}
            errorMessage={state.errorMessage}
            failureReason={state.failureReason}
            item={state.item}
            onRetryUpload={handleRetryUpload}
            onRestart={handleRestart}
          />
        </div>
      )}
    </main>
  );
}
