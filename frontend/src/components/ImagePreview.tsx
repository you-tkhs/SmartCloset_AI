"use client";

import { useEffect, useState } from "react";

interface ImagePreviewProps {
  file: File;
}

export function ImagePreview({ file }: ImagePreviewProps) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  if (!url) return null;

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt="アップロード画像プレビュー"
      className="max-h-80 w-full rounded-lg border border-zinc-200 object-contain dark:border-zinc-800"
    />
  );
}

// design.md 12.7節: 長辺1280px超のみCanvas APIで縮小する任意最適化(サーバー側検証が正のため必須ではない)
export async function resizeImageIfNeeded(file: File): Promise<File> {
  if (file.type !== "image/jpeg") return file;

  const bitmap = await createImageBitmap(file);
  const longSide = Math.max(bitmap.width, bitmap.height);
  if (longSide <= 1280) {
    bitmap.close();
    return file;
  }

  const scale = 1280 / longSide;
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    bitmap.close();
    return file;
  }
  ctx.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/jpeg", 0.85),
  );
  if (!blob) return file;

  return new File([blob], file.name, { type: "image/jpeg" });
}
