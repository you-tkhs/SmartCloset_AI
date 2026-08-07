"use client";

import { useCallback, useRef } from "react";
import { ACCEPTED_MIME_TYPES, MAX_UPLOAD_SIZE_BYTES } from "@/lib/upload";

interface UploadDropzoneProps {
  onFileAccepted: (file: File) => void;
  onValidationError: (message: string) => void;
}

export function UploadDropzone({ onFileAccepted, onValidationError }: UploadDropzoneProps) {
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const libraryInputRef = useRef<HTMLInputElement>(null);

  const validateAndAccept = useCallback(
    (file: File | undefined | null) => {
      if (!file) return;
      if (!ACCEPTED_MIME_TYPES.includes(file.type)) {
        onValidationError("JPEG/PNG形式のみ対応しています。");
        return;
      }
      if (file.size > MAX_UPLOAD_SIZE_BYTES) {
        onValidationError("10MB以下の画像をご利用ください。");
        return;
      }
      onFileAccepted(file);
    },
    [onFileAccepted, onValidationError],
  );

  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-lg border-2 border-zinc-300 p-12 text-center dark:border-zinc-700">
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/jpeg,image/png"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          validateAndAccept(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <input
        ref={libraryInputRef}
        type="file"
        accept="image/jpeg,image/png"
        className="hidden"
        onChange={(e) => {
          validateAndAccept(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <div className="flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={() => cameraInputRef.current?.click()}
          className="rounded-full bg-zinc-900 px-5 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
        >
          写真を撮る
        </button>
        <button
          type="button"
          onClick={() => libraryInputRef.current?.click()}
          className="rounded-full border border-zinc-300 px-5 py-2 text-sm text-zinc-700 dark:border-zinc-700 dark:text-zinc-300"
        >
          ライブラリから選択
        </button>
      </div>
      <p className="text-xs text-zinc-400">JPEG / PNG・10MBまで</p>
    </div>
  );
}
