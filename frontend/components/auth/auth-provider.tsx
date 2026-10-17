"use client"

import * as React from "react"

import { useAuthStore } from "@/lib/store/auth"

/** Mount'da joriy foydalanuvchini yuklaydi (token bo'lsa). Hech narsa render qilmaydi. */
function AuthProvider() {
  React.useEffect(() => {
    useAuthStore.getState().loadMe()
  }, [])
  return null
}

export { AuthProvider }
