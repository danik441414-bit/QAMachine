"use client";

import { useEffect } from "react";
import { adminApi } from "@/lib/api";

export function TrackVisit({ path }: { path: string }) {
  useEffect(() => {
    adminApi.trackVisit(path);
  }, [path]);
  return null;
}
