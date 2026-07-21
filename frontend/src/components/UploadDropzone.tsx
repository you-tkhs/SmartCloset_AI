"use client";

import { useCallback, useRef, useState } from "react";
import { ACCEPTED_MIME_TYPES, MAX_UPLOAD_SIZE_BYTES } from "@/lib/upload";

interface UploadDropzoneProps {
  onFileAccepted: (file: File) => void;
  onValidationError: (message: string) => void;
}

export function UploadDropzone({ onFileAccepted, onValidationError }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

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
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        validateAndAccept(e.dataTransfer.files?.[0]);
      }}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
        isDragging
          ? "border-zinc-900 bg-zinc-50 dark:border-zinc-100 dark:bg-zinc-900"
          : "border-zinc-300 dark:border-zinc-700"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png"
        className="hidden"
        onChange={(e) => {
          validateAndAccept(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        クリックして画像を選択、またはドラッグ&ドロップ
      </p>
      <p className="text-xs text-zinc-400">JPEG / PNG・10MBまで</p>
    </div>
  );
}
