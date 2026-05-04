"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { toast } from "sonner";

export default function GoogleCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    const hash = window.location.hash.slice(1);
    const params = new URLSearchParams(hash);
    const idToken = params.get("id_token");
    const error = params.get("error");

    if (error || !idToken) {
      toast.error("Google sign-in was cancelled.");
      router.replace("/login");
      return;
    }

    authApi
      .googleLogin(idToken)
      .then(({ accessToken }) => {
        localStorage.setItem("access_token", accessToken);
        router.replace("/dashboard");
      })
      .catch(() => {
        toast.error("Google sign-in failed. Please try again.");
        router.replace("/login");
      });
  }, [router]);

  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <div className="h-8 w-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
      <p className="text-sm text-text-secondary">Signing in with Google…</p>
    </div>
  );
}
