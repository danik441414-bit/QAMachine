"use client";

import { useState } from "react";
import Link from "next/link";
import { Mail, CheckCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail]     = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent]       = useState(false);
  const [error, setError]     = useState("");

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    if (!email.trim()) { setError("Email is required"); return; }
    setError("");
    setLoading(true);
    try {
      await authApi.forgotPassword(email.trim());
      setSent(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <div className="animate-slide-up text-center space-y-5">
        <div className="flex justify-center">
          <div className="h-16 w-16 rounded-2xl bg-green-500/10 border border-green-500/20
                          flex items-center justify-center">
            <CheckCircle className="h-8 w-8 text-green-400" />
          </div>
        </div>
        <div>
          <h1 className="text-xl font-bold text-text-primary mb-2">Check your email</h1>
          <p className="text-sm text-text-secondary leading-relaxed">
            If <strong className="text-text-primary">{email}</strong> exists in our system,
            we sent a password reset link. Check your inbox and spam folder.
          </p>
        </div>
        <p className="text-xs text-text-muted">
          Link expires in 1 hour.
        </p>
        <Link
          href="/login"
          className="inline-block text-sm text-accent hover:underline"
        >
          Back to login
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-slide-up">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Forgot password?</h1>
        <p className="text-sm text-text-secondary">
          Enter your email and we&apos;ll send you a reset link.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => { setEmail(e.target.value); setError(""); }}
          error={error}
          leftIcon={<Mail className="h-4 w-4" />}
          autoComplete="email"
          autoFocus
        />

        <Button type="submit" size="lg" loading={loading} className="w-full mt-2">
          Send reset link
        </Button>
      </form>

      <p className="text-center text-sm text-text-secondary mt-6">
        Remember your password?{" "}
        <Link href="/login" className="text-accent hover:text-accent-hover font-medium transition-colors">
          Sign in
        </Link>
      </p>
    </div>
  );
}
