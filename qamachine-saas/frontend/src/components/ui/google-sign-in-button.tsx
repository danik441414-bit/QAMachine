"use client";
import { useEffect, useRef } from "react";

declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          initialize: (config: object) => void;
          renderButton: (element: HTMLElement, config: object) => void;
        };
      };
    };
  }
}

const CLIENT_ID = "672004294381-hbpai74a9scdhu39cl46gmkie3c2s87m.apps.googleusercontent.com";
const GSI_URL = "https://accounts.google.com/gsi/client";

interface Props {
  onSuccess: (idToken: string) => void;
  onError?: () => void;
  text?: "signin_with" | "signup_with";
}

export function GoogleSignInButton({ onSuccess, onError, text = "signin_with" }: Props) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);

  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  useEffect(() => {
    function initGoogle() {
      if (!window.google?.accounts?.id || !buttonRef.current) return;

      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: (response: { credential: string }) => {
          if (response.credential) {
            onSuccessRef.current(response.credential);
          } else {
            onErrorRef.current?.();
          }
        },
      });

      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "filled_black",
        size: "large",
        type: "standard",
        text,
        shape: "rectangular",
        locale: "en",
      });
    }

    // If GSI is already loaded (client-side navigation from another page), init immediately
    if (window.google?.accounts?.id) {
      initGoogle();
      return;
    }

    // If script tag already exists but hasn't fired yet, wait for it
    const existing = document.querySelector(`script[src="${GSI_URL}"]`) as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener("load", initGoogle);
      return () => existing.removeEventListener("load", initGoogle);
    }

    // First load: inject script
    const script = document.createElement("script");
    script.src = GSI_URL;
    script.async = true;
    script.defer = true;
    script.onload = initGoogle;
    document.head.appendChild(script);

    return () => {
      script.onload = null;
    };
  }, [text]);

  return <div ref={buttonRef} />;
}
