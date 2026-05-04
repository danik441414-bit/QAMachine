"use client";
import { useRef } from "react";
import Script from "next/script";

const CLIENT_ID = "672004294381-hbpai74a9scdhu39cl46gmkie3c2s87m.apps.googleusercontent.com";

interface Props {
  onSuccess: (idToken: string) => void;
  onError?: () => void;
  text?: "signin_with" | "signup_with";
}

export function GoogleSignInButton({ onSuccess, onError, text = "signin_with" }: Props) {
  const buttonRef = useRef<HTMLDivElement>(null);

  function initialize() {
    if (!window.google || !buttonRef.current) return;
    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: (response: { credential: string }) => {
        if (response.credential) {
          onSuccess(response.credential);
        } else {
          onError?.();
        }
      },
    });
    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: "filled_black",
      size: "large",
      type: "standard",
      text,
      shape: "rectangular",
    });
  }

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        onLoad={initialize}
        strategy="lazyOnload"
      />
      <div ref={buttonRef} />
    </>
  );
}
