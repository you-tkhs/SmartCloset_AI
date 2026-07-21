"use client";

import { useEffect, useState } from "react";
import { ApiError, getWeather } from "@/lib/api";
import type { WeatherInfo } from "@/lib/types";

export function WeatherBadge() {
  const [weather, setWeather] = useState<WeatherInfo | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getWeather()
      .then((res) => {
        if (!cancelled) setWeather(res);
      })
      .catch((err) => {
        if (!cancelled) setUnavailable(err instanceof ApiError || true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (unavailable) {
    return (
      <div className="text-sm text-zinc-500 dark:text-zinc-400">
        天気情報を取得できませんでした
      </div>
    );
  }

  if (!weather) {
    return <div className="text-sm text-zinc-400">天気情報を取得中...</div>;
  }

  return (
    <div className="flex items-center gap-2 rounded-full border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700">
      <span className="font-medium">{weather.city}</span>
      <span>{weather.temp}°C</span>
      <span className="text-zinc-500 dark:text-zinc-400">{weather.description}</span>
    </div>
  );
}
