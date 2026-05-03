"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Mail, Lock, User, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { GoogleLogin } from "@react-oauth/google";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api";

const FREE_PERKS = [
  "3 QA runs / month",
  "UI/UX & Functional testing",
  "AI bug reports",
];

export default function SignupPage() {
  const router = useRouter();
  const [name, setName]           = useState("");
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [showPass, setShowPass]   = useState(false);
  const [loading, setLoading]     = useState(false);
  const [errors, setErrors]       = useState<{
    name?: string; email?: string; password?: string;
  }>({});

  function validate(): boolean {
    const e: typeof errors = {};
    if (!name.trim())  e.name  = "Name is required";
    if (!email.trim()) e.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = "Enter a valid email";
    if (!password)     e.password = "Password is required";
    else if (password.length < 8) e.password = "Minimum 8 characters";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  const [emailSent, setEmailSent]       = useState(false);
  const [resending, setResending]       = useState(false);
  const [magicEmail, setMagicEmail]     = useState("");
  const [magicLoading, setMagicLoading] = useState(false);
  const [magicSent, setMagicSent]       = useState(false);

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    if (!validate() || loading) return;

    setLoading(true);
    try {
      const result = await authApi.signup(name.trim(), email.trim(), password);
      if (result.verificationRequired) {
        setEmailSent(true);
      } else {
        // Verification disabled — auto-login
        const { accessToken } = await authApi.login(email.trim(), password);
        localStorage.setItem("access_token", accessToken);
        toast.success("Welcome to QAmachine!");
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Something went wrong. Please try again.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleMagicLink() {
    if (!magicEmail.trim() || magicLoading) return;
    setMagicLoading(true);
    try {
      await authApi.requestMagicLink(magicEmail.trim());
      setMagicSent(true);
    } catch {
      toast.error("Failed to send link. Try again.");
    } finally {
      setMagicLoading(false);
    }
  }

  async function handleResend() {
    setResending(true);
    try {
      await authApi.resendVerification(email.trim());
      toast.success("Verification email resent!");
    } catch {
      toast.error("Failed to resend. Try again in a moment.");
    } finally {
      setResending(false);
    }
  }

  // ── "Check your email" screen ───────────────────────────────────────────────
  if (emailSent) {
    return (
      <div className="animate-slide-up text-center space-y-5">
        <div className="flex justify-center">
          <div className="h-16 w-16 rounded-2xl bg-accent/10 border border-accent/20
                          flex items-center justify-center">
            <Mail className="h-8 w-8 text-accent" />
          </div>
        </div>
        <div>
          <h1 className="text-xl font-bold text-text-primary mb-2">Check your email</h1>
          <p className="text-sm text-text-secondary leading-relaxed">
            We sent a verification link to<br/>
            <strong className="text-text-primary">{email}</strong>
          </p>
        </div>
        <div className="bg-bg-surface border border-border rounded-xl p-4 text-left space-y-2">
          <p className="text-xs text-text-muted">
            1. Open the email from <strong className="text-text-secondary">noreply@qamachine.site</strong>
          </p>
          <p className="text-xs text-text-muted">
            2. Click <strong className="text-text-secondary">"Verify email address"</strong>
          </p>
          <p className="text-xs text-text-muted">
            3. You'll be redirected to login automatically
          </p>
        </div>
        <p className="text-xs text-text-muted">
          Didn't get it? Check spam or{" "}
          <button
            onClick={handleResend}
            disabled={resending}
            className="text-accent hover:underline disabled:opacity-50"
          >
            {resending ? "Sending…" : "resend"}
          </button>
        </p>
        <p className="text-xs text-text-muted pt-2">
          <Link href="/login" className="text-text-secondary hover:text-text-primary underline">
            Back to login
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="animate-slide-up">

      {/* Heading */}
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-text-primary mb-2">
          Create your account
        </h1>
        <p className="text-sm text-text-secondary">
          Start automating QA in minutes — free to begin.
        </p>
      </div>

      {/* Free plan info */}
      <div className="mb-6 rounded-xl bg-accent/5 border border-accent/20 px-4 py-3">
        <p className="text-xs font-medium text-accent mb-2">Free plan includes:</p>
        <div className="flex flex-col gap-1">
          {FREE_PERKS.map((perk) => (
            <div key={perk} className="flex items-center gap-2">
              <CheckCircle className="h-3.5 w-3.5 text-accent shrink-0" />
              <span className="text-xs text-text-secondary">{perk}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-text-muted mt-2">
          No credit card required.{" "}
          <Link href="/billing" className="text-accent hover:underline">
            See all plans →
          </Link>
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Full name"
          type="text"
          placeholder="Alex Smith"
          value={name}
          onChange={(e) => { setName(e.target.value); if (errors.name) setErrors((p) => ({ ...p, name: undefined })); }}
          error={errors.name}
          leftIcon={<User className="h-4 w-4" />}
          autoComplete="name"
          autoFocus
        />

        <Input
          label="Email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => { setEmail(e.target.value); if (errors.email) setErrors((p) => ({ ...p, email: undefined })); }}
          error={errors.email}
          leftIcon={<Mail className="h-4 w-4" />}
          autoComplete="email"
        />

        <Input
          label="Password"
          type={showPass ? "text" : "password"}
          placeholder="Min. 8 characters"
          value={password}
          onChange={(e) => { setPassword(e.target.value); if (errors.password) setErrors((p) => ({ ...p, password: undefined })); }}
          error={errors.password}
          leftIcon={<Lock className="h-4 w-4" />}
          rightIcon={
            <button
              type="button"
              onClick={() => setShowPass((v) => !v)}
              className="text-text-muted hover:text-text-secondary transition-colors"
              tabIndex={-1}
            >
              {showPass
                ? <EyeOff className="h-4 w-4" />
                : <Eye className="h-4 w-4" />}
            </button>
          }
          autoComplete="new-password"
        />

        <div className="flex justify-center pt-2">
          <Button type="submit" size="lg" loading={loading} className="w-full">
            Create account
          </Button>
        </div>
      </form>

      <p className="text-xs text-text-muted text-center mt-4 leading-relaxed">
        By creating an account you agree to our{" "}
        <a href="#" className="text-text-secondary hover:text-text-primary underline">
          Terms of Service
        </a>{" "}
        and{" "}
        <a href="#" className="text-text-secondary hover:text-text-primary underline">
          Privacy Policy
        </a>.
      </p>

      <div className="flex items-center gap-3 my-6">
        <div className="flex-1 h-px bg-border" />
        <span className="text-xs text-text-muted">or</span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Google sign-up */}
      <div className="flex justify-center mb-6">
        <GoogleLogin
          onSuccess={async (resp) => {
            if (!resp.credential) return;
            setLoading(true);
            try {
              const { accessToken } = await authApi.googleLogin(resp.credential);
              localStorage.setItem("access_token", accessToken);
              toast.success("Welcome to QAmachine!");
              router.push("/dashboard");
            } catch {
              toast.error("Google sign-up failed. Please try again.");
            } finally {
              setLoading(false);
            }
          }}
          onError={() => toast.error("Google sign-up failed.")}
          theme="filled_black"
          size="large"
          shape="rectangular"
          text="signup_with"
        />
      </div>

      {/* Magic link section */}
      <div className="mt-2 rounded-xl border border-border bg-bg-surface p-4">
        <p className="text-xs font-medium text-text-muted mb-3 text-center">
          Skip the form — sign up with email link
        </p>
        {magicSent ? (
          <div className="text-center py-2 space-y-1">
            <p className="text-sm font-medium text-success">Link sent!</p>
            <p className="text-xs text-text-muted">
              Check <strong className="text-text-secondary">{magicEmail}</strong> — link expires in 15 min.
            </p>
            <button
              type="button"
              onClick={() => { setMagicSent(false); setMagicEmail(""); }}
              className="text-xs text-accent hover:underline mt-1"
            >
              Send to another email
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <input
              type="email"
              value={magicEmail}
              onChange={(e) => setMagicEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleMagicLink()}
              placeholder="your@email.com"
              className="flex-1 h-9 rounded-lg border border-border bg-bg-elevated px-3
                         text-sm text-text-primary placeholder:text-text-muted
                         focus:outline-none focus:border-accent transition-colors"
            />
            <button
              type="button"
              onClick={handleMagicLink}
              disabled={!magicEmail.trim() || magicLoading}
              className="h-9 px-4 rounded-lg bg-accent text-white text-sm font-medium
                         hover:bg-accent/90 disabled:opacity-40 transition-colors shrink-0"
            >
              {magicLoading ? "Sending…" : "Send link"}
            </button>
          </div>
        )}
      </div>

      <p className="text-center text-sm text-text-secondary mt-4">
        Already have an account?{" "}
        <Link
          href="/login"
          className="text-accent hover:text-accent-hover font-medium transition-colors"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
