"use client"

import * as React from "react"
import Script from "next/script"

import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? ""
// Google renderButton kengligi px'da va 400 dan oshmaydi.
const MAX_BUTTON_WIDTH = 400

type GoogleCredentialResponse = { credential: string }

type GoogleIdApi = {
  initialize: (config: {
    client_id: string
    callback: (response: GoogleCredentialResponse) => void
    ux_mode?: "popup" | "redirect"
  }) => void
  renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdApi } }
  }
}

/**
 * Google Identity Services rasmiy tugmasi. Logo va ranglar Google brend
 * qoidalariga ko'ra o'zgartirilmaydi — shu sabab tugmani Google o'zi chizadi.
 * Client ID berilmagan bo'lsa hech narsa ko'rsatilmaydi.
 */
function GoogleSignInButton({
  mode,
  disabled,
  onCredential,
}: {
  mode: "login" | "register"
  disabled?: boolean
  onCredential: (credential: string) => void
}) {
  const containerRef = React.useRef<HTMLDivElement>(null)
  const onCredentialRef = React.useRef(onCredential)
  const [ready, setReady] = React.useState(false)

  React.useEffect(() => {
    onCredentialRef.current = onCredential
  }, [onCredential])

  const render = React.useCallback(() => {
    const google = window.google
    const container = containerRef.current
    if (!google || !container) return
    google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: (response) => onCredentialRef.current(response.credential),
      ux_mode: "popup",
    })
    container.replaceChildren()
    google.accounts.id.renderButton(container, {
      type: "standard",
      theme: "outline",
      size: "large",
      shape: "rectangular",
      text: mode === "login" ? "signin_with" : "signup_with",
      logo_alignment: "center",
      locale: "uz",
      width: Math.min(container.clientWidth || MAX_BUTTON_WIDTH, MAX_BUTTON_WIDTH),
    })
    setReady(true)
  }, [mode])

  if (!CLIENT_ID) return null

  return (
    <>
      <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onReady={render} />
      <div className="relative min-h-10" aria-busy={!ready || disabled}>
        {!ready && <Skeleton className="absolute inset-0 h-10 w-full" />}
        <div
          ref={containerRef}
          className={cn(
            "flex justify-center transition-opacity",
            disabled && "pointer-events-none opacity-50"
          )}
        />
      </div>
    </>
  )
}

export { GoogleSignInButton }
